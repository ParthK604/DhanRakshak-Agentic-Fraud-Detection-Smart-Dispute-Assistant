# AI History

**Protocol for any AI agent:** read context.md -> architecture.md -> PHASE_HISTORY.md -> this file.
Before you stop (or run out of tokens), append an entry below: what you did, files touched, what is half-done, what to do next.

---

## Entry 1: Claude, planning + Phase 1
- Read hackathon rules; wrote context.md with deadline, judging criteria, prize strategy, submission checklist.
- Created Phase 1 scaffold: config, db, PayPal OAuth client, Groq client, /api/health, docs, .gitignore, LICENSE.
- Not yet verified by running (user must run /api/health and report results).
- Next: Phase 2 (PayPal sandbox data + seed script + Mongo schemas).

## Entry 2: Copilot SDK in VS Code, Phase 2
- Read the existing root-level context, architecture, phase, and AI history docs and inspected the Phase 1 backend.
- Changed: `backend/app/config.py`, `backend/app/db.py`, `backend/app/main.py`, `backend/app/services/paypal_client.py`; added typed schemas, transaction repository/router, PayPal transaction service, deterministic seed/probe/activity scripts, `.env.example`, dev requirements, and tests.
- Environment finding: `.env` uses `MONGO_URI`; config accepts it alongside `MONGODB_URI`. No secret values were added to source or logs.
- PayPal probe (2026-10-18): OAuth token `200`; Transaction Search `403 NOT_AUTHORIZED`; Disputes list `200`; Orders create `200`. Transaction Search must be enabled for the sandbox app. Orders create returns an approval link; buyer approval and capture remain manual. Transaction Search may lag sandbox activity.
- Verification: health is `ok` for PayPal, MongoDB, and Groq; seed reset + seed twice prints stable 45-row scenario summary; filtered transaction API returns duplicate Netflix rows; sync returns an actionable 502; pytest passes (5 tests).
- Next Phase 3 steps: implement deterministic risk features using repository history functions, keep `scenario` out of all LLM input, then add risk persistence and scoring endpoints.

## Entry 3: Copilot SDK in VS Code, Phase 3
- Added deterministic features, risk schemas, LangGraph agent, risk-score repository, risk router, evaluator, and offline tests; extended config, indexes, and main router registration.
- Model: `GROQ_MODEL` remains `openai/gpt-oss-120b`. The implementation requests Groq JSON Schema output first and retries with JSON mode when schema output is unsupported; every response is validated with Pydantic.
- Tuning: merchant median after three observations, overall median fallback, velocity thresholds, geographic history, and low-weight `possible_duplicate`. Final LLM score is clamped to rules score +/-20.
- Verification: `pytest -q` passes with 12 tests; `python -m scripts.eval_risk --rules-only` passes with baseline 100% low, unusual amount medium, new-payee/suspicious-merchant high, and velocity mostly medium. Live Groq latency/rate-limit behavior still needs Checkpoint B.
- Next Phase 4: reuse persisted `possible_duplicate` assessments as a hand-off hint for the dispute agent, then implement intent understanding, transaction evidence retrieval, refund calculation, dispute-letter drafting, and PayPal Disputes integration.

## Entry 4: Copilot SDK in VS Code, Phase 4
- Added dispute models, evidence/refund/letter/steps services, dispute repository and session TTL, `dispute_graph.py`, filing service, dispute router, seed scenarios, demo/evaluation scripts, tests, and docs.
- PayPal findings: the Phase 2 probe recorded OAuth 200, Disputes list 200, and no confirmed create permission. Official create reference: https://developer.paypal.com/api/customer-disputes/v1/. During the Phase 4 smoke test, `POST /v1/customer/disputes` returned HTTP 400, so the actual working mode is `prepared` fallback. No reply claims PayPal filing in this mode.
- Dispute process note: the implementation intentionally avoids unsupported time-limit claims. It directs users to the PayPal sandbox Resolution Center and preserves the official API reference for the create route.
- Verification: 20 tests pass; `python -m scripts.eval_disputes --no-llm` passes 12/12; live chat required explicit confirmation, attempted PayPal create with idempotency, and retained a prepared dispute after the API error.
- Tuning: fallback intent parsing now handles duplicate-payment wording, cancellation phrasing, wrong-amount wording, unauthorized wording, and known merchant names. `possible_duplicate` remains the Layer 1 hand-off signal.
- Next Phase 5: add deterministic merchant history/trust features, a merchant trust score model and repository, explainable Groq reasoning with fallback, and a confirmation-safe merchant trust endpoint.

