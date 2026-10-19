# DhanRakshak — Project Context

> Read this first. Then architecture.md, PHASE_HISTORY.md, AI_HISTORY.md.

## What it is
**DhanRakshak: Agentic Fraud Detection + Smart Dispute Assistant**, built for the PayPal AI Hackathon (Devpost).
An AI layer on top of PayPal (sandbox) that (1) scores every transaction for fraud risk with reasoning,
(2) resolves disputes end-to-end via an agent, and (3) scores merchant trust before a user pays a new merchant.

## Layers
1. **Real-time risk scoring**: signals: unusual amount for merchant, new payee + large amount, geographic anomaly, velocity. Output: risk score (0-100), level, reasons.
2. **Agentic dispute assistant**: user says "I was charged twice for Netflix" -> agent fetches history, detects duplicate, drafts dispute letter with evidence, calculates refund, guides next steps (PayPal Disputes API sandbox).
3. **Merchant trust score**: before paying a new merchant, agent checks transaction patterns/research and returns trust score + reasoning.

## Design principle
Signals are computed deterministically in code (testable, cheap). The LLM does reasoning, explanation, drafting and tool orchestration. Never let the LLM invent transaction data.

## Stack
FastAPI | LangGraph | Groq (non-Llama model, set via GROQ_MODEL) | PayPal REST sandbox (Transaction Search + Disputes) | MongoDB | Next.js + AG Grid | Postman | Render | (optional) APIMatic

## Hackathon facts (from official rules)
- Submission deadline: **Nov 12, 2026, 12:00 pm PST** (= Nov 13, 1:30 am IST). Internal target: submit by Nov 10.
- PayPal integration must be central; AI tool of our choice.
- Judging (equal weight): Technological Implementation, Design, Potential Impact, Innovation, Presentation.
- Prizes we are targeting: Grand prizes + honorable mentions (Best Use of PayPal + AI, Agentic Commerce) + sponsor prizes: AG Grid, Render, (APIMatic). A project can win at most ONE sponsor prize.
- Postman is a listed sponsor tool but has no prize in the prize table; use it for API testing/docs only.

## Submission checklist (non-negotiable)
- [ ] Public GitHub repo with an open-source LICENSE visible in About
- [ ] No secrets committed (.env is gitignored)
- [ ] README with complete setup/run instructions + test credentials/sandbox notes, and/or hosted demo URL
- [ ] Working demo (not a mockup)
- [ ] Demo video < 3 min, public on YouTube, no copyrighted music/trademarks
- [ ] Text description of features
- [ ] Sponsor-prize requirements checked on Devpost for each sponsor we claim

## Conventions
- Python 3.11+, async everywhere, Pydantic models for all API I/O.
- Config only via `app/config.py` (env vars). Never read os.environ elsewhere.
- Every phase ends by updating PHASE_HISTORY.md, AI_HISTORY.md, and architecture.md if files changed.