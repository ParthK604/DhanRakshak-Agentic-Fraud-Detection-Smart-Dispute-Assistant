import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from app.agents.merchant_graph import score_merchant
from app.models.merchant import (
    MerchantPage, MerchantSummary, PrecheckRequest, PrecheckResponse,
    TrustAssessment, TrustRequest,
)
from app.models.schemas import Transaction
from app.repositories import merchants
from app.repositories import transactions
from app.services.features import combine_rules_score, compute_signals
from app.services.merchant_internal import internal_signals, merchant_id
from app.services.merchant_research import research_merchant
from app.services.merchant_scoring import level_for, score_signals
from app.config import get_settings

router = APIRouter(prefix="/api/merchants", tags=["merchants"])


@router.post("/signals", response_model=dict[str, object], summary="Debug merchant trust signals")
async def merchant_signals(request: TrustRequest) -> dict[str, object]:
    """Development/debug endpoint: deterministic merchant signals and research only."""
    rows, _ = await transactions.list_transactions({}, 1, 10000, ("timestamp", 1))
    internal = internal_signals(request.merchant_name, rows)
    external, findings, sources, _ = await research_merchant(request.merchant_name, request.merchant_url)
    signals = internal + external
    score, confidence, green, red = score_signals(signals)
    return {
        "merchant_id": merchant_id(request.merchant_name), "merchant_name": request.merchant_name,
        "signals": signals, "findings": findings, "rules_score": score,
        "confidence": confidence, "level": level_for(score, confidence),
        "research_mode": get_settings().merchant_research_mode,
        "sources_used": sources, "green_flags": green, "red_flags": red,
    }


@router.post("/trust", response_model=TrustAssessment)
async def trust(request: TrustRequest) -> TrustAssessment:
    cached = await merchants.get(merchant_id(request.merchant_name))
    if cached and not request.refresh and cached.expires_at > datetime.now(UTC):
        return cached
    return await score_merchant(request.merchant_name, request.merchant_url, request.user_id)


@router.post("/precheck", response_model=PrecheckResponse)
async def precheck(request: PrecheckRequest) -> PrecheckResponse:
    trust_assessment = await score_merchant(request.merchant_name, request.merchant_url, request.user_id)
    rows, _ = await transactions.list_transactions({"user_id": request.user_id}, 1, 500, ("timestamp", 1))
    hypothetical = Transaction(
        txn_id="precheck-only", user_id=request.user_id, amount=request.amount,
        currency=request.currency, merchant_name=request.merchant_name,
        direction="outgoing", country="US", timestamp=datetime.now(UTC),
        status="PENDING", source="simulated",
    )
    signals = compute_signals(hypothetical, rows)
    risk_score = combine_rules_score(signals)
    triggered = [signal for signal in signals if signal.triggered]
    if trust_assessment.trust_level == "high_risk" or risk_score >= 70:
        verdict = "do_not_proceed"
    elif trust_assessment.trust_level in {"caution", "unknown"} or risk_score >= 35:
        verdict = "review"
    else:
        verdict = "proceed"
    combined = f"Merchant trust is {trust_assessment.trust_level} at {trust_assessment.trust_score}/100; payment rules score is {risk_score}."
    if triggered:
        combined += " Payment signals: " + "; ".join(signal.evidence for signal in triggered[:3])
    return PrecheckResponse(
        trust=trust_assessment,
        payment_risk_signals=[signal.model_dump() for signal in signals],
        payment_risk_score=risk_score,
        combined_verdict=verdict,
        combined_reasoning=combined,
    )


@router.post("/trust-batch", response_model=list[TrustAssessment])
async def trust_batch(merchants_input: list[str] | str) -> list[TrustAssessment]:
    if merchants_input == "all seeded":
        rows, _ = await transactions.list_transactions({}, 1, 10000, ("timestamp", 1))
        names = sorted({row.merchant_name for row in rows})
    elif isinstance(merchants_input, list):
        names = merchants_input
    else:
        raise HTTPException(status_code=400, detail="Body must be a list of merchant names or 'all seeded'")
    semaphore = asyncio.Semaphore(3)
    async def run(name: str) -> TrustAssessment:
        async with semaphore:
            return await score_merchant(name)
    return await asyncio.gather(*(run(name) for name in names))


@router.get("", response_model=MerchantPage)
async def list_merchants(
    q: str | None = None,
    level: str | None = Query(default=None, pattern="^(trusted|caution|high_risk|unknown)$"),
    min_score: int | None = Query(default=None, ge=0, le=100),
    max_score: int | None = Query(default=None, ge=0, le=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> MerchantPage:
    items, total = await merchants.list_assessments({"q": q, "trust_level": level, "min_score": min_score, "max_score": max_score}, page, page_size)
    return MerchantPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/summary", response_model=MerchantSummary)
async def merchant_summary() -> MerchantSummary:
    return await merchants.summary()


@router.get("/{merchant_id}", response_model=TrustAssessment)
async def get_merchant(merchant_id: str) -> TrustAssessment:
    assessment = await merchants.get(merchant_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Merchant assessment not found")
    return assessment
