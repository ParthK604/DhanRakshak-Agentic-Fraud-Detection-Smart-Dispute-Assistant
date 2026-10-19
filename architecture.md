# Architecture (file design)

_Status legend: [x] exists, [ ] planned_

```
DhanRakshak-.../
├── docs/                     [x] context.md, architecture.md, AI_HISTORY.md, PHASE_HISTORY.md
├── backend/
│   ├── .env                  [x] secrets (gitignored)
│   ├── .env.example          [x]
│   ├── requirements.txt      [x]
│   ├── app/
│   │   ├── main.py           [x] FastAPI app, CORS, lifespan (Mongo connect/close)
│   │   ├── config.py         [x] Settings via pydantic-settings
│   │   ├── db.py             [x] Motor client, get_db(), ping
│   │   ├── routers/
│   │   │   ├── health.py     [x] GET /api/health (PayPal, Mongo, Groq checks)
│   │   │   ├── transactions.py [x] Phase 2
│   │   │   ├── risk.py       [x] Phase 3
│   │   │   ├── disputes.py   [x] Phase 4
│   │   │   └── merchants.py  [x] Phase 5 trust/precheck/list APIs
│   │   ├── repositories/
│   │   │   └── transactions.py [x] typed Mongo transaction repository
│   │   ├── services/
│   │   │   ├── paypal_client.py [x] OAuth token cache + generic request()
│   │   │   ├── llm.py        [x] Groq client + ping
│   │   │   ├── paypal_transactions.py [x] Transaction Search mapper/fetcher
│   │   │   └── features.py   [x] deterministic risk signals and context (Phase 3)
│   │   │   ├── dispute_evidence.py, refunds.py, letter.py, dispute_steps.py
│   │   │   └── dispute_filing.py
│   │   ├── agents/           [x] risk_graph.py, dispute_graph.py, merchant_graph.py
│   │   └── models/           [x] transaction, risk, and dispute Pydantic schemas
│   │   ├── repositories/disputes.py [x] dispute and session persistence
│   ├── scripts/seed_data.py  [x] deterministic seeded scenarios
│   ├── scripts/probe_paypal.py [x] sandbox capability probe
│   ├── scripts/generate_sandbox_activity.py [x] approval-required order
│   ├── scripts/eval_risk.py  [x] seeded risk evaluation
│   ├── scripts/eval_disputes.py [x] deterministic dispute evaluation
│   ├── scripts/demo_dispute_chat.py [x] scripted conversation demo
│   └── tests/                [x] Phase 2 through Phase 5 unit tests
├── frontend/                 [x] Next.js 16 dashboard + AG Grid/AG Charts (Phase 6)
│   ├── app/                  [x] dashboard, transactions, disputes, merchants
│   ├── components/           [x] responsive shell and shared UI states
│   ├── lib/api.ts            [x] typed API client and ApiError
│   ├── lib/api-types.ts      [x] generated from backend OpenAPI
│   └── lib/ag-grid.ts        [x] Community module registration and shared theme
├── postman/                  [ ] collection + environment (Phase 7)
├── render.yaml               [ ] Phase 7
├── LICENSE                   [x] MIT
└── README.md                 [ ] Phase 8
```

## Planned Mongo collections
- `transactions`: unique txn_id, amount, currency, merchant, payee, country/city, timestamp, status, scenario, source (paypal_sandbox | seeded); indexes on txn_id, user/timestamp, user/merchant
- `risk_scores`: txn id, score, level, signals{}, reasoning, model, created_at
- `disputes`: dispute id, txn ids, type, status, letter, refund_amount, steps, timeline[]
- `merchants`: merchant_id, trust_score, trust_level, signals, findings, reasoning,
  cache expiry, LLM/fallback metadata; unique merchant_id, trust_score, updated_at desc

