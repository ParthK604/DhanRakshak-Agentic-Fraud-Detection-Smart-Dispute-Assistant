from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

IssueType = Literal[
    "duplicate_charge", "unauthorized", "wrong_amount",
    "not_received", "cancelled_subscription", "other",
]
DisputeStage = Literal[
    "understanding", "needs_clarification", "evidence_ready",
    "awaiting_confirmation", "submitted", "no_issue_found",
    "declined", "out_of_scope",
]
SubmissionMode = Literal["paypal", "prepared"]


class DisputeIntent(BaseModel):
    issue_type: IssueType
    merchant_text: str | None = None
    amount: float | None = Field(default=None, gt=0)
    date_hint: date | None = None
    confidence: float = Field(ge=0, le=1)


class EvidenceItem(BaseModel):
    txn_id: str
    amount: float
    currency: str
    merchant_name: str
    timestamp: datetime
    relevance: str


class EvidencePack(BaseModel):
    candidate_txns: list[EvidenceItem]
    matched_txns: list[EvidenceItem]
    timeline: list[str]
    merchant_billing_pattern: str
    risk_summary: str | None = None
    facts: list[str]


class RefundCalculation(BaseModel):
    amount: float = Field(ge=0)
    currency: str
    line_items: list[str]
    basis: str
    disclaimer: str = "Estimate; the final decision rests with PayPal and the merchant."


class DisputeLetter(BaseModel):
    subject: str
    body: str
    grounded: bool


class ResolutionStep(BaseModel):
    order: int
    title: str
    detail: str
    owner: Literal["user", "merchant", "paypal"]
    status: Literal["pending", "current", "complete"] = "pending"


class TimelineEvent(BaseModel):
    event: str
    detail: str
    at: datetime


class DisputeRecord(BaseModel):
    dispute_id: str
    user_id: str
    issue_type: IssueType
    txn_ids: list[str]
    status: Literal["draft", "awaiting_confirmation", "submitted", "declined", "closed"]
    submission_mode: SubmissionMode
    paypal_dispute_id: str | None = None
    evidence: EvidencePack
    refund: RefundCalculation
    letter: DisputeLetter
    steps: list[ResolutionStep]
    timeline: list[TimelineEvent]
    fallback_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    user_id: str
    session_id: str | None = None
    message: str | None = None
    action: Literal["confirm", "cancel", "select_transaction"] | None = None
    payload: dict[str, object] | None = None


class SuggestedAction(BaseModel):
    label: str
    action: str
    payload: dict[str, object] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    stage: DisputeStage
    awaiting_confirmation: bool
    candidates: list[EvidenceItem] = Field(default_factory=list)
    evidence: EvidencePack | None = None
    refund: RefundCalculation | None = None
    letter: DisputeLetter | None = None
    steps: list[ResolutionStep] = Field(default_factory=list)
    dispute_id: str | None = None
    suggested_actions: list[SuggestedAction] = Field(default_factory=list)
    llm_used: bool
    fallback_reason: str | None = None


class DisputePage(BaseModel):
    items: list[DisputeRecord]
    total: int
    page: int
    page_size: int


class DisputeSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    by_issue_type: dict[str, int]
    total_refund_amount: float


class AnalyzeRequest(BaseModel):
    user_id: str
    merchant: str
    issue_type: IssueType
    expected_amount: float | None = Field(default=None, gt=0)
    cancel_date: date | None = None
