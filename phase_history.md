# Phase History

| # | Phase | Target | Status |
|---|-------|--------|--------|
| 1 | Foundation: docs, config, health check for PayPal/Mongo/Groq   | DONE |
| 2 | PayPal sandbox data layer + Mongo schemas + seed script  | DONE |
| 3 | Layer 1: risk scoring (signals + LangGraph + Groq)  | DONE |
| 4 | Layer 2: dispute agent + PayPal Disputes API  | DONE |
| 5 | Layer 3: merchant trust scoring  | DONE |
| 6 | Next.js dashboard with AG Grid  | PARTIAL |
| 7 | Postman collection, Render deploy, (APIMatic) | todo |
| 8 | Polish, README, tests, demo video, Devpost submission | todo |

## Phase log
(append a short summary after each phase: what shipped, what changed vs plan, known issues)

### Phase 1
- Health is green for PayPal OAuth, MongoDB, and Groq.

### Phase 2
- Shipped typed transaction models, Mongo indexes/repository, PayPal Transaction Search sync/mapping, API endpoints, deterministic seeded scenarios, sandbox probe/activity scripts, and unit tests.
- Deviation: the existing environment uses `MONGO_URI`; settings accept both `MONGO_URI` and `MONGODB_URI`. Transaction Search permission is not enabled in the sandbox app, so sync intentionally returns an actionable 502.
- Known issues: newly created sandbox activity may take up to several hours to appear in Transaction Search; Orders require manual buyer approval before capture.

### Phase 3
- Shipped deterministic risk signals, no-look-ahead history handling, risk persistence, LangGraph scoring, Groq structured-output/JSON fallback, clamp protection, batch scoring, read endpoints, and evaluation tooling.
- Verification: deterministic evaluation and 12 offline tests pass. Final smoke checks passed for health, batch scoring, paged scores, and summary. MongoDB, PayPal, and Groq health were all green.
- Rules-only baseline is documented in EVAL_RISK.md. The full Groq run completed successfully, but reasoning sometimes underweighted deterministic signals (especially velocity); score clamping and fallback behavior remained correct. Duplicate detection remains intentionally informational/low weight for Phase 4 hand-off.

### Phase 4
- Shipped deterministic dispute evidence, fuzzy merchant resolution, duplicate matching, refund calculations, grounded letters, resolution steps, typed dispute/session persistence, stateful chat, explicit confirmation, PayPal filing fallback, status sync, debug/read endpoints, demo/evaluation scripts, and tests.
- Verification: 20 unit tests pass; deterministic dispute evaluation passes 12/12; live duplicate-chat smoke test produced a one-charge refund estimate and required confirmation.
- Submission path: `prepared` after the configured PayPal create attempt returned HTTP 400. The record remains safe and honest; it was not represented as filed. PayPal list/read was available in the earlier probe, while create capability was not confirmed.
- Known issue: the current dispute graph uses the grounded deterministic letter template as the reliable path; an optional LLM letter-drafting enhancement can be added later without weakening grounding verification.

### Phase 5
- Shipped merchant contracts, deterministic internal/external signals, fixture/live
  research selection, SSRF-safe fetching, lookalike detection, rules scoring,
  bounded Groq fallback, cache persistence, merchant APIs, indexes, and a fixture
  evaluator.
- Verification: Checkpoints A and B passed with fixture research and Groq fallback/
  reasoning checks. Rules-only merchant evaluation passes 12/12, the full
  regression suite passes 20 tests, health is green, merchant list/summary/trust/
  precheck endpoints respond correctly, and a suspicious precheck returns
  `do_not_proceed`.
- Known deviations: live RDAP/domain age and an optional search provider are not
  implemented; live research currently uses safe page fetching. Docker-based
  integration validation was unavailable because the local Docker daemon was not
  running. The API-only service was validated with its existing MongoDB instance.

### Phase 6
- Implemented the Next.js 16.4.2 frontend shell, typed OpenAPI client,
  light/dark theme support, health polling, dashboard KPIs/charts, PayPal
  sandbox connection state, transaction risk grid and live scoring panel,
  disputes grid/assistant, and merchant trust/pre-payment-check views.
- Added Community AG Grid module/theming setup, infinite-row datasources,
  custom risk/trust/source/signal renderers, CSV export, drawers, provenance
  labels, explicit dispute confirmation, and friendly sync-error handling.
- Verification: `npm.cmd run gen:api`, `npm.cmd run lint`, and
  `npm.cmd run build` pass. Production HTTP smoke checks returned 200 for
  `/`, `/transactions`, `/disputes`, `/merchants`, and backend `/api/health`.
  Browser smoke checks reached the dashboard, transactions, disputes, and
  merchants views after fixing chart module registration and loading-row
  rendering guards.
- Known gaps: transaction-prefill routing, persistent column layouts/saved
  views, some advanced grid filters, and full browser/runtime validation still
  need follow-up. Backend behavior was not changed in Phase 6.