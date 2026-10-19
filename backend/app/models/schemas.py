from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    txn_id: str
    user_id: str
    amount: float
    currency: str
    merchant_name: str
    merchant_id: str | None = None
    payee_email: str | None = None
    direction: Literal["outgoing", "incoming"]
    country: str
    city: str | None = None
    timestamp: datetime
    status: str
    description: str | None = None
    source: Literal["paypal_sandbox", "seeded", "simulated"]
    scenario: str | None = Field(
        default=None,
        description=(
            "Ground-truth test label. It is for deterministic tests and must never "
            "be sent to an LLM."
        ),
    )


class TransactionPage(BaseModel):
    items: list[Transaction]
    total: int
    page: int
    page_size: int


class SyncResult(BaseModel):
    fetched: int
    upserted: int
    source: Literal["paypal_sandbox", "seeded"]
    note: str | None = None


class RiskSignal(BaseModel):
    name: str
    triggered: bool
    severity: float = Field(ge=0, le=1)
    weight: float = Field(ge=0)
    value: float | int | str | bool | None = None
    evidence: str


class RiskAssessment(BaseModel):
    txn_id: str
    user_id: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high"]
    recommended_action: Literal["allow", "review", "block"]
    signals: list[RiskSignal]
    rules_score: int = Field(ge=0, le=100)
    llm_score: int | None = Field(default=None, ge=0, le=100)
    reasoning: str
    reasons: list[str] = Field(max_length=4)
    model: str
    llm_used: bool
    fallback_reason: str | None = None
    latency_ms: int = Field(ge=0)
    created_at: datetime


class RiskPage(BaseModel):
    items: list[RiskAssessment]
    total: int
    page: int
    page_size: int


class RiskSummary(BaseModel):
    total: int
    low: int
    medium: int
    high: int
    average_score: float
    top_signals: list[dict[str, int | str]]


class RiskSignalsResponse(BaseModel):
    txn_id: str
    signals: list[RiskSignal]
    rules_score: int
    risk_level: Literal["low", "medium", "high"]
    context: dict[str, object]


class ScoreRequest(BaseModel):
    txn_id: str
    force: bool = False


class IncomingTransaction(BaseModel):
    txn_id: str
    user_id: str
    amount: float = Field(gt=0)
    currency: str
    merchant_name: str
    merchant_id: str | None = None
    payee_email: str | None = None
    direction: Literal["outgoing", "incoming"] = "outgoing"
    country: str
    city: str | None = None
    timestamp: datetime
    status: str = "COMPLETED"
    description: str | None = None


class ScoreTransactionRequest(BaseModel):
    transaction: IncomingTransaction


class BatchScoreRequest(BaseModel):
    user_id: str
    limit: int = Field(default=50, ge=1, le=500)
    only_unscored: bool = True


class BatchScoreResult(BaseModel):
    scored: int
    skipped: int
    failed: int
