import asyncio
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from app.agents.risk_graph import score_transaction
from app.models.schemas import (
    BatchScoreRequest,
    BatchScoreResult,
    IncomingTransaction,
    RiskAssessment,
    RiskPage,
    RiskSignalsResponse,
    RiskSummary,
    ScoreRequest,
    Transaction,
)
from app.repositories import risk_scores
from app.repositories import transactions as transaction_repository
from app.services.features import build_context, combine_rules_score, compute_signals, risk_level

router = APIRouter(prefix="/api/risk", tags=["risk"])


async def _history(txn: Transaction) -> list[Transaction]:
    rows = await transaction_repository.get_user_history(txn.user_id, until=txn.timestamp)
    return [row for row in rows if row.timestamp < txn.timestamp and row.txn_id != txn.txn_id]


@router.post("/signals", response_model=RiskSignalsResponse, summary="Debug deterministic risk signals")
async def debug_signals(txn_id: str) -> RiskSignalsResponse:
    """Development/debug endpoint: compute signals without making an LLM call."""
    txn = await transaction_repository.get_transaction(txn_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    history = await _history(txn)
    signals = compute_signals(txn, history)
    score = combine_rules_score(signals)
    return RiskSignalsResponse(txn_id=txn_id, signals=signals, rules_score=score, risk_level=risk_level(score), context=build_context(txn, history))


@router.post("/score", response_model=RiskAssessment)
async def score_existing(request: ScoreRequest) -> RiskAssessment:
    cached = await risk_scores.get(request.txn_id)
    if cached and not request.force:
        return cached
    txn = await transaction_repository.get_transaction(request.txn_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return await score_transaction(txn)


@router.post("/score-transaction", response_model=RiskAssessment)
async def score_incoming(transaction: IncomingTransaction) -> RiskAssessment:
    txn = Transaction(**transaction.model_dump(), source="simulated")
    await transaction_repository.upsert_many([txn])
    return await score_transaction(txn)


@router.post("/score-batch", response_model=BatchScoreResult)
async def score_batch(request: BatchScoreRequest) -> BatchScoreResult:
    rows, _ = await transaction_repository.list_transactions(
        {"user_id": request.user_id}, 1, request.limit, ("timestamp", 1)
    )
    semaphore = asyncio.Semaphore(3)
    scored = skipped = failed = 0

    async def score_one(txn: Transaction) -> str:
        async with semaphore:
            if request.only_unscored and await risk_scores.get(txn.txn_id):
                return "skipped"
            for attempt in range(2):
                try:
                    await score_transaction(txn)
                    return "scored"
                except Exception:
                    if attempt == 0:
                        await asyncio.sleep(0.25)
            return "failed"

    results = await asyncio.gather(*(score_one(row) for row in rows))
    for result in results:
        if result == "scored":
            scored += 1
        elif result == "skipped":
            skipped += 1
        else:
            failed += 1
    return BatchScoreResult(scored=scored, skipped=skipped, failed=failed)


@router.get("/scores", response_model=RiskPage)
async def list_scores(
    user_id: str | None = None,
    level: str | None = Query(default=None, pattern="^(low|medium|high)$"),
    min_score: int | None = Query(default=None, ge=0, le=100),
    max_score: int | None = Query(default=None, ge=0, le=100),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> RiskPage:
    if min_score is not None and max_score is not None and min_score > max_score:
        raise HTTPException(status_code=400, detail="min_score cannot exceed max_score")
    items, total = await risk_scores.list_scores(
        {"user_id": user_id, "risk_level": level, "min_score": min_score, "max_score": max_score, "from_date": from_date, "to_date": to_date},
        page, page_size,
    )
    return RiskPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/scores/{txn_id}", response_model=RiskAssessment)
async def get_score(txn_id: str) -> RiskAssessment:
    assessment = await risk_scores.get(txn_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Risk assessment not found")
    return assessment


@router.get("/summary", response_model=RiskSummary)
async def get_summary(user_id: str | None = None) -> RiskSummary:
    return await risk_scores.summary(user_id)