## Planned API surface
- GET  /api/health
- GET  /api/transactions, GET /api/transactions/{txn_id}, POST /api/transactions/sync
- POST /api/transactions/seed and POST /api/transactions/seed/reset (development only)
- POST /api/risk/signals (development/debug, deterministic only)
- POST /api/risk/score, POST /api/risk/score-transaction, POST /api/risk/score-batch
- GET /api/risk/scores, GET /api/risk/scores/{txn_id}, GET /api/risk/summary
- POST /api/disputes/analyze (development/debug, deterministic only)
- POST /api/disputes/chat (stateful agent), GET /api/disputes, GET /api/disputes/{id}
- GET /api/disputes/sessions/{session_id}, POST /api/disputes/{id}/sync-status
- POST /api/disputes/{id}/advance (development prepared-dispute simulation)
- POST /api/merchants/trust, GET /api/merchants
- POST /api/merchants/signals, POST /api/merchants/precheck,
  POST /api/merchants/trust-batch, GET /api/merchants/{merchant_id},
  GET /api/merchants/summary

## Frontend data flow
- `frontend/lib/api.ts` is the single browser API client. It reads
  `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`) and
  `NEXT_PUBLIC_DEMO_USER_ID` (default `demo-user-1`), applies request timeouts,
  and exposes typed endpoint helpers. `frontend/lib/api-types.ts` is generated
  by `npm run gen:api` from `/openapi.json`.
- React Query owns polling, caching, invalidation, and loading/error states.
  AG Grid infinite-row datasources translate grid paging, sorting, and the
  available search/filter controls into the backend's paged list requests.
  Transaction risk records are merged with the visible transaction page.
- `frontend/lib/ag-grid.ts` registers Community modules once and provides the
  shared Quartz theme/default column behavior. AG Grid infinite row model,
  custom renderers, CSV export, selection, and responsive grids are used on
  transactions, disputes, and merchants. AG Charts provides dashboard risk
  distribution and posture visualizations.

## Frontend environment
- `NEXT_PUBLIC_API_BASE_URL`: deployed or local backend base URL.
- `NEXT_PUBLIC_DEMO_USER_ID`: demo user identifier sent to user-scoped APIs.
- Copy `frontend/.env.example` to `frontend/.env.local` for local overrides.

## Agent graphs (LangGraph)
- Risk: load_context -> compute_signals -> llm_reason -> finalize -> persist.
  Rules produce the initial score; Groq may adjust it by at most +/-20, with
  level/action recomputed from the final score. LLM failure falls back to rules.
- Dispute: understand_intent -> fetch_history -> detect_issue -> calc_refund -> draft_letter -> open_dispute -> guide_steps
- Dispute implementation: classify_turn -> resolve_and_match -> prepare_evidence ->
  draft_letter -> explicit confirmation -> file_dispute -> compose_reply. Facts,
  matching, refund math, and letter grounding are deterministic. Session state is
  stored in `dispute_sessions` with a seven-day TTL.
- Merchant: concurrent internal_stats + external_research -> compute_signals ->
  llm_reason -> finalize -> persist. Rules are deterministic; Groq is evidence
  constrained, clamped to +/-20, and falls back to rules. Live URLs go through
  safe_fetch only; fixture mode is offline and page text is untrusted data.

## Env vars
PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_BASE_URL, MONGODB_URI (or MONGO_URI), MONGODB_DB, GROQ_API_KEY, GROQ_MODEL, CORS_ORIGINS, ENABLE_DEV_ENDPOINTS, AUTO_SCORE_ON_SYNC, RISK_LLM_TIMEOUT_SECONDS, DISPUTE_SUBMISSION_MODE, MERCHANT_RESEARCH_MODE, SEARCH_PROVIDER, SEARCH_API_KEY, MERCHANT_CACHE_HOURS, MERCHANT_UNKNOWN_CONFIDENCE_FLOOR

Risk indexes: unique `risk_scores.txn_id` and `(user_id, created_at desc)`.
Dispute indexes: unique `disputes.dispute_id`, `(user_id, created_at desc)`,
unique `dispute_sessions.session_id`, and a seven-day TTL on `updated_at`.

`DISPUTE_SUBMISSION_MODE=paypal` attempts `POST /v1/customer/disputes` in the
PayPal sandbox with an idempotency header. Any failure safely falls back to
`submission_mode=prepared`; prepared means the letter and evidence are saved but
the user must submit them through the PayPal sandbox Resolution Center.

PayPal Transaction Search permits at most a 31-day range per request and newly
created sandbox transactions may take up to several hours to appear. Sync splits
longer ranges and returns an actionable error when the sandbox app lacks permission.