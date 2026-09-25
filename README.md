# AWS Route 53 Clone

A software engineering assignment recreating Route 53 resource-management
workflows using Next.js, TypeScript, FastAPI, and SQLite. This application will
manage representations of DNS resources; it will not resolve DNS or call AWS.

## Current status: Phase 3

Implemented: frontend/backend scaffolds, the five-table SQLite model, Alembic
migrations, backend demo authentication with persistent sessions, and isolated
database/authentication tests. GET /health remains unchanged.

Frontend login, resource APIs, Cloudscape UI, frontend test tools, and deployment
remain deferred. Phase 4 requires explicit approval.

## Architecture

- `frontend/`: Next.js App Router and TypeScript; pnpm dependency lockfile.
- `backend/`: FastAPI, SQLModel connection engine, Pydantic Settings, Uvicorn.
- SQLite foreign keys are enabled per connection. Sessions are request-scoped.
- The engine does not connect or create schema on import/startup. `/health` is
  a process-liveness endpoint, not a database-readiness check.
- The database now contains users, sessions, hosted zones, record sets, and values.
  Authentication now uses opaque database-backed sessions. Future UI uses Cloudscape
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
Alembic and Argon2 are runtime dependencies; pytest and httpx2 are development-only.

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
Database and authentication tests are available below. Frontend and end-to-end
test tools remain deferred.

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
    dependencies.py
    errors.py
    main.py
    normalization.py
    security.py
    seed.py
    routers/auth.py
    schemas/auth.py
    services/auth_service.py
    models/            # User, Session, HostedZone, DNSRecordSet, DNSRecordValue
  migrations/
    env.py
    script.py.mako
    versions/0001_create_database_foundation.py
  tests/
    conftest.py
    test_auth.py
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
No timestamp triggers are used.

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

## Backend demo authentication

From backend/, after installing requirements-dev.txt:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Access the API at http://localhost:8000 and use http://localhost:3000 for the
frontend origin. Keep browser hostnames consistent; binding the server to
127.0.0.1 keeps it local. There is no frontend login screen yet.

Public assignment credentials:

- Email: `demo@route53clone.dev`
- Password: `Scaler@123`
- Display name: `Demo User`

The seed command creates an Argon2id password hash. Repeated runs leave the
existing account, password, and profile unchanged. Seeding never runs on import
or startup and does not create tables.

| Endpoint | Behavior | Status |
| --- | --- | --- |
| POST /api/v1/auth/login | JSON email/password; sets cookie; returns safe user and expiry | 200; invalid credentials 401 |
| GET /api/v1/auth/me | Resolves identity from the session cookie | 200; missing/invalid/expired session 401 |
| POST /api/v1/auth/logout | Revokes session and clears cookie | 204, including missing/invalid/expired sessions |
| GET /health | Existing process liveness | 200 |

Login JSON: `{"email":"demo@route53clone.dev","password":"Scaler@123"}`.
Login and me return `{user: {id, email, display_name}, expires_at}`.
Password hashes, token hashes, and raw tokens never appear in response JSON.
Malformed input returns 422; rejected mutation origins return 403. Errors use
`{error: {code, message}}`; validation errors include safe field details without
echoing input values.

Sessions default to a fixed 24-hour lifetime without sliding refresh. Tokens
contain 32 random bytes (256 bits); only their SHA-256 digest is stored.
Passwords use Argon2, not SHA-256. Each login creates an independent session.
Logout revokes only the supplied session. Expired sessions are rejected; logout
also removes an expired row when its cookie is supplied. Background cleanup is
not implemented.

The reusable get_current_user dependency derives identity exclusively from the
cookie-backed session. Authentication responses use Cache-Control: no-store.

Additional backend environment settings:

| Variable | Default |
| --- | --- |
| ALLOWED_FRONTEND_ORIGINS | JSON array: `["http://localhost:3000"]` |
| SESSION_COOKIE_NAME | `route53_session` |
| SESSION_TTL_SECONDS | `86400` |
| SESSION_COOKIE_SECURE | `false` locally; set `true` for HTTPS |
| SESSION_COOKIE_SAMESITE | `lax`; `none` requires Secure |

The host-only cookie uses HttpOnly and Path=/, with Max-Age and Expires matching
the stored expiry. CORS permits credentials only for explicitly configured
origins, never wildcard origins. Future browser requests must use
`credentials: "include"`. Login/logout reject an Origin that is neither a
configured frontend origin nor the API's own origin. Clients without Origin
remain supported. Deployment-specific CSRF hardening is deferred.

Run authentication tests or the complete backend suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_auth.py
.\.venv\Scripts\python.exe -m pytest
```

Tests migrate isolated temporary SQLite databases and never use the development
database. They cover seeding, cookies, safe responses, expiry/revocation, session
persistence, identity isolation, CORS/Origin checks, and transaction rollback.
The installed Starlette version prefers httpx2 for its test client, avoiding its
deprecated httpx fallback.

## Tooling notes

TypeScript is pinned to 5.9.3 for compatibility with the Next.js ESLint parser.
ESLint 9 is pinned because the installed Next.js React/import/accessibility
plugins do not yet declare ESLint 10 support. The package registry marks ESLint
9 deprecated; revisit the pin when those plugins support the newer major.
Only the `unrs-resolver` native helper is explicitly permitted to run its install
script in `pnpm-workspace.yaml`.
