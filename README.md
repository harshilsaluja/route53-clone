# AWS Route 53 Clone

A software engineering assignment recreating Route 53 resource-management
workflows using Next.js, TypeScript, FastAPI, and SQLite. This application will
manage representations of DNS resources; it will not resolve DNS or call AWS.

## Current status: combined Phases 6 + 7

Implemented: frontend/backend scaffolds, the five-table SQLite model, Alembic
migrations, backend session authentication, authenticated Hosted Zone and DNS
Record APIs, plus the Cloudscape/TanStack Query frontend foundation and complete
Hosted Zones browser workflow. GET /health remains unchanged.

The DNS Records frontend, Alias records, automatic NS/SOA generation, end-to-end
test framework, and deployment remain deferred.

## Architecture

- `frontend/`: Next.js App Router and TypeScript; pnpm dependency lockfile.
- `backend/`: FastAPI, SQLModel connection engine, Pydantic Settings, Uvicorn.
- SQLite foreign keys are enabled per connection. Sessions are request-scoped.
- The engine does not connect or create schema on import/startup. `/health` is
  a process-liveness endpoint, not a database-readiness check.
- The database contains users, sessions, hosted zones, record sets, and values.
  Authentication uses opaque database-backed sessions. The frontend uses
  Cloudscape and remains subject to comparison with Route 53 visual references.

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

