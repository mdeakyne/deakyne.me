# Developer Metrics Dashboard Implementation Plan

> **For Claude:** Use `${SUPERPOWERS_SKILLS_ROOT}/skills/collaboration/executing-plans/SKILL.md` to implement this plan task-by-task.

**Goal:** Launch a dual-sourced developer metrics dashboard that logs usage locally, streams events into PostHog, and serves combined insights through the terminal `metrics` command.

**Architecture:** Backend middleware records enriched API call data into SQLite and asynchronously mirrors events to PostHog. Aggregation helpers maintain cached daily/endpoint tables locally while analytics endpoints stitch in PostHog insights. The frontend initializes PostHog tracking, exposes a `metrics` command, and renders ASCII analytics panels backed by the combined API payload.

**Tech Stack:** FastAPI, SQLite, python-posthog, httpx, Next.js 14, TypeScript, posthog-js, Vitest.

---

### Task 1: Add PostHog dependencies and configuration scaffolding

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `package.json`
- Modify: `README.md`
- Create: `.env.example` (if it does not exist yet)
- Create: `app/config/posthog.ts` (or similar utility)

**Step 1:** Append `posthog>=3.5.0` to `backend/pyproject.toml` dependencies.

**Step 2:** From `backend/`, run `pip install -e .` to sync the local environment; expect success with the new dependency.

**Step 3:** Add `posthog-js` and `@posthog/react` to the main app dependencies (`npm install posthog-js @posthog/react`); note the updated `package-lock.json`.

**Step 4:** Introduce an `.env.example` (or update it if present) with placeholders for `POSTHOG_PROJECT_API_KEY`, `POSTHOG_HOST`, `NEXT_PUBLIC_POSTHOG_KEY`, and `NEXT_PUBLIC_POSTHOG_HOST`.

**Step 5:** Update `README.md` environment setup instructions to mention the new variables and the PostHog provisioning steps.

**Step 6:** Create `app/config/posthog.ts` that lazily initializes PostHog in the browser using the public env vars; export helpers for capturing terminal command events.

**Step 7:** Run `npm run lint` to ensure the new file passes existing checks.

---

### Task 2: Expand backend logging schema and middleware instrumentation

**Files:**
- Modify: `backend/main.py`
- Create: `backend/logging_middleware.py`
- Create: `backend/tests/test_logging_middleware.py`

**Step 1:** In `backend/main.py`, extend `init_db()` to add `response_time_ms`, `status_code`, `user_agent`, and `request_id` columns to `api_logs`, plus create `daily_metrics` and `endpoint_metrics` tables if they do not exist.

**Step 2:** Build `backend/logging_middleware.py` that wraps requests, stamps `request_id`, measures response time, writes a log row, and returns the updated response.

**Step 3:** Write unit tests in `backend/tests/test_logging_middleware.py` using an in-memory SQLite db to confirm the middleware records the enriched fields.

**Step 4:** Register the middleware in `backend/main.py` and ensure responses include the `X-Request-ID` header.

**Step 5:** Run `pytest backend/tests/test_logging_middleware.py -q` and confirm it fails (RED).

**Step 6:** Implement the middleware functionality until the test passes (GREEN).

**Step 7:** Re-run the test to confirm success, then refactor for clarity without breaking it (REFACTOR).

---

### Task 3: Implement PostHog client and event mirroring

**Files:**
- Create: `backend/posthog_client.py`
- Create: `backend/tests/test_posthog_client.py`
- Modify: `backend/logging_middleware.py`

**Step 1:** Write `backend/posthog_client.py` that initializes a singleton PostHog client from env vars and exposes `capture_api_call(event_payload: dict)` with graceful no-op behavior if PostHog config is missing.

**Step 2:** Update the logging middleware to call `capture_api_call` asynchronously (using `asyncio.create_task` or background tasks) after writing to SQLite.

**Step 3:** Draft tests in `backend/tests/test_posthog_client.py` that monkeypatch PostHog to verify events are constructed and skipped appropriately when keys are absent.

**Step 4:** Run `pytest backend/tests/test_posthog_client.py -q` and confirm the initial failure (RED).

**Step 5:** Implement the client & middleware integration until tests pass (GREEN).

**Step 6:** Re-run the middleware test suite to ensure instrumentation still passes and refactor as needed (REFACTOR).

---

### Task 4: Build local aggregation services

**Files:**
- Create: `backend/metrics_store.py`
- Create: `backend/tests/test_metrics_store.py`
- Modify: `backend/main.py`

**Step 1:** Design `backend/metrics_store.py` with functions to refresh `daily_metrics`/`endpoint_metrics` tables and to compute overview stats (totals, uniques, avg response time, error rate) from SQLite.

**Step 2:** Add helper to `metrics_store` that returns the last refreshed timestamp so callers can decide whether to recalc (e.g., only if older than 15 minutes).

**Step 3:** Write unit tests populating in-memory data to validate refresh logic and metric calculations.

**Step 4:** Run `pytest backend/tests/test_metrics_store.py -q` (RED).

