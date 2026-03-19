# Exercise Steps

## Table of Contents

1. [Initial Reading & Thinking](#1-initial-reading--thinking)
2. [AI Analysis](#2-ai-analysis)
   - [2.1 Feeding the Subject to the AI](#21-feeding-the-subject-to-the-ai)
   - [2.2 Reading the AI Output](#22-reading-the-ai-output)
   - [2.3 Validating the Proposals](#23-validating-the-proposals)
     - [Authentication](#authentication)
     - [Authorization](#authorization)
     - [Limitations](#limitations)
3. [My Concerns](#3-my-concerns)
   - [Databases](#databases)
4. [Starting the Implementation](#4-starting-the-implementation)
   - [AI as a Good Dev but a Bad Employee](#ai-as-a-good-dev-but-a-bad-employee)

---

## 1. Initial Reading & Thinking

I read the test roughly one week before starting it.

During that time, I started thinking about the solution. I had in mind a microservice architecture (almost explicitly stated in the test), with a shared library (or a dedicated microservice if needed).

I was told: *"try Claude Code and see what its limitations are — you may be surprised"*.

At this point I hadn't yet decided on one or multiple databases, or how services would communicate with each other. However, I kept in mind that Redis would be a good and performant solution if, for example, a permission cache was needed.

---

## 2. AI Analysis

### 2.1 Feeding the Subject to the AI

Once I started working on the test, I gave the PDF to the AI to see what it would recommend.

I constrained it to Python and Vue.js, while only suggesting FastAPI.

- **Python**: my main language, and appropriate for web applications.
- **FastAPI**: for microservices, using micro-frameworks is more adapted — It won't necessarily need an ORM or a lot of middlewares.
  FastAPI also uses Pydantic (written in Rust for performance) for serialization, validation, and deserialization of data — all working with type hints, and ultimately able to generate an OpenAPI schema for auto-generated Swagger documentation.
- **Vue.js**: my preferred frontend framework. I'm more experienced with AngularJS, but it's obsolete, and recently I've been learning Vue.js. Regarding the place of the frontend in the test, it is clearly a "will figure out later" part — but worth keeping in mind.

---

### 2.2 Reading the AI Output

The AI proposed FastAPI and 3 microservices:

| Service       | Responsibility                                      | Database                    |
|---------------|-----------------------------------------------------|-----------------------------|
| `auth`        | Authentication, authorization, and user management  | Own database                |
| `task`        | All task-related operations                         | Own database                |
| `analytics`   | Stats and reporting on tasks                        | Read-only access to task DB |

<!-- TODO: add architecture diagram showing the 3 services, their databases, and the frontend -->

Authentication: JWT

Access control: Role-Based Access Control (RBAC)

```
user → role → permissions
```

---

### 2.3 Validating the Proposals

#### Authentication

Because I wasn't fully familiar with all authentication methods and their specifics, I read up on JWT and why it is a good choice for stateless authentication.

```
The auth service authenticates users with username and password,
creates an object containing the user's permissions, signs it with
a private key — this signed object is the JWT token.

Other services use the associated public key to verify the token.
Once verified, the token content can be used to determine the
user's permissions and roles.

The frontend holds neither key.
```

<!-- TODO: add a sequence diagram showing the JWT flow: login → token issuance → token verification across services -->

This aligns with my reading, and the following points made me agree with the AI's choice:

- Only one service handles authentication.
- JWT enables stateless authentication.
- Roles and permissions can be easily managed and validated across services.
- The frontend cannot tamper with authentication data.

---

#### Authorization

The AI proposed Role-Based Access Control: `user → role → permissions`.

In this model, a user can have multiple roles, and each role defines a set of permissions in the form of `tasks:create`.

I like this representation because:

- Permissions are human-readable.
- Permissions are not directly tied to users — we don't grant nuclear launch access to someone named "Macron" because of their name, but because their current *role* is "president".
- Compared to Django's permission/group system, this model is simpler and fits the needs well.

<!-- TODO: add an entity-relationship diagram: User ↔ Role ↔ Permission -->

There is one known limitation: a user holding multiple roles (e.g., `admin` and `regular user`) will always see everything through their admin role. If they want to use the app as a regular user, they will have difficulty seeing only what they are supposed to see.

Two recommendations to work around this:

1. Use two separate accounts — one for regular use, one with admin privileges (e.g., `john.doe+admin@gmail.com`).
2. Avoid promoting someone to admin unless they have a thorough understanding of the software.

---

#### Limitations

**On the authentication design:**

- **Permission changes**: handled by updating the JWT token with a short TTL.
- **User banning**: will only take effect after token re-issuance. Solution: a Redis-backed token blacklist.
- **JWT content is not encrypted**: secrets should never be stored in it. That was never the intention here — for a list of permissions and in the scope of this test, it is acceptable.

**On the permissions design:**

- With great power comes great responsibility: do not promote someone to admin unless they have a very good understanding of the software.
- Use two accounts: one for regular use, one with admin privileges (e.g., `john.doe+admin@gmail.com`).

---

## 3. My Concerns

### Databases

Initially, I was not very comfortable with the idea of fully separated databases in a microservice architecture. I was convinced that at some point, data would need to be shared between services. Also, having separated databases is incompatible with SQL constraints like foreign keys across multiple databases.

In our example:

- **Auth/permissions** shared across all services for permission checking → handled by JWT.
- **Analytics** needing access to task data → this is exactly the problem.

<!-- TODO: add a diagram showing the data-sharing trade-offs between the 3 approaches below -->

Ideally, every microservice should be independent and own its database — but that is theory. To handle this data-sharing problem, we had 3 options:

| Option           | Description                                                | Verdict                                    |
|------------------|------------------------------------------------------------|--------------------------------------------|
| HTTP API call    | Analytics queries the task service via HTTP                | Too costly on the infrastructure           |
| Direct DB read   | Analytics reads the task database directly (read-only)     | **Chosen** — low latency, high performance |
| Local replica DB | Analytics keeps a local copy, updated on every task change | Too many writes and HTTP calls             |

I also kept in mind that consolidating all databases into a single one is doable and relatively easy. The reverse operation — splitting a monolithic database — is far more complex.

---

## 4. Starting the Implementation

I initialized the project and repository with a `CLAUDE.md` file, then started giving instructions to Claude Code for the implementation.

At that point I thought I would need to write a lot of code — but Claude Code did a great job handling multiple tasks simultaneously in different workspaces, and with a bit of setup, even the GitHub pull requests.

The implementation order was:

1. Implement the backends (one service at a time).
2. Create end-to-end tests to simulate the frontend and validate how everything works when all services run together.
3. Create a shared library to handle common functionalities (permission verification, utils, …).
4. Create the frontend.

During these steps, I also asked Claude to spin up additional agents to refactor code, set up CI, add tests, and handle smaller tasks — which required me to orchestrate the timing of which PR to merge before or after another to maintain code quality and keep features moving (as if I had a real sprint to manage).

---

### AI as a Good Dev but a Bad Employee

So I stopped being a developer and became a project manager instead 😄.

I reviewed pull requests and kept asking for more: tests, coverage, CI pipelines, data seed scripts, a Docker Compose setup, semantic release, monorepo and so on.

Most of my review comments fell into three categories:

- Refactoring suggestions.
- Fixing failing tests because CI was in error.
- Adding tests because coverage was too low.

It was occasionally frustrating to receive a clean-looking pull request, only to find — while reviewing — that the CI had failed or that a merge from `main` was needed with conflicts to resolve.

That said, it was an interesting way to probe the limits of AI-assisted development. Claude handled all of these tasks well, even if I had to explicitly ask for what should have been obvious steps.
