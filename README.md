# deakyne.me
The personal website of Matt Deakyne

## Backend (FastAPI) — Development with uv

Python dependencies and tasks are managed with `uv` via `pyproject.toml` at the repo root.

- Install dependencies
  - `uv sync`

- Run the dev server
  - `uv run uvicorn backend.app.main:app --reload`

- Run tests
  - `uv run pytest`

Environment
- Set an API key for local testing:
  - `export API_KEYS_JSON='{"test-key":["chat:read","chat:write"]}'`

Endpoints
- Health: `GET /healthz`
- Chat (sync): `POST /api/chat`
- Chat (SSE): `GET /api/chat/stream?session_id=dev1`
