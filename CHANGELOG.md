## [1.3.0](https://github.com/jbarreau/geofoncier-test/compare/v1.2.0...v1.3.0) (2026-03-17)

### Features

* **analytics:** implement read-only analytics endpoints ([#9](https://github.com/jbarreau/geofoncier-test/issues/9)) ([e4bb2d5](https://github.com/jbarreau/geofoncier-test/commit/e4bb2d555437877867887e6b27d64007d7b08ae4))

## [1.2.0](https://github.com/jbarreau/geofoncier-test/compare/v1.1.0...v1.2.0) (2026-03-16)

### Features

* **task-service:** add SQLAlchemy models, Alembic migration, and CRUD endpoints ([#7](https://github.com/jbarreau/geofoncier-test/issues/7)) ([1bcb10b](https://github.com/jbarreau/geofoncier-test/commit/1bcb10b13d793df19c46322f08738e88fc490401))

## [1.1.0](https://github.com/jbarreau/geofoncier-test/compare/v1.0.0...v1.1.0) (2026-03-16)

### Features

* **task-service:** add JWT RS256 middleware with Redis blacklist and require_permission ([#6](https://github.com/jbarreau/geofoncier-test/issues/6)) ([b3f4325](https://github.com/jbarreau/geofoncier-test/commit/b3f4325edc58bc84e8b02ee2ba15c2c6d4051533))

## 1.0.0 (2026-03-16)

### Features

* **auth-service:** add auth-service with JWT and refresh token support ([#2](https://github.com/jbarreau/geofoncier-test/issues/2)) ([82834d6](https://github.com/jbarreau/geofoncier-test/commit/82834d6ad6c3b9e91bad19266d7ce0c8d294735c))
* **ci:** setup python-semantic-release for mono-repo ([#1](https://github.com/jbarreau/geofoncier-test/issues/1)) ([a29e39e](https://github.com/jbarreau/geofoncier-test/commit/a29e39e6eecbf9b9a9f9ab8ee24c48de35225b45))

# Changelog

All notable changes to **Geofoncier** are documented here.
Each service maintains its own changelog:

- [auth-service/CHANGELOG.md](auth-service/CHANGELOG.md)
- [task-service/CHANGELOG.md](task-service/CHANGELOG.md)
- [analytics-service/CHANGELOG.md](analytics-service/CHANGELOG.md)

Changelogs are generated automatically by
[python-semantic-release](https://python-semantic-release.readthedocs.io/)
following [Conventional Commits](https://www.conventionalcommits.org/).
