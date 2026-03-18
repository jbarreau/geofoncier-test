#!/usr/bin/env bash
# =============================================================================
# scripts/release.sh
#
# Run python-semantic-release for one or all services in the mono-repo.
#
# Usage:
#   ./scripts/release.sh                       # release all services
#   ./scripts/release.sh auth-service          # release a single service
#   ./scripts/release.sh --dry-run             # print what would happen
#   ./scripts/release.sh auth-service --dry-run
#
# Expected env vars (typically injected by CI):
#   GH_TOKEN   – GitHub token with repo write access (for tag push + release)
#
# Dependencies (install into the venv or CI environment):
#   pip install "python-semantic-release>=9.0"
# =============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICES=("auth-service" "task-service" "analytics-service")

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
TARGET=""
DRY_RUN=false

for arg in "$@"; do
  case "$arg" in
    --dry-run)
      DRY_RUN=true
      ;;
    auth-service|task-service|analytics-service)
      TARGET="$arg"
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: $0 [service-name] [--dry-run]" >&2
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() { echo "[release] $*"; }

release_service() {
  local service="$1"
  local service_dir="$ROOT_DIR/backend/$service"

  if [[ ! -d "$service_dir" ]]; then
    echo "Service directory not found: $service_dir" >&2
    exit 1
  fi

  log "----------------------------------------------"
  log "Processing: $service"
  log "----------------------------------------------"

  pushd "$service_dir" > /dev/null

  local sr_flags=()
  if [[ "$DRY_RUN" == true ]]; then
    sr_flags+=("--noop")
    log "DRY RUN – no commits, tags, or pushes will be made"
  fi

  # 1. Compute next version, update pyproject.toml, generate/update CHANGELOG.md,
  #    create a version commit and a tag.
  log "Running: semantic-release version ${sr_flags[*]}"
  semantic-release version "${sr_flags[@]}"

  # 2. Push the version commit + tag to the remote.
  #    Skip in dry-run mode; CI should push only after all services succeed.
  if [[ "$DRY_RUN" == false ]]; then
    log "Running: semantic-release publish"
    semantic-release publish
  fi

  popd > /dev/null
  log "Done: $service"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if [[ -n "$TARGET" ]]; then
  release_service "$TARGET"
else
  for service in "${SERVICES[@]}"; do
    release_service "$service"
  done
fi

log "All done."
