# Repository Guidelines

## Project Structure & Module Organization
- Current files: `README.md`, `LICENSE`, `.gitignore`.
- Preferred layout as the site evolves:
  - `src/` – site code (pages, components, styles).
  - `content/` – Markdown/posts or copy.
  - `public/` – static assets served as-is.
  - `scripts/` – small build/release utilities.
  - `tests/` – automated tests mirroring `src/`.

Example
```
src/
  pages/
  components/
public/
content/
scripts/
tests/
```

## Build, Test, and Development Commands
No tooling is committed yet. Use the matching set below once a stack is chosen:
- Node (e.g., Astro/Next): `npm install`; `npm run dev` (local), `npm run build` (prod), `npm test`.
- Python (e.g., MkDocs/Sphinx): `python -m venv .venv && source .venv/bin/activate`; `pip install -r requirements.txt`; `mkdocs serve`; `mkdocs build`.
Document chosen commands in `README.md` after setup.

## Coding Style & Naming Conventions
- Indentation: 2 spaces for web files; 4 spaces for Python.
- Names: kebab-case for files/assets (`about-me.md`), PascalCase for UI components, snake_case for Python modules/functions.
- Formatting: Prettier for web stacks; Black + Ruff for Python. Add config files (`.prettierrc`, `pyproject.toml`) at repo root.

## Testing Guidelines
- Frameworks: Jest/Vitest for JS/TS; pytest for Python.
- Location: place tests under `tests/` mirroring `src/`.
- Naming: JS/TS `*.test.ts(x)`; Python `test_*.py`.
- Aim for ≥80% coverage on changed code; include snapshot/screenshots for UI when helpful.

## Commit & Pull Request Guidelines
- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`.
- Commits: small, focused, imperative mood (e.g., “feat: add hero section”).
- PRs: clear description, linked issues, before/after screenshots for UI, reproduction steps, and notes on testing/impact.

## Security & Configuration Tips
- Never commit secrets. Use `.env.local` or `.env.development` (ignored) and add `.env.example` with non-sensitive keys.
- Keep dependencies minimal; pin versions for reproducible builds.
- Validate external content and sanitize user input if any dynamic features are added.

## Agent-Specific Notes
- Keep changes scoped and reversible. Follow structure above, update `README.md` when introducing tools, and add minimal CI in a separate PR.

<!-- AGENTS-CLI-STACK-START -->
## CLI Agent Integration

### FastAPI Backend (Chat + SSE)
- Routes: `POST /api/chat` (JSON: `{ messages: [...] }`) and `GET /api/chat/stream?session_id=...` (SSE).
- SSE: respond with `Content-Type: text/event-stream`; events `token`, `done`, `error`.
- CORS: allow `https://deakyne.me` and local dev (`http://localhost:3000`).
- Example:
  - `curl -N "https://deakyne.dev/api/chat/stream?session_id=abc" -H "Authorization: Bearer <API_KEY>"`

### Oso Auth (API-Key Scopes)
- Header: `Authorization: Bearer <API_KEY>`; reject missing/invalid with `401`, insufficient scope with `403`.
- Scopes: `chat:read`, `chat:write`, `analytics:write` (extend as needed).
- Polar sketch (policy.polar):
  - `has_scope(user, "chat:write") if user.scopes.contains("chat:write");`
  - `allow(user, "create", Chat) if has_scope(user, "chat:write");`

### PostHog Analytics (Client/Server)
- Env: `POSTHOG_KEY`, `POSTHOG_HOST` (e.g., `https://us.i.posthog.com`).
- Client (frontend): load PostHog JS, track `pageview`, `chat_submitted`, `chat_token_streamed`.
- Server (FastAPI): use `posthog` Python SDK to `capture` on chat start/end; flush asynchronously after response.
- Respect privacy: anonymize IP, honor Do Not Track.

### Coolify Deployment
- Frontend: `deakyne.me` → static app/service; Backend: `deakyne.dev` → FastAPI service.
- Health checks: expose `GET /healthz` on backend.
- CORS origins in backend env: `CORS_ORIGINS=https://deakyne.me,http://localhost:3000`.
- Set env in Coolify: `POSTHOG_KEY`, `POSTHOG_HOST`, `OSO_POLICY_PATH`, `API_KEYS` (or key store); enable automatic SSL.
<!-- AGENTS-CLI-STACK-END -->