Open [the frontend](http://localhost:3000). Start the backend first, then sign in
with the demo credentials below. Keep \`localhost\` consistent for both applications
so the browser can use the host-only authentication cookie.

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
    routers/           # auth.py, hosted_zones.py, dns_records.py
    schemas/           # auth.py, common.py, hosted_zone.py, dns_record.py
    services/          # auth_service.py, hosted_zone_service.py, dns_record_service.py
    validation/        # dns_names.py, record_values.py
    models/            # User, Session, HostedZone, DNSRecordSet, DNSRecordValue
  migrations/
    env.py
    script.py.mako
    versions/0001_create_database_foundation.py
  tests/
    conftest.py
    test_auth.py
    test_dns_records.py
    test_hosted_zones.py
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

Zone name/comment/type editing is available through the Hosted Zone API.
Renaming a zone preserves relative record owners without rewriting target values. Alias, automatic NS/SOA,
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
127.0.0.1 keeps it local. The frontend login page communicates directly with this
API and includes the HttpOnly session cookie on authenticated requests.

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
cookie-backed session; Hosted Zone endpoints use it for ownership. Authentication responses use Cache-Control: no-store.

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
`credentials: "include"`. Mutating authentication and Hosted Zone requests reject an Origin that is neither
a configured frontend origin nor the API's own origin. Clients without Origin
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

## Route 53 frontend

The browser UI uses Cloudscape for the AWS-style shell and controls, and TanStack
Query for session and Hosted Zone server state. All API calls go through a small
typed client that sends credentials, handles empty 204 responses, and converts
structured backend errors into safe frontend messages.

| Route | Behavior |
| --- | --- |
| / | Redirects through the protected Route 53 area |
| /login | Demo login and authentication errors |
| /route53/hosted-zones | Backend search, type filtering, pagination, selection, and deletion |
| /route53/hosted-zones/create | Create a public or private Hosted Zone |
| /route53/hosted-zones/{zoneId} | Zone metadata and record-count summary |
| /route53/hosted-zones/{zoneId}/edit | Edit name, description, and type |
| Sidebar destinations | Intentional assignment placeholders |

Protected pages restore the user through GET /api/v1/auth/me. Authentication
tokens never enter JavaScript storage or application state; the browser manages
the HttpOnly cookie. Logging out clears cached query data and returns to login.
Create, update, and delete operations show Cloudscape notifications. Deletion
requires confirmation and warns that stored records are also removed.

The Hosted Zones list keeps search, type, and page in the URL. Search is debounced
and all filtering and pagination happen in the FastAPI backend. The details page
contains a neutral Records section placeholder; DNS Record frontend management is
deliberately deferred to the next authorized phase.

## Hosted Zone backend API

All five endpoints require the session cookie. Ownership always comes from the
authenticated user; request bodies cannot supply user_id. Another user's zone
and a nonexistent zone both return 404 HOSTED_ZONE_NOT_FOUND.

| Endpoint | Success | Purpose |
| --- | --- | --- |
| GET /api/v1/hosted-zones | 200 | List the current user's zones |
| POST /api/v1/hosted-zones | 201 | Create a PUBLIC or PRIVATE zone |
| GET /api/v1/hosted-zones/{zone_id} | 200 | Retrieve an owned zone |
| PATCH /api/v1/hosted-zones/{zone_id} | 200 | Update name, comment, or type |
| DELETE /api/v1/hosted-zones/{zone_id} | 204 | Delete an owned zone and its records |

Create body:

```json
{"name": "Example.COM.", "type": "PUBLIC", "comment": "Production domain"}
```

Names are trimmed, lowercased, and have one optional trailing dot removed before
validation. ASCII/punycode labels must be 1–63 characters, use letters/digits/
hyphens, and cannot begin or end with a hyphen. The full normalized name is limited
to 253 characters. Empty labels, spaces inside names, Unicode labels, wildcard
zones, and URL syntax are rejected. No DNS lookup or IDN conversion is performed.
Comments are optional/null and limited to 1,024 characters.

Uniqueness remains (authenticated user, normalized name, type). Duplicate creates,
renames, and type changes return 409 HOSTED_ZONE_ALREADY_EXISTS. Public and
private zones may share a name, and different users may independently own the
same name/type.

List query parameters:

| Parameter | Default | Accepted values |
| --- | --- | --- |
| search | empty | Trimmed substring of name or comment; maximum 1,024 characters |
| type | no filter | PUBLIC or PRIVATE |
| page | 1 | Integer >= 1 |
| page_size | 20 | Integer 1–100 |
| sort_by | name | name, type, created_at |
| sort_order | asc | asc, desc |

Search is case-insensitive for ASCII using SQLite; '%' and '_' are treated as
literal characters. Search/type filters combine in SQL, and ordering/pagination
also happen in SQL. ID ascending is the final sort tie-breaker. Unknown list query
parameters, invalid sort fields, and invalid pagination values return 422.

Responses expose id, name, type, comment, record_count, created_at, and updated_at.
No owner ID or other user information is exposed. record_count is the number of
record sets, not individual values. List counts are computed with an aggregate
join without per-zone queries.

Lists return `{items: [...], pagination: {page, page_size, total, pages}}`.
total/pages reflect the filtered collection; zero matches means total=0/pages=0.
A valid page beyond the last page returns an empty items array without an error.

PATCH requires at least one editable field. Omitted fields stay unchanged;
comment:null clears the comment. name/type cannot be null, and unknown body
fields are rejected. The merged zone is revalidated. Actual changes refresh
updated_at. Renaming changes the future FQDN derived from relative record names,
but never rewrites stored record names or target values. The future UI must warn
about this behavior before renaming.

DELETE relies on database foreign-key cascades to remove record sets and values.
No confirmation token is required; the future frontend will provide confirmation.
Mutations use the existing Origin check, and CORS permits GET/POST/PATCH/DELETE.
Zone responses use Cache-Control: no-store. Missing authentication returns 401;
invalid payloads/UUIDs return safe 422 errors. /docs exposes the request, response,
and query schemas.

Run Hosted Zone tests or the complete backend suite from backend/:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_hosted_zones.py
.\.venv\Scripts\python.exe -m pytest
```

Tests use migrated temporary SQLite databases. Existing record rows are created
directly in test fixtures to verify counts, rename preservation, and cascades;
the Phase 5 suite exercises the public DNS Record endpoints as well.

## DNS Record backend API

All record endpoints require the existing session cookie and are nested under an
owned Hosted Zone:

| Endpoint | Success | Purpose |
| --- | --- | --- |
| GET /api/v1/hosted-zones/{zone_id}/records | 200 | Search, filter, sort, and page records |
| POST /api/v1/hosted-zones/{zone_id}/records | 201 | Create a logical record set and its values |
| GET /api/v1/hosted-zones/{zone_id}/records/{record_id} | 200 | Retrieve one record |
| PATCH /api/v1/hosted-zones/{zone_id}/records/{record_id} | 200 | Partially update a record |
| DELETE /api/v1/hosted-zones/{zone_id}/records/{record_id} | 204 | Delete a record and cascade its values |

Create accepts `name`, `record_type`, `ttl`, optional
`routing_policy: "SIMPLE"`, and a nonempty `values` array. PATCH accepts any
nonempty subset and replaces the complete value collection when `values` is
present. Unknown fields and null editable fields are rejected. Responses add the
computed `fqdn` and ordered string values without exposing value-row IDs.

Record owner names are lowercase and relative to the zone. `@` and the empty
string both represent the apex and are stored as an empty string. Supplying an
absolute name or duplicating the zone suffix is rejected. The response FQDN is
the zone name at the apex and `<relative-name>.<zone-name>` otherwise. Basic
ASCII labels, underscore service labels, and a complete leftmost wildcard label
are supported; the final FQDN is limited to 253 characters.

The supported types are A, AAAA, CNAME, TXT, MX, NS, PTR, SRV, and CAA. A and
AAAA use canonical IP formatting. Hostname targets are lowercased and lose one
trailing dot. MX and SRV numeric fields are range checked and structural
whitespace is canonicalized. CAA accepts flags 0-255, the tags issue,
issuewild, and iodef, and a JSON-style quoted nonempty value. TXT uses raw
strings: case, spaces, quotes, and backslashes round-trip unchanged.

A record set cannot contain duplicate canonical values. The same zone/name/type
is unique. CNAME requires exactly one target, cannot exist at the apex, and
cannot coexist with another type at its owner name in either direction. Record
set/value writes and conflict checks occur in one SQLite write transaction;
failed creates or updates leave no partial data.

List queries support `search`, `record_type`, `page`, `page_size` (maximum
100), `sort_by` (name, record_type, ttl, created_at), and `sort_order`. Search
runs in SQLite across relative names, derived FQDNs, and values. Value matching
uses EXISTS, and values are eager loaded in a batched query. Hosted Zone
`record_count` continues to count record sets, regardless of value count.

Run the DNS Record tests or complete backend suite from backend/:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_dns_records.py
.\.venv\Scripts\python.exe -m pytest
```

## Tooling notes

TypeScript is pinned to 5.9.3 for compatibility with the Next.js ESLint parser.
ESLint 9 is pinned because the installed Next.js React/import/accessibility
plugins do not yet declare ESLint 10 support. The package registry marks ESLint
9 deprecated; revisit the pin when those plugins support the newer major.
Only the `unrs-resolver` native helper is explicitly permitted to run its install
script in `pnpm-workspace.yaml`.
