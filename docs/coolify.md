# Coolify Deployment Fix (Issue #5)

Status: Draft

Goal: Ensure the site/service runs successfully on Coolify with proper health checks, CORS, and env configuration.

Checklist
- [ ] Reproduce the failure on Coolify and capture logs
- [ ] Add `GET /healthz` endpoint on backend (if needed)
- [ ] Validate `CORS_ORIGINS` covers `https://deakyne.me` and local dev
- [ ] Confirm required env vars in Coolify: `POSTHOG_KEY`, `POSTHOG_HOST`, `OSO_POLICY_PATH`, `API_KEYS`
- [ ] Verify automatic SSL and service ports are correct
- [ ] Add/adjust README deployment notes for Coolify

References
- Issue: https://github.com/mdeakyne/deakyne.me/issues/5
- Coolify notes are outlined in the repository guidelines.
