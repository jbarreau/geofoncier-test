# Exercise Steps

## Table of Contents

1. [Initial Reading & Framing](#1-initial-reading--framing)
2. [AI Analysis](#2-ai-analysis)
   - [2.1 Feeding the Subject to the AI](#21-feeding-the-subject-to-the-ai)
   - [2.2 Reviewing the AI Proposal](#22-reviewing-the-ai-proposal)
   - [2.3 Validating the Proposal](#23-validating-the-proposal)
     - [Authentication](#authentication)
     - [Authorization](#authorization)
     - [Known Limitations](#known-limitations)
3. [Architecture Concerns](#3-architecture-concerns)
   - [Database Boundaries and Data Sharing](#database-boundaries-and-data-sharing)
4. [Implementation Approach](#4-implementation-approach)
   - [AI as a Productive Contributor, but Not Autonomous](#ai-as-a-productive-contributor-but-not-autonomous)

---

## 1. Initial Reading & Framing

I read the assignment about one week before I started coding.

During that week, I explored some architecture options. A microservice approach looked like a good fit, with either:

- a shared library for common logic, or
- a dedicated service if stronger isolation was needed.

I also wanted to test Claude Code and see where it helps and where it fails.

At that point, I had not decided:

- one database for all services vs one database per service,
- how services should communicate with each other.

I also kept Redis in mind for fast permission caching.

---

## 2. AI Analysis

### 2.1 Feeding the Subject to the AI

When I started, I gave the PDF to the AI and set these constraints:

- **Python** for backend,
- **Vue.js** for frontend,
- **FastAPI** as backend framework.

Why:

- **Python**: it is my strongest language and has a strong API ecosystem.
- **FastAPI**: good for service APIs, with typing, validation, and OpenAPI support.
- **Vue.js**: my preferred frontend framework for this scope.

---

### 2.2 Reviewing the AI Proposal

The AI suggested 3 microservices:

| Service | Responsibility | Database |
|---|---|---|
| `auth` | Authentication, authorization, user management | Own database |
| `task` | Task CRUD and business operations | Own database |
| `analytics` | Task reporting and statistics | Read-only access to task DB |

<!-- TODO: add architecture diagram (frontend + 3 services + databases) -->

Authentication mechanism: **JWT**

Authorization model: **RBAC**

```text
user → role → permissions
```

---

### 2.3 Validating the Proposal

#### Authentication

I reviewed JWT to confirm trade-offs and runtime impact.

```text
The auth service checks credentials and returns a signed token
with identity and authorization claims.

Other services verify the token signature with a public key and
apply permissions from token claims.

The frontend stores and sends the token, but does not keep signing keys.
```

<!-- TODO: add sequence diagram: login → token issuance → token verification -->

Why this fit the exercise:

- Auth is centralized in one service.
- Token checks are stateless in other services.
- Claims can include roles/permissions for local checks.
- Signature validation prevents client-side token tampering.

---

#### Authorization

The model is RBAC: `user → role → permissions`, with permissions like `tasks:create`.

Why I kept it:

- Easy to read and audit.
- Clear separation between identity and permissions.
- Simpler than full policy engines for this test.

<!-- TODO: add entity-relationship diagram: User ↔ Role ↔ Permission -->

Known caveat: users with both admin and non-admin roles can end up in “always-admin” behavior in UI/API flows.

Practical mitigations:

1. Use separate accounts for admin and daily usage.
2. Limit admin grants and keep approval/audit steps.

---

#### Known Limitations

**Authentication design:**

- **Permission changes** are applied only after token refresh (mitigate with short token TTL).
- **User ban/revocation** is delayed without server-side revocation (mitigate with Redis denylist).
- **JWT payload visibility**: payload is signed, not encrypted. Do not put secrets in it.

**Authorization design:**

- RBAC alone is too coarse for some context rules (ownership, environment, business context).
- Advanced rules may require resource-level checks in addition to RBAC.

---

## 3. Architecture Concerns

### Database Boundaries and Data Sharing

At first, I was not convinced by strict database isolation per service, because data-sharing needs usually appear quickly in real systems.

In this case:

- **Auth data** is shared indirectly through JWT claims.
- **Analytics** still needs task data, which brings coupling back.

<!-- TODO: add diagram comparing data-sharing strategies -->

I reviewed 3 options:

| Option | Description | Verdict |
|---|---|---|
| HTTP API calls | Analytics fetches data from task service APIs | More latency and infra cost |
| Direct DB read | Analytics reads task DB with read-only access | **Chosen** for simplicity/performance in this test |
| Local replica | Analytics keeps its own projection copy | More moving parts and write amplification |

For this exercise, this choice is acceptable. In production, I would usually prefer explicit data contracts/events instead of direct DB coupling.

---

## 4. Implementation Approach

I started the repository with `CLAUDE.md`, then worked feature by feature with Claude Code.

Execution order:

1. Implement backend services (incrementally).
2. Add end-to-end tests for cross-service behavior.
3. Move shared logic into a shared library.
4. Implement the frontend.

In parallel, I used AI workflows for refactoring, CI, testing, and DX tasks, while I managed PR order and merge order to keep the branch stable.

---

### AI as a Productive Contributor, but Not Autonomous

My role shifted from mostly writing code to:

- framing tasks clearly,
- reviewing design and implementation choices,
- enforcing quality gates (tests, CI, maintainability).

Most review feedback was in three groups:

- Refactoring and simplification.
- CI/test stabilization.
- Missing tests and coverage gaps.

Main friction points were expected:

- PRs that looked complete but failed CI,
- rebase/merge drift with `main`,
- missing “obvious” engineering steps unless explicitly requested.

Overall, AI greatly improved delivery speed, but it still needed clear direction and strict review.
