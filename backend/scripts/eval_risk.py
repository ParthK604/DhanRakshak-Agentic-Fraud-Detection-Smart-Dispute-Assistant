import argparse
import asyncio
from collections import defaultdict

from app import db
from app.agents.risk_graph import score_transaction
from app.repositories import transactions
from app.services.features import combine_rules_score, compute_signals, risk_level


async def evaluate(rules_only: bool) -> None:
    db.connect()
    rows, _ = await transactions.list_transactions({}, 1, 500, ("timestamp", 1))
    grouped: dict[str, list[tuple[int, str, list[str]]]] = defaultdict(list)
    for row in rows:
        history = [
            item for item in rows
            if item.user_id == row.user_id
            and item.timestamp < row.timestamp
            and item.txn_id != row.txn_id
        ]
        signals = compute_signals(row, history)
        rules_score = combine_rules_score(signals)
        if rules_only:
            score, level = rules_score, risk_level(rules_score)
            fired = [signal.name for signal in signals if signal.triggered]
        else:
            assessment = await score_transaction(row)
            score, level = assessment.risk_score, assessment.risk_level
            fired = [signal.name for signal in assessment.signals if signal.triggered]
        grouped[row.scenario or "unlabelled"].append((score, level, fired))

    print("Scenario                 Count  Mean   Low    Medium High   Top signals")
    print("-" * 84)
    for scenario, values in sorted(grouped.items()):
        count = len(values)
        mean = sum(value[0] for value in values) / count
        levels = {name: sum(value[1] == name for value in values) * 100 / count for name in ("low", "medium", "high")}
        signal_counts: dict[str, int] = defaultdict(int)
        for _, _, fired in values:
            for signal in fired:
                signal_counts[signal] += 1
        top = ", ".join(name for name, _ in sorted(signal_counts.items(), key=lambda item: item[1], reverse=True)[:3]) or "-"
        print(f"{scenario:<24} {count:>5}  {mean:>5.1f}  {levels['low']:>5.1f}% {levels['medium']:>6.1f}% {levels['high']:>5.1f}%  {top}")
    db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate seeded risk scenarios.")
    parser.add_argument("--rules-only", action="store_true", help="Skip Groq and evaluate deterministic rules.")
    args = parser.parse_args()
    asyncio.run(evaluate(args.rules_only))


if __name__ == "__main__":
    main()
