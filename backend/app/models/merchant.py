from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MerchantSignal(BaseModel):
    name: str
    source: Literal["internal", "domain", "web", "name"]
    triggered: bool
    direction: Literal["positive", "negative", "neutral"]
    impact: float = Field(ge=-1, le=1)
    weight: float = Field(ge=0)
    value: float | int | str | bool | None = None
    evidence: str
    available: bool


class ResearchFinding(BaseModel):
    type: str
    summary: str
    source_url: str | None = None
    retrieved_at: datetime


class TrustAssessment(BaseModel):
    merchant_id: str
    merchant_name: str
    merchant_url: str | None = None
    trust_score: int = Field(ge=0, le=100)
    trust_level: Literal["trusted", "caution", "high_risk", "unknown"]
    recommendation: Literal["proceed", "proceed_with_caution", "avoid", "verify_first"]
    confidence: float = Field(ge=0, le=1)
    rules_score: int = Field(ge=0, le=100)
    llm_score: int | None = Field(default=None, ge=0, le=100)
    green_flags: list[str] = Field(default_factory=list, max_length=4)
    red_flags: list[str] = Field(default_factory=list, max_length=4)
    signals: list[MerchantSignal]
    findings: list[ResearchFinding]
    reasoning: str
    model: str
    llm_used: bool
    fallback_reason: str | None = None
    research_mode: Literal["live", "fixture"]
    sources_used: list[str]
    latency_ms: int
    created_at: datetime
    expires_at: datetime


class TrustRequest(BaseModel):
    merchant_name: str
    merchant_url: str | None = None
    user_id: str | None = None
    refresh: bool = False


class PrecheckRequest(BaseModel):
    user_id: str
    merchant_name: str
    merchant_url: str | None = None
    amount: float = Field(gt=0)
    currency: str = "USD"


class PrecheckResponse(BaseModel):
    trust: TrustAssessment
    payment_risk_signals: list[dict[str, object]]
    payment_risk_score: int
    combined_verdict: Literal["proceed", "review", "do_not_proceed"]
    combined_reasoning: str


class MerchantPage(BaseModel):
    items: list[TrustAssessment]
    total: int
    page: int
    page_size: int


class MerchantSummary(BaseModel):
    total: int
    by_level: dict[str, int]
    lowest_trust_merchants: list[dict[str, object]]
    common_red_flags: list[dict[str, object]]
