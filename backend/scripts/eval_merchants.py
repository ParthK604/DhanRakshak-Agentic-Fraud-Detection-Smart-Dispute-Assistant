import argparse
import asyncio
import os
from dataclasses import dataclass

from app.services.merchant_internal import internal_signals
from app.services.merchant_research import research_merchant
from app.services.merchant_scoring import level_for, score_signals


@dataclass(frozen=True)
class Case:
    name: str
    expected: str


CASES = [
    Case("Acme Hardware", "trusted"),
    Case("New Local Books", "caution"),
    Case("Paypa1 Support", "high_risk"),
    Case("Flash Prize Outlet", "high_risk"),
    Case("Northstar Electronics", "caution"),
    Case("Electrolux Global Shop", "high_risk"),
    Case("Netflix", "unknown"),
    Case("Spotify", "unknown"),
    Case("Amazon", "unknown"),
    Case("Whole Foods", "unknown"),
    Case("QuickCart", "unknown"),
    Case("City Utilities", "unknown"),
]


async def evaluate() -> int:
    os.environ["MERCHANT_RESEARCH_MODE"] = "fixture"
    passed = 0
    for case in CASES:
        external, findings, _, _ = await research_merchant(case.name)
        signals = internal_signals(case.name, []) + external
        score, confidence, _, _ = score_signals(signals)
        actual = level_for(score, confidence)
        ok = actual == case.expected
        passed += int(ok)
        print(
            f"{'PASS' if ok else 'FAIL'} | {case.name} | "
            f"expected={case.expected} actual={actual} score={score} confidence={confidence:.2f}"
        )
    accuracy = passed / len(CASES) * 100
    print(f"Overall: {passed}/{len(CASES)} ({accuracy:.1f}%)")
    return 0 if passed == len(CASES) else 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true", help="Run deterministic rules only.")
    parser.parse_args()
    raise SystemExit(asyncio.run(evaluate()))


if __name__ == "__main__":
    main()
