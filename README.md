# DhanRakshak: Agentic Fraud Shield + Smart Dispute Assistant

> *DhanRakshak* means "wealth protector". An agentic layer on top of **PayPal (sandbox)** that scores every payment's fraud risk in real time, resolves disputes with evidence-backed letters and refund estimates, and rates merchants' trustworthiness **before** you pay.

Built for the **PayPal AI Hackathon**.

| | |
|---|---|
| Live demo | https://dhan-rakshak-agentic-fraud-detectio.vercel.app/ |
| API docs (Swagger) | https://dhanrakshak-agentic-fraud-detection.onrender.com/docs |
| Demo video | (https://youtu.be/o3LBvWKaS3c?si=pZDdNrM721otzDeZ) |

> The backend runs on Render's free tier, which sleeps when idle. The first request can take up to a minute to wake it up.

---

## What it does

DhanRakshak has three layers, all visible in one dashboard.

1. **Layer 1: Real-time risk scoring.** Every transaction gets a 0-100 risk score, a level (low / medium / high), a recommended action (allow / review / block), the signals that fired, and plain-language reasoning. Signals: unusual amount for the merchant, new payee plus large amount, geographic anomaly, and velocity (too many payments too fast). A "possible duplicate" hint feeds Layer 2.
2. **Layer 2: Smart dispute assistant.** A multi-turn agent. Tell it *"I was charged twice for a subscription"* and it fetches your history, finds the duplicate, calculates the refund, drafts a dispute letter backed by evidence, and guides you through the resolution steps. **Nothing is filed until you press Confirm.**
3. **Layer 3: Merchant trust scoring.** Before paying a new merchant, a pre-payment check returns a trust score (0-100) with green and red flags, a confidence value, a recommendation, and a combined verdict with the Layer 1 payment risk.

---

## How we use PayPal

The backend integrates the **PayPal developer platform (free sandbox)** through its REST APIs.

| PayPal API | What it does in DhanRakshak |
|---|---|
| OAuth 2.0 (client credentials) | Authenticates every call; the token is cached and refreshed automatically. |
| Transaction Search (reporting) | `POST /api/transactions/sync` pulls sandbox account activity into our store (`source = paypal_sandbox`), idempotent by transaction id. |
| Orders v2 | `scripts/generate_sandbox_activity.py` creates and captures sandbox payments so the demo has real PayPal activity. |
| Disputes | The dispute agent reads PayPal disputes and attempts to file one after the user confirms. |

**What works and what does not (we say it plainly in the product):**
- PayPal filing unavailable; dispute prepared locally: Client error '400 Bad Request' for url 'https://api-m.sandbox.paypal.com/v1/customer/disputes' For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400
- PayPal sandbox cannot produce every scenario a fraud system needs (geographic anomalies, velocity bursts, duplicate charges). We therefore also load a **deterministic seeded dataset**, labelled `seeded` or `simulated` everywhere in the UI. Seeded data is never presented as PayPal data.

---

## How we use AI

- **Model:** Groq-hosted Groq — OpenAI GPT-OSS 120B for reasoning in all three layers (risk explanations, understanding dispute requests and drafting replies, merchant trust summaries).
- **Orchestration:** **LangGraph** workflows:
  - Risk: load history, compute signals, LLM reasoning, finalize, persist.
  - Disputes: understand intent, fetch and match transactions, calculate refund, draft letter, **wait for confirmation**, file, guide next steps (state persisted per session).
  - Merchants: resolve merchant, internal stats and external research in parallel, score, LLM reasoning, finalize, persist.
- **Design principle: code owns the facts, the model owns the language.** Signals, duplicate matching and refund math are deterministic, tested code. The model never invents transactions, amounts, IDs or merchants.
- **Guardrails:**
  - The LLM score can move only within **+/-20** of the rules score (both are recorded).
  - Structured output is validated with Pydantic; invalid output gets one retry, then a **rules-only fallback**. Endpoints never fail because a model call failed.
  - Dispute letters are checked so every amount and transaction ID exists in the evidence.
  - Web content and user text are treated as **untrusted data** (prompt-injection guard); the model never sees internal test labels.
  - Merchant research uses an **SSRF-safe fetcher** (blocks private, loopback and link-local addresses, re-checks redirects, size and time caps).
  - No look-ahead: scoring a past transaction only uses history from before it.
  - Human-in-the-loop: filing requires an explicit Confirm action.

---

## Architecture

```
                 +---------------------+
   Browser  ---> |  Next.js dashboard  |   (Vercel)
                 |  AG Grid + AG Charts|
                 +----------+----------+
                            | REST (JSON)
                 +----------v----------+        +------------------+
                 |  FastAPI backend    | -----> | PayPal sandbox   |
                 |  LangGraph agents   |        | OAuth, Txn Search|
                 |  (Render)           |        | Orders, Disputes |
                 +----+----------+-----+        +------------------+
                      |          |
              +-------v--+   +---v------+
              | MongoDB  |   |  Groq    |
              | Atlas    |   |  LLM API |
              +----------+   +----------+
```

---

## Tech stack and sponsor integrations

| Area | Technology |
|---|---|
| Backend | Python, FastAPI, Pydantic, httpx, Motor (async MongoDB) |
| Agents / AI | LangGraph, Groq |
| Database | MongoDB Atlas |
| Payments | PayPal sandbox REST APIs |
| Frontend | Next.js (App Router), TypeScript, React, Tailwind CSS |
| **AG Grid** (sponsor) | AG Grid Community + AG Charts Community |
| **Render** (sponsor) | Backend hosting |
| **Postman** (sponsor tool) | API collection and tests |
| Hosting | Render (API), Vercel (frontend) |

### AG Grid
Every data view (Transactions, Disputes, Merchants) is an AG Grid:
- **Infinite row model** against our paginated API, with server-side sorting and filtering.
- **Custom cell renderers:** risk meter, signal chips with evidence tooltips, trust meter, source and submission-status badges.
- Saved views (one-click presets), a column chooser, persisted column layout with a reset button, row flash on newly scored rows, CSV export of loaded rows.
- A themed grid that follows light and dark mode.
- **AG Charts** powers the risk distribution and risk posture charts on the Overview.
  

### Render
- The FastAPI backend is deployed on Render with GitHub auto-deploy and secrets stored as environment variables.
- A lightweight `/healthz` endpoint is used for health checks.  The service is defined as a Blueprint in [`render.yaml`](render.yaml).
  

### Postman
-  [`postman/`](postman/) contains a collection generated from the OpenAPI spec, with local and Render environments and test scripts for the main flows (health, transactions, risk scoring, dispute chat, merchant trust and pre-payment check).

---
 
## Project structure
 
```
.
+-- backend/
|   +-- app/
|   |   +-- main.py, config.py, db.py
|   |   +-- routers/        health, transactions, risk, disputes, merchants
|   |   +-- services/       paypal client, LLM client, risk signals, dispute evidence,
|   |   |                   refunds, letters, merchant research, safe fetcher
|   |   +-- agents/         risk_graph, dispute_graph, merchant_graph (LangGraph)
|   |   +-- models/         Pydantic schemas
|   |   +-- repositories/   MongoDB access
|   +-- scripts/            seed_data, probe_paypal, generate_sandbox_activity,
|   |                       eval_risk, eval_disputes, eval_merchants, demo_dispute_chat
|   +-- tests/
|   +-- requirements.txt
+-- frontend/               Next.js app (pages, components, lib)
+-- context.md  architecture.md  ai_history.md  phase_history.md
+-- EVAL_RISK.md  EVAL_DISPUTES.md  EVAL_MERCHANTS.md
+-- render.yaml  postman/   [EDIT: keep only if present]
+-- LICENSE
```
 
---

## Setup

### Prerequisites
- Python 3.11 or newer (deployed on 3.14) and Node.js 20 or newer
- A free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster (allow your IP in Network Access)
- A free [PayPal Developer](https://developer.paypal.com/) account with a **Sandbox** app (Client ID and Secret). To pull real sandbox activity, enable **Transaction Search** for that app in the developer dashboard.
- A [Groq](https://console.groq.com/) API key

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows (PowerShell):   .venv\Scripts\Activate.ps1
# macOS / Linux:          source .venv/bin/activate

pip install -r requirements.txt
```

Create `backend/.env` (copy `backend/.env.example` and fill it in; **never commit this file**):

```dotenv
PAYPAL_CLIENT_ID=your-sandbox-client-id
PAYPAL_CLIENT_SECRET=your-sandbox-secret
PAYPAL_BASE_URL=https://api-m.sandbox.paypal.com
MONGODB_URI=mongodb+srv://USER:PASSWORD@CLUSTER.mongodb.net/?appName=dhanrakshak
MONGODB_DB=dhanrakshak
GROQ_API_KEY=your-groq-key
GROQ_MODEL=your-groq-model-name
CORS_ORIGINS=http://localhost:3000
```

Load the demo data and start the API:

```bash
python -m scripts.seed_data        # deterministic seeded dataset (safe to re-run)
uvicorn app.main:app --reload      # http://localhost:8000
```

Open `http://localhost:8000/docs` for the interactive API and `http://localhost:8000/api/health` to check PayPal, MongoDB and Groq connectivity.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local         # Windows: copy .env.example .env.local
npm run dev                        # http://localhost:3000
```

`frontend/.env.local`:

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_DEMO_USER_ID=demo-user-1
```

### 3. Optional: real PayPal sandbox data

```bash
python -m scripts.probe_paypal                  # checks OAuth, Transaction Search, Disputes access
python -m scripts.generate_sandbox_activity     # creates sandbox orders (needs buyer approval, see script header)
```

Then use **Sync from PayPal sandbox** in the dashboard (or `POST /api/transactions/sync`). New sandbox activity can take a while to appear in Transaction Search.

### 4. Tests and evaluations

```bash
cd backend
pytest                                   # offline unit tests
python -m scripts.eval_risk              # labelled fraud scenarios (add --rules-only to skip the LLM)
python -m scripts.eval_disputes          # dispute agent on labelled messages
python -m scripts.eval_merchants         # merchant trust on labelled fixtures
```

Results are saved in `EVAL_RISK.md`, `EVAL_DISPUTES.md` and `EVAL_MERCHANTS.md`.

---

## Environment variables

| Variable | Purpose |
|---|---|
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | PayPal sandbox app credentials |
| `PAYPAL_BASE_URL` | PayPal API base (default: sandbox) |
| `MONGODB_URI` (alias `MONGO_URI`), `MONGODB_DB` | MongoDB connection and database name |
| `GROQ_API_KEY`, `GROQ_MODEL` | LLM access and model name |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `DISPUTE_SUBMISSION_MODE` | `paypal` (try real filing, fall back to prepared) or `prepared` |
| `MERCHANT_RESEARCH_MODE` | `live` or `fixture` (recorded research data, for repeatable demos and tests) |
| `ENABLE_DEV_ENDPOINTS` | Enables dev-only seed/demo endpoints (keep `false` in production) |
| `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_DEMO_USER_ID` | Frontend config |

---

## API overview

Full interactive docs at `/docs` (OpenAPI at `/openapi.json`).

| Area | Endpoints |
|---|---|
| Health | `GET /healthz`, `GET /api/health` |
| Transactions | `GET /api/transactions`, `GET /api/transactions/{txn_id}`, `POST /api/transactions/sync` |
| Risk (Layer 1) | `POST /api/risk/score`, `POST /api/risk/score-transaction`, `POST /api/risk/score-batch`, `GET /api/risk/scores`, `GET /api/risk/summary` |
| Disputes (Layer 2) | `POST /api/disputes/chat`, `GET /api/disputes`, `GET /api/disputes/{id}`, `GET /api/disputes/summary`, `POST /api/disputes/{id}/sync-status` |
| Merchants (Layer 3) | `POST /api/merchants/trust`, `POST /api/merchants/precheck`, `GET /api/merchants`, `GET /api/merchants/summary` |

---

## Try it (2-minute tour)

1. **Overview:** KPI cards, risk charts and the PayPal connection card.
2. **Transactions:** in *Live risk scoring*, simulate a payment to a new payee in a new country for a large amount. Watch it flagged high risk, then open the row to see the signals and reasoning.
3. **Disputes:** tell the assistant *"I was charged twice for [a seeded subscription merchant]"*. Review the evidence, refund estimate and letter, then press **Confirm**. Note the honest filing status.
4. **Merchants:** run a pre-payment check on a suspicious merchant (expect **Avoid**) and an established one (expect **Proceed**).

---

## Honesty and limitations

- Demo data is **seeded and simulated**, and labelled as such in the UI. Everything runs against PayPal's **sandbox**, never real money.
- A dispute is only shown as **Filed with PayPal** if PayPal's API actually accepted it; otherwise it is **Prepared, not filed**.
- Refund amounts are **estimates**; the final decision rests with PayPal and the merchant.
- Merchant research in demo mode may use recorded fixtures (shown as `Fixture` in the UI). Live research currently covers safe page fetching and domain checks; richer sources such as domain age lookups are future work.
- Free-tier hosting: cold starts on the first request, and a rate limit protects the shared model quota.

---

## Project docs

- [`context.md`](context.md): what the project is and the rules we followed
- [`architecture.md`](architecture.md): file design, collections and endpoints
- [`phase_history.md`](phase_history.md) and [`ai_history.md`](ai_history.md): how it was built, phase by phase
- `EVAL_*.md`: evaluation results

## License

MIT. See [`LICENSE`](LICENSE).
