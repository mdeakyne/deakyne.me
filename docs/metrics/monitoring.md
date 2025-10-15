# Metrics Monitoring Guide

This document summarizes how the developer metrics dashboard is assembled and how to inspect data across sources.

## Data Flow Overview

1. **Request Logging**
   - `LoggingMiddleware` enriches each FastAPI request with `response_time_ms`, `status_code`, `user_agent`, `request_id`, and `auth_email` (or `anonymous`).
   - Every log entry is persisted in `api_logs` and mirrored to PostHog via `backend/posthog_client.py`.

2. **Local Aggregation**
   - `metrics_store.refresh_materialized_views()` maintains `daily_metrics` and `endpoint_metrics` tables.
   - Local API endpoints read from these materialized views for low-latency stats and offline resilience.

3. **PostHog Insights**
   - `posthog_insights.py` queries PostHog’s Trends API for endpoint usage, timeline data, and active user counts.
   - Values are combined with local aggregates in `backend/routes/metrics.py` (see `/dashboard` response schema).

4. **Frontend Rendering**
   - `/app/api/metrics/dashboard` proxies the backend payload.
   - `lib/commands.ts` exposes the `metrics` command; ASCII rendering lives in `lib/metrics.ts` with tests in `tests/lib/metrics.test.ts`.

## Verification Checklist

- `backend/.venv/bin/python -m pytest backend/tests -q` (back-end coverage)
- `npm run test` (front-end unit tests)
- `npm run lint` (Next.js ESLint rules)
- Manual smoke test: `npm run dev` + `uv run python backend/main.py` → run `metrics` in the terminal.

## PostHog References

- Capture key (server): `POSTHOG_PROJECT_API_KEY`
- Insights access: `POSTHOG_PROJECT_ID` + `POSTHOG_API_KEY`
- Frontend public key: `NEXT_PUBLIC_POSTHOG_KEY`
- Dashboard URL: `NEXT_PUBLIC_POSTHOG_DASHBOARD_URL`

If PostHog is unavailable, the dashboard gracefully falls back to local aggregates.
