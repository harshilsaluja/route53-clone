# AWS Route 53 Clone

A software engineering assignment recreating Route 53 resource-management
workflows using Next.js, TypeScript, FastAPI, and SQLite. This application will
manage representations of DNS resources; it will not resolve DNS or call AWS.

## Current status: Phase 1

Implemented: separate frontend/backend scaffolds, environment examples, a lazy
SQLite connection foundation, and `GET /health` returning `{"status":"ok"}`.

Domain models, authentication, hosted-zone/record APIs, Cloudscape UI, testing
frameworks, and deployment are intentionally deferred. There is no deployed demo
or demo login yet. Phase 2 requires explicit approval.

## Architecture

- `frontend/`: Next.js App Router and TypeScript; pnpm dependency lockfile.
- `backend/`: FastAPI, SQLModel connection engine, Pydantic Settings, Uvicorn.
- SQLite foreign keys are enabled per connection. Sessions are request-scoped.
- The engine does not connect or create schema on import/startup. `/health` is
  a process-liveness endpoint, not a database-readiness check.
- Future phases add opaque server-side sessions, hosted zones, record sets and
  record values. Future UI uses Cloudscape and actual Route 53 visual references.

## Prerequisites

- Node.js 24 LTS (Node.js 20.9+ supported by the selected Next.js generation).
- pnpm 11.19.0, as pinned in `frontend/package.json`.
- Python 3.12 recommended.

Install pnpm through your usual Node setup if needed: `npm install -g pnpm@11.19.0`.
Use two terminals for frontend and backend. No global Python dependencies needed.

## Frontend setup

From the repository root, in PowerShell:

```powershell
cd frontend
Copy-Item .env.example .env.local
pnpm install --frozen-lockfile
pnpm dev
```

Open [the frontend](http://localhost:3000). The Phase 1 page states that the
Next.js frontend is running. No backend request is made from this page yet.

## Backend setup

From the repository root, in PowerShell:

```powershell
cd backend
python -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

On macOS/Linux, use `cp` instead of `Copy-Item` and `.venv/bin/python` instead
of `.\.venv\Scripts\python.exe`. Run backend commands from `backend/`.

- [Health endpoint](http://localhost:8000/health)
- [OpenAPI documentation](http://localhost:8000/docs)

`requirements.txt` owns runtime dependencies; `requirements-dev.txt` includes it.
No development testing frameworks are installed during Phase 1.

## Environment configuration

| Location | Variable | Default / purpose |
| --- | --- | --- |
| `frontend/.env.local` | `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1`; reserved for future API integration |
| `backend/.env` | `APP_NAME` | `AWS Route 53 Clone API`; OpenAPI title |
| `backend/.env` | `DATABASE_URL` | `sqlite:///./route53.db`; relative to `backend/`, not shell cwd |

Process environment variables override backend `.env` values. Frontend public
variables are browser-visible and must not contain secrets. Restart after changes.

SQLite URLs only are accepted. An absolute Windows path can use forward slashes,
for example `sqlite:///C:/route53-data/route53.db`. Create the parent directory
before connecting. Prefer local storage outside OneDrive for database files.
No database file or domain tables are needed or created by Phase 1 startup.

## Verification

From `frontend/`:

```powershell
pnpm lint
pnpm typecheck
pnpm build
pnpm start
```

With FastAPI running, from another PowerShell terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected JSON: `{"status":"ok"}` with HTTP 200. Stop servers with Ctrl+C.
Backend feature tests, frontend component tests, and end-to-end tests will be
introduced with their relevant phases.

## Repository layout

```text
AGENTS.md
README.md
.gitignore
frontend/
  app/                 # Root layout, startup page, basic global styles
  .env.example
  eslint.config.mjs
  next-env.d.ts
  next.config.ts
  package.json
  pnpm-lock.yaml
  pnpm-workspace.yaml  # Explicit native dependency build permission
  tsconfig.json
backend/
  app/
    __init__.py
    config.py
    database.py
    main.py
  .env.example
  requirements.txt
  requirements-dev.txt
```

## Planned constraints

Hosted zones will be unique by owner, normalized name, and PUBLIC/PRIVATE type.
Zone renaming will preserve relative record owner names without rewriting target
values. Only SIMPLE routing is planned initially. Alias, automatic NS/SOA, and
bonus functionality remain deferred. Deployment must preserve the SQLite file;
no hosting provider or deployment configuration has been selected yet.

## Tooling notes

TypeScript is pinned to 5.9.3 for compatibility with the Next.js ESLint parser.
ESLint 9 is pinned because the installed Next.js React/import/accessibility
plugins do not yet declare ESLint 10 support. The package registry marks ESLint
9 deprecated; revisit the pin when those plugins support the newer major.
Only the `unrs-resolver` native helper is explicitly permitted to run its install
script in `pnpm-workspace.yaml`.
