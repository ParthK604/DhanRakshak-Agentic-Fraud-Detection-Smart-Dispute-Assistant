from dataclasses import dataclass

from app.config import get_settings
from app.models.merchant import MerchantSignal


@dataclass(frozen=True)
class MerchantConfig:
    neutral_score: int = 50
    trusted_floor: int = 70
    caution_floor: int = 40
    max_adjustment: int = 20


MERCHANT_CONFIG = MerchantConfig()


def score_signals(signals: list[MerchantSignal]) -> tuple[int, float, list[str], list[str]]:
    available = [signal for signal in signals if signal.available]
    if not available:
        return 50, 0.0, [], []
    adjustment = sum(signal.impact * signal.weight for signal in available if signal.triggered)
    score = max(0, min(100, round(MERCHANT_CONFIG.neutral_score + adjustment)))
    informative = [
        signal for signal in available
        if signal.triggered or signal.direction != "neutral"
    ]
    total_weight = sum(signal.weight for signal in informative)
    confidence = min(1.0, total_weight / 70)
    green = [signal.evidence for signal in available if signal.triggered and signal.direction == "positive"][:4]
    red = [signal.evidence for signal in available if signal.triggered and signal.direction == "negative"][:4]
    return score, round(confidence, 2), green, red


def level_for(score: int, confidence: float) -> str:
    if confidence < get_settings().merchant_unknown_confidence_floor:
        return "unknown"
    return "trusted" if score >= 70 else "caution" if score >= 40 else "high_risk"


def recommendation_for(level: str) -> str:
    return {"trusted": "proceed", "caution": "proceed_with_caution", "high_risk": "avoid", "unknown": "verify_first"}[level]
