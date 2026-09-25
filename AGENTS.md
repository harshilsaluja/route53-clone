# Working agreements

This is an evaluated AWS Route 53 clone assignment. Keep the implementation
focused, maintainable, and close to the approved phase scope.

- Required stack: Next.js App Router + TypeScript, FastAPI + Python, SQLite.
- Keep frontend and backend separate. Do not implement backend business logic
  in Next.js API routes.
- Implement only the phase explicitly authorized by the user. Stop after its
  verification and report; do not start the next phase without instruction.
- Phase 1 includes scaffolding, configuration, a SQLite connection foundation,
  and GET /health only. No domain tables, auth, resource APIs, or Route 53 UI.
- Python dependencies belong in requirements.txt and requirements-dev.txt.
  Do not duplicate them in pyproject.toml.
- Add pytest when backend feature testing begins, frontend test libraries when
  needed, and Playwright when an end-to-end workflow exists.
- Future UI uses Cloudscape plus review against actual Route 53 screenshots.
- Future auth uses opaque server-side sessions and HttpOnly cookies.
- Future zones are unique by (user_id, normalized name, type). Zone name,
  comment, and type are editable. Record owner names are relative; renaming a
  zone must warn that owner names change while target values remain unchanged.
- DNS validation is assignment-level, not exhaustive RFC implementation.
- Only SIMPLE routing initially. Alias, automatic NS/SOA, and bonuses deferred.
- Never commit secrets, virtual environments, dependencies, or SQLite files.

## Verification

From frontend/: pnpm lint, pnpm typecheck, pnpm build.
From backend/: run python -m uvicorn app.main:app, then GET /health.
Use the backend virtual environment. Additional tests arrive with their phases.

At each phase end, report files changed, commands/checks, results, warnings,
and the resulting source tree. Keep README synchronized.
