# AWS Route 53 Clone

A software engineering assignment recreating Route 53 resource-management
workflows using Next.js, TypeScript, FastAPI, and SQLite. This application will
manage representations of DNS resources; it will not resolve DNS or call AWS.

## Current status: Phase 2

Implemented: frontend/backend scaffolds, the five-table SQLite model, an initial
Alembic migration, isolated pytest database tests, and `GET /health` returning
`{"status":"ok"}`.

Authentication, resource APIs, Cloudscape UI, frontend testing frameworks, and
deployment remain deferred. There is no deployed demo or demo login yet.
Phase 3 requires explicit approval.

## Architecture

- `frontend/`: Next.js App Router and TypeScript; pnpm dependency lockfile.
- `backend/`: FastAPI, SQLModel connection engine, Pydantic Settings, Uvicorn.
- SQLite foreign keys are enabled per connection. Sessions are request-scoped.
- The engine does not connect or create schema on import/startup. `/health` is
  a process-liveness endpoint, not a database-readiness check.
- The database now contains users, sessions, hosted zones, record sets, and values.
  Session authentication behavior remains deferred. Future UI uses Cloudscape
  and actual Route 53 visual references.

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
Alembic is a runtime migration dependency; pytest is development-only.

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
Application startup does not create database files or tables; run migrations explicitly.

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
Database tests are now available (see below). API tests, frontend component tests,
and end-to-end tests will be introduced with their relevant phases.

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
    normalization.py
    models/            # User, Session, HostedZone, DNSRecordSet, DNSRecordValue
  migrations/
    env.py
    script.py.mako
    versions/0001_create_database_foundation.py
  tests/
    conftest.py
    test_database.py
    test_migrations.py
  .env.example
  alembic.ini
  pytest.ini
  requirements.txt
  requirements-dev.txt
```

## Database model and migrations

SQLModel supplies the table/relationship models, SQLAlchemy enforces relational
constraints, and Alembic owns schema changes. No startup `create_all()` or migration
side effects are used.

```text
users
  |-- sessions
  +-- hosted_zones
        +-- dns_record_sets
              +-- dns_record_values
```

Every table has a UUID primary key (SQLite CHAR(32), Python UUID). Every child
foreign key uses `ON DELETE CASCADE`. Relationship deletes defer to the database;
value collections are loaded in ascending `position` order.

- Unique: normalized user email; session token hash; zones by
  `(user_id, name, type)`; record sets by `(hosted_zone_id, name, record_type)`;
  values by `(record_set_id, position)`.
- Indexes: unique email/token indexes; session user/expiry indexes; zone owner/type
  and record zone/type indexes. The composite unique constraints also provide
  indexes beginning with owner/name, zone/name, and record-set/position, avoiding
  redundant indexes for those lookups.
- Checks: positive TTL, nonnegative value position, PUBLIC/PRIVATE zone types,
  the nine required record types, SIMPLE routing, and canonical email/name storage.
- Multiple values occupy separate rows. Their DNS syntax and the rule requiring
  at least one value per record set belong to later service/schema validation.

Normalization is explicit: callers use `normalize_email()` and
`normalize_zone_name()` before persistence. For example, `Example.COM.` becomes
`example.com`. Models do not silently rewrite inputs; database checks reject
noncanonical stored names. Record owners are lowercase relative names; `""` is
the apex. FQDN-to-relative conversion is deferred to the API/service phase.

Timestamps default to aware UTC in Python, are stored as naive UTC in SQLite,
and return as aware UTC after loading. Naive Python timestamp inputs are rejected.
SQL defaults use CURRENT_TIMESTAMP (UTC); ORM/SQLAlchemy updates refresh
`updated_at`. Direct textual SQL updates must set `updated_at` explicitly.
No timestamp triggers or authentication logic are introduced.

From `backend/`, using the configured DATABASE_URL:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

To reverse this initial migration on a disposable database:

```powershell
.\.venv\Scripts\python.exe -m alembic downgrade base
```

Downgrade deletes all five domain tables and their data. Alembic retains its
empty `alembic_version` bookkeeping table. Do not downgrade a database whose data
you need to retain. Future changes use `alembic revision --autogenerate -m "description"`;
always review the generated migration before applying it.

Run the database tests from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Each test uses a temporary SQLite file migrated by Alembic. Tests never use the
configured development database. Coverage includes constraints, all supported
enums, UTC/UUID round trips, ordered values, transaction rollback, isolation of
resource trees, raw-SQL and ORM cascades, and upgrade/downgrade/re-upgrade.
Warnings are treated as test failures.

Zone name/comment/type editing remains planned. Renaming a zone preserves
relative record owners without rewriting target values. Alias, automatic NS/SOA,
and bonuses remain deferred. Deployment must preserve SQLite on persistent disk.

## Tooling notes

TypeScript is pinned to 5.9.3 for compatibility with the Next.js ESLint parser.
ESLint 9 is pinned because the installed Next.js React/import/accessibility
plugins do not yet declare ESLint 10 support. The package registry marks ESLint
9 deprecated; revisit the pin when those plugins support the newer major.
Only the `unrs-resolver` native helper is explicitly permitted to run its install
script in `pnpm-workspace.yaml`.
