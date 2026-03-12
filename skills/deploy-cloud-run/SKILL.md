---
name: deploy-cloud-run
description: Deploy and operate the backend on Google Cloud Run with Cloud SQL integration. Use when tasks involve `my-awesome-agent/deploy.sh`, Docker image/runtime behavior, environment variable wiring, secret injection, or production rollout verification.
---

# Deploy Cloud Run

Deploy backend safely with repeatable Cloud Run and Cloud SQL configuration.

## Use This Workflow

1. Inspect deployment and container definitions first.
- `my-awesome-agent/deploy.sh`
- `my-awesome-agent/Dockerfile`
- `my-awesome-agent/start.sh`
- `my-awesome-agent/app/local.env.example`

2. Verify deployment assumptions.
- Confirm project, region, and Cloud SQL instance names match target environment.
- Confirm secret names for DB user/password/name are correct.
- Confirm app expects DB host via Unix socket when Cloud SQL is enabled.

3. Run deployment.
- Preferred: execute `deploy.sh` from `my-awesome-agent` after updating env-specific values.
- If deploying manually, mirror `gcloud run deploy` flags from `deploy.sh`.

4. Validate post-deploy.
- Check Cloud Run service revision health.
- Verify `/health` endpoint.
- Verify `/config/stages` returns stage metadata.
- Verify WebSocket connectivity from frontend environment.

## Guardrails

- Do not hardcode secrets in source files.
- Keep `USE_DB`, `USE_CLOUD_SQL`, and DB env vars mutually consistent.
- Keep region/model compatibility in mind when changing `GOOGLE_CLOUD_LOCATION`.
- Keep rollback simple: retain prior stable revision until smoke checks pass.
