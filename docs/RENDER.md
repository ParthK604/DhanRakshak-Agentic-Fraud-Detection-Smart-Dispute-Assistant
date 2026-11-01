# Render deployment

## Topology

`Vercel frontend -> Render FastAPI web service -> MongoDB Atlas`, with the backend
also calling PayPal sandbox and Groq. The root `render.yaml` is a Render Blueprint
for the existing `dhanrakshak-agentic-fraud-detection` service.

The Blueprint uses a free web service, `/healthz` health checks, GitHub
auto-deploys on commits to `main`, and environment variables. Secret values use
`sync: false`, so Render prompts for them without putting credentials in source.
Render logs and the optional (paid-plan) cron job are also supported.

## Deploy from scratch

1. Push the repository to GitHub with `main` as the deployed branch.
2. In Render, choose **New -> Blueprint**, select the repository, and confirm the
   preview says it updates the existing service rather than creating a duplicate.
3. Apply the Blueprint and enter `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`,
   `MONGO_URI`, and `GROQ_API_KEY` when prompted.
4. Confirm the non-secret values in `render.yaml`, especially `CORS_ORIGINS`.
5. Set Vercel `NEXT_PUBLIC_API_BASE_URL` to
   `https://dhanrakshak-agentic-fraud-detection.onrender.com` and
   `NEXT_PUBLIC_DEMO_USER_ID` to `demo-user-1`, then redeploy Vercel.
6. Watch the Render deploy log for dependency installation followed by
   `uvicorn app.main:app` listening on the Render `$PORT`.

Free services spin down after roughly 15 minutes without traffic, so the first
request can take up to about a minute. Open the service about a minute before a
demo instead of adding a self-ping job. MongoDB Atlas must allow Render's
outbound addresses (the simple demo setup uses `0.0.0.0/0`), and CORS must
include the exact Vercel origin.

## How to validate

Validate the file with the Render CLI (`render blueprints validate`) if the CLI
is installed, the Render Validate Blueprint API, or a YAML extension configured
with `https://render.com/schema/render.yaml.json`. Local validation can also
confirm YAML syntax, but it cannot prove the dashboard will update the existing
service or that Render credentials work.

Before applying, check:

- `GET /healthz` returns `{"status":"ok"}` without PayPal, MongoDB, or Groq calls.
- `GET /api/health` returns the existing service statuses plus `checked_at` and
  `cached`; an immediate second call reports `"cached": true`.
- `/docs` loads and the Vercel app can list transactions.
- A deploy log shows a successful build, a healthy `/healthz` check, and the
  service becoming live.

## Screenshots for the sponsor submission

- Render service dashboard page
- Blueprint preview showing the existing service update
- A successful deploy log
- Health-check status
- A log line from a scored transaction
