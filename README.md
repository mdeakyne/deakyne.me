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

## Coolify Deployment

This repo includes Dockerfiles for backend and frontend:

- Backend: `Dockerfile.backend` (exposes port 8000)
  - Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`
  - Health: `GET /healthz`
  - Env:
    - `API_KEYS_JSON` (e.g., `{ "prod-key": ["chat:read","chat:write"] }`)
    - `CORS_ORIGINS` (comma-separated, e.g., `https://deakyne.me,http://localhost:3000`)
    - Optional: `POSTHOG_KEY`, `POSTHOG_HOST`, `USE_OSO`, `OSO_POLICY_PATH`

- Frontend: `Dockerfile.frontend` (exposes port 5000)
  - Command: `hypercorn src.frontend.app:app --bind 0.0.0.0:5000`
  - Health: `GET /healthz`
  - Env:
    - `BACKEND_URL` (e.g., `https://deakyne.dev`)
    - `BACKEND_API_KEY` (must exist in backend `API_KEYS_JSON` with `chat:write`)

Coolify steps (two services)
- Connect the GitHub repo in Coolify.
- Create service “backend” using `Dockerfile.backend`.
  - Ports: 8000 exposed; enable health check `/healthz`.
  - Set env: `API_KEYS_JSON`, `CORS_ORIGINS`, `POSTHOG_*` as needed.
- Create service “frontend” using `Dockerfile.frontend`.
  - Ports: 5000 exposed; health check `/healthz`.
  - Set env: `BACKEND_URL` to the backend’s public URL and `BACKEND_API_KEY`.
- Enable SSL for both domains (e.g., `deakyne.dev` for backend and `deakyne.me` for frontend).

Env templates
- Backend: see `.env.backend.example` for placeholders to paste into Coolify.
- Frontend: see `.env.example` for `BACKEND_URL` and `BACKEND_API_KEY`.

Auto-deploy from main (optional)
- Add repository secrets in GitHub:
  - `COOLIFY_WEBHOOK_BACKEND` set to the backend service’s Deploy Webhook URL.
  - `COOLIFY_WEBHOOK_FRONTEND` set to the frontend service’s Deploy Webhook URL.
- A workflow `.github/workflows/coolify-deploy.yml` triggers these webhooks on pushes to `main`.

Local Coolify (port 8000 in use)
- If your Coolify dashboard runs on `http://localhost:8000`, avoid reusing 8000 for the backend service on the host.
- Recommended host port mappings:
  - Backend service: container port 8000 → host port 8081
  - Frontend service: container port 5000 → host port 8082
- Update env when running locally via Coolify:
  - Frontend `BACKEND_URL=http://localhost:8081`
  - Backend `CORS_ORIGINS=http://localhost:8082`
  - Keep API keys in `API_KEYS_JSON` (e.g., `{ "prod-key": ["chat:read","chat:write"] }`).

### Local Docker Compose (Coolify parity)

Run both services locally with the same port mappings/config:

- `docker compose up --build`

This starts:
- Backend at http://localhost:8081 (container port 8000)
- Frontend at http://localhost:8082 (container port 5000)

Defaults in compose (docker-compose.yaml):
- Backend `API_KEYS_JSON` contains `dev-key` with `chat:read,chat:write`.
- Frontend uses `BACKEND_URL=http://backend:8000` (internal network) and `BACKEND_API_KEY=dev-key`.

Adjust env in `docker-compose.local.yml` as needed.