## Entry 5: Copilot SDK in VS Code, Phase 5 DONE
- Added merchant models, internal/research/scoring services, SSRF-safe fetching,
  fixture catalog, graph, repository, router, indexes, evaluator, and docs.
- Fixture rules evaluation passes 12/12; established merchants are trusted,
  new legitimate merchants are caution, suspicious/lookalike/scam merchants are
  high risk, and no-data merchants are unknown. Existing tests pass 20/20.
- Safe fetching is the only live third-party path and rejects restricted IP
  ranges with redirect and response caps. Live RDAP/domain age and the optional
  search provider remain future work.
- Checkpoint A and Checkpoint B passed with fixture mode active; Groq reasoning,
  cache/refresh, fallback, prompt-injection resistance, and SSRF behavior were
  manually verified. Checkpoint C automation passed: evaluator 12/12, pytest
  20/20, health green, trust/list/summary/precheck smoke checks green, and the
  suspicious precheck returned `do_not_proceed`.
- Live page research is implemented through the SSRF-safe fetcher. RDAP/domain
  age and an optional search provider remain documented future work. Docker was
  unavailable during final validation because its daemon was not running.
- Phase 6 should consume merchant trust, precheck, batch, paged list, detail, and
  summary endpoints together with the existing risk/dispute list and summary
  response shapes.

## Entry 6: Copilot SDK in VS Code, Phase 6 frontend implementation
- Added the Next.js 16.4.2 dashboard under `frontend/` with React 19.3.0,
  `@tanstack/react-query` 5.x, AG Grid Community 34.x, AG Charts 13.x,
  `lucide-react`, `next-themes`, `sonner`, and `openapi-typescript`.
- Added the typed API wrapper and generated `frontend/lib/api-types.ts`,
  shared AG Grid registration/theme, responsive shell, health indicator,
  dashboard, transactions, disputes, and merchants pages. Added
  `frontend/.env.example`; local values belong in the ignored `.env.local`.
- The UI surfaces transaction source, dispute submission mode, merchant
  research mode, model/fallback metadata, reasoning, and actionable PayPal
  sync errors. No backend behavior was changed during Phase 6.
- Verification completed: `npm.cmd run gen:api`, `npm.cmd run lint`, and
  `npm.cmd run build` all exited 0. The build uses Next.js 16.4.2 Turbopack
  and prerenders all four application routes successfully.
- Runtime validation found and fixed two frontend-only issues: the dashboard
  now registers AG Charts Community modules through the shared registration
  module, and transaction loading rows no longer pass undefined amounts/status
  values into renderers. The rebuilt production server returned 200 for all
  four frontend routes and browser snapshots rendered all four views.
- Half-done: browser runtime/checkpoint validation is still pending; the
  transaction-prefill dispute route, persistent column state/saved views,
  advanced date/amount filters, and some richer timeline/download polish are
  not yet complete.
- Phase 7 next steps: generate and verify a Postman collection from the
  backend OpenAPI document; deploy backend and frontend to Render; configure
  the frontend's `NEXT_PUBLIC_API_BASE_URL` to the deployed backend URL and
  `NEXT_PUBLIC_DEMO_USER_ID` to the demo account; then optionally evaluate
  APIMatic. Re-run OpenAPI generation after any deployed contract change.