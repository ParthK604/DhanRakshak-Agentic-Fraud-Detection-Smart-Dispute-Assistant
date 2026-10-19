from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.agents.dispute_graph import chat
from app.models.dispute import (
    AnalyzeRequest, ChatRequest, ChatResponse, DisputePage, DisputeRecord,
    DisputeSummary, EvidencePack, DisputeIntent,
)
from app.repositories import disputes
from app.repositories import transactions
from app.services.dispute_evidence import build_evidence_pack, find_duplicates, resolve_merchant
from app.services.dispute_filing import sync_status
from app.services.dispute_steps import resolution_steps
from app.services.refunds import calculate_refund

router = APIRouter(prefix="/api/disputes", tags=["disputes"])


@router.post("/analyze", response_model=ChatResponse, summary="Debug deterministic dispute analysis")
async def analyze(request: AnalyzeRequest) -> ChatResponse:
    """Development/debug endpoint: analyze evidence and refund without an LLM or filing."""
    rows, _ = await transactions.list_transactions({"user_id": request.user_id}, 1, 500, ("timestamp", -1))
    merchant = resolve_merchant(request.merchant, sorted({row.merchant_name for row in rows}))
    if merchant is None:
        return ChatResponse(
            session_id="debug", reply="No matching merchant found.", stage="no_issue_found",
            awaiting_confirmation=False, llm_used=False,
        )
    candidates = [row for row in rows if row.merchant_name == merchant]
    pairs = find_duplicates(request.user_id, merchant, rows)
    if request.issue_type == "duplicate_charge":
        matched_ids = {item.txn_id for pair in pairs for item in pair[:2]}
        matched = [row for row in candidates if row.txn_id in matched_ids]
        target = matched[0] if matched else (candidates[0] if candidates else None)
    else:
        matched = candidates[:1]
        target = matched[0] if matched else None
    if target is None:
        return ChatResponse(session_id="debug", reply="No matching transaction found.", stage="no_issue_found", awaiting_confirmation=False, llm_used=False)
    intent = DisputeIntent(issue_type=request.issue_type, merchant_text=merchant, confidence=1)
    evidence = build_evidence_pack(
        target, rows, intent, expected_amount=request.expected_amount, cancel_date=request.cancel_date
    )
    if request.issue_type == "duplicate_charge" and not evidence.matched_txns:
        return ChatResponse(session_id="debug", reply="No duplicate found.", stage="no_issue_found", awaiting_confirmation=False, candidates=evidence.candidate_txns, evidence=evidence, llm_used=False)
    refund = calculate_refund(request.issue_type, evidence, {"expected_amount": request.expected_amount} if request.expected_amount else {})
    from app.services.letter import template_letter
    letter = template_letter(request.issue_type, evidence, refund)
    return ChatResponse(
        session_id="debug", reply=f"Evidence ready. Estimated refund: {refund.amount:.2f} {refund.currency}.",
        stage="evidence_ready", awaiting_confirmation=False, candidates=evidence.candidate_txns,
        evidence=evidence, refund=refund, letter=letter,
        steps=resolution_steps(request.issue_type), llm_used=False,
    )


@router.post("/chat", response_model=ChatResponse)
async def dispute_chat(request: ChatRequest) -> ChatResponse:
    """Run one stateful dispute-assistant turn. Filing requires action=confirm."""
    return await chat(request)


@router.get("", response_model=DisputePage)
async def list_disputes(
    user_id: str | None = None,
    status: str | None = None,
    issue_type: str | None = None,
    submission_mode: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> DisputePage:
    items, total = await disputes.list_records(
        {"user_id": user_id, "status": status, "issue_type": issue_type, "submission_mode": submission_mode},
        page, page_size,
    )
    return DisputePage(items=items, total=total, page=page, page_size=page_size)


@router.get("/summary", response_model=DisputeSummary)
async def dispute_summary(user_id: str | None = None) -> DisputeSummary:
    return await disputes.summary(user_id)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, object]:
    session = await disputes.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Dispute session not found")
    session.pop("_id", None)
    return session


@router.get("/{dispute_id}", response_model=DisputeRecord)
async def get_dispute(dispute_id: str) -> DisputeRecord:
    record = await disputes.get(dispute_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Dispute not found")
    return record


@router.post("/{dispute_id}/sync-status", response_model=DisputeRecord)
async def sync_dispute_status(dispute_id: str) -> DisputeRecord:
    record = await disputes.get(dispute_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Dispute not found")
    try:
        record = await sync_status(record)
    except Exception as exc:
        record.fallback_reason = f"Status sync failed: {str(exc)[:200]}"
    return await disputes.save(record)


@router.post("/{dispute_id}/advance", response_model=DisputeRecord)
async def advance_prepared_dispute(dispute_id: str, status: str = Query(default="under_review")) -> DisputeRecord:
    if not get_settings().enable_dev_endpoints:
        raise HTTPException(status_code=404, detail="Not found")
    record = await disputes.get(dispute_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if record.submission_mode == "paypal":
        raise HTTPException(status_code=409, detail="Cannot demo-advance a PayPal dispute")
    record.timeline.append(__import__("app.models.dispute", fromlist=["TimelineEvent"]).TimelineEvent(
        event="demo_simulation", detail=f"Prepared dispute moved to {status}.", at=datetime.now(UTC)
    ))
    record.status = "closed" if status == "closed" else "submitted"
    record.updated_at = datetime.now(UTC)
    return await disputes.save(record)
