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

## Frontend (Quart + HTMX)

This repo includes a minimal Quart app that renders a simple HTMX chat UI and proxies chat requests to the FastAPI backend.

- Install deps (if not already): `uv sync`
- Configure env (copy `.env.example` and adjust):
  - `BACKEND_URL` (default `http://127.0.0.1:8000`)
  - `BACKEND_API_KEY` (must match a key in backend `API_KEYS_JSON`)
- Run backend (in one terminal): `uv run uvicorn backend.app.main:app --reload`
- Run frontend (in another terminal):
  - Using Quart CLI: `uv run quart --app src.frontend.app:app run --reload -p 5000`
  - Or Hypercorn: `uv run hypercorn src.frontend.app:app --reload --bind 127.0.0.1:5000`
- Open: `http://127.0.0.1:5000`

Notes
- The frontend sends a synchronous chat request to the backend and re-renders the chat panel using HTMX.
- For streaming tokens (SSE), we can add a Quart proxy endpoint that forwards the backend SSE stream to the browser; this avoids exposing API keys in the client. Let me know if you want that added.