**Step 5:** Implement refresh + query logic until tests pass (GREEN).

**Step 6:** Export a `ensure_metrics_freshness()` function and call it from upcoming API endpoints.

**Step 7:** Re-run the test suite and refactor `metrics_store.py` for readability (REFACTOR).

---

### Task 5: Integrate PostHog Insights and expose metrics API endpoints

**Files:**
- Create: `backend/posthog_insights.py`
- Create: `backend/routes/metrics.py`
- Modify: `backend/main.py`
- Create: `backend/tests/test_metrics_endpoints.py`

**Step 1:** Implement `backend/posthog_insights.py` with helpers that query PostHog’s Trends and Funnels endpoints for timeline, endpoint popularity, and user cohorts; use `httpx.AsyncClient` with API key auth.

**Step 2:** Build `backend/routes/metrics.py` FastAPI router providing:
  - `GET /api/metrics/overview`
  - `GET /api/metrics/endpoints`
  - `GET /api/metrics/timeline`
  - `GET /api/metrics/users`
  Internally combine `metrics_store` data with PostHog responses.

**Step 3:** Register the router in `backend/main.py` and ensure CORS/exposed headers cover new endpoints.

**Step 4:** Write tests in `backend/tests/test_metrics_endpoints.py` using dependency overrides or `respx` to mock PostHog responses and validate combined payload structure.

**Step 5:** Run `pytest backend/tests/test_metrics_endpoints.py -q` to see failures (RED).

**Step 6:** Implement endpoints until tests pass (GREEN).

**Step 7:** Execute `pytest backend/tests -q` to confirm the entire backend suite passes; refactor for clarity (REFACTOR).

---

### Task 6: Emit frontend PostHog events and fetch dashboard data

**Files:**
- Modify/Create: `app/layout.tsx` or equivalent to initialize PostHog provider
- Modify: `components/Terminal.tsx`
- Modify: `lib/commands.ts`
- Create: `lib/metrics.ts`
- Create: `tests/lib/metrics.test.ts`

**Step 1:** Wrap the app with PostHog’s provider (client-side only) pulling values from `NEXT_PUBLIC_POSTHOG_*` env vars.

**Step 2:** Update `components/Terminal.tsx` to initialize PostHog once on mount and capture events (`terminal_command`) when commands execute.

**Step 3:** Extend `lib/commands.ts` with a new `metrics` handler that fetches `/api/metrics/dashboard` (see Task 7) and passes data to a formatter helper.

**Step 4:** Create `lib/metrics.ts` containing pure functions that accept API responses and return formatted ASCII sections (overview panel, endpoint bars, sparkline timeline, percentile trend summary).

**Step 5:** Add Vitest to the project (`npm install -D vitest @testing-library/react @testing-library/jest-dom`) and configure a `test` script in `package.json`.

**Step 6:** Write unit tests in `tests/lib/metrics.test.ts` covering formatter functions for sample payloads.

**Step 7:** Run `npm run test` to watch it fail (RED), implement formatters until tests pass (GREEN), then rerun and refactor (REFACTOR).

**Step 8:** Run `npm run lint` to ensure updated files meet linting rules.

---

### Task 7: Create combined dashboard endpoint and ASCII renderer hookup

**Files:**
- Modify/Create: `backend/routes/metrics.py`
- Modify: `lib/commands.ts`
- Modify: `components/Terminal.tsx`
- Update: `README.md`

**Step 1:** Add `GET /api/metrics/dashboard` endpoint that calls the four metrics endpoints internally (or shared service) and returns a single payload optimized for the terminal renderer.

**Step 2:** Update the `metrics` command to render the ASCII dashboard using the formatter outputs and handle error states (e.g., PostHog unavailable).

**Step 3:** Adjust the terminal welcome/help text to mention the new `metrics` command.

**Step 4:** Update README usage instructions demonstrating how to run the new command and explaining that aggregated data comes from both local SQLite and PostHog.

**Step 5:** Add or update frontend tests if needed to cover the command output formatting.

**Step 6:** Run `npm run test` and `npm run lint` to confirm JavaScript/TypeScript changes pass CI checks.

**Step 7:** Run `pytest backend/tests -q` as a final backend verification.

**Step 8:** Manually exercise the terminal command in dev (`npm run dev`) to capture a PostHog event and validate the dashboard renders without runtime errors.

---

### Task 8: Final verification and documentation polish

**Files:**
- Modify: `README.md`
- Optional docs: `docs/metrics/monitoring.md`

**Step 1:** Document PostHog provisioning steps, free-tier considerations, and the fallback behavior when PostHog is unavailable.

**Step 2:** Note how to refresh aggregated metrics manually (e.g., CLI command or API call) and where the data is stored locally.

**Step 3:** Run `pytest backend/tests -q` and `npm run test` one more time to confirm everything still passes after doc edits.

**Step 4:** Summarize outstanding TODOs or future enhancements in the README or docs (e.g., move to scheduled background jobs).

---

# End of Plan
