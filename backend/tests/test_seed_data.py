from datetime import UTC

from scripts.seed_data import (
    generate_duplicate_charge,
    generate_geo_anomaly,
    generate_seed_transactions,
    generate_velocity_burst,
)


def test_duplicate_pair_matches() -> None:
    rows = generate_duplicate_charge()
    assert rows[0].merchant_name == rows[1].merchant_name == "Netflix"
    assert rows[0].amount == rows[1].amount
    assert (rows[1].timestamp - rows[0].timestamp).total_seconds() == 180


def test_velocity_burst_count_and_window() -> None:
    rows = generate_velocity_burst()
    assert len(rows) == 9
    assert (max(row.timestamp for row in rows) - min(row.timestamp for row in rows)).total_seconds() < 300


def test_geo_anomaly_is_distant_and_close_in_time() -> None:
    rows = generate_geo_anomaly()
    assert {row.country for row in rows} == {"US", "SG"}
    assert (rows[1].timestamp - rows[0].timestamp).total_seconds() < 4 * 3600


def test_seed_is_deterministic() -> None:
    first = [row.model_dump(mode="json") for row in generate_seed_transactions()]
    second = [row.model_dump(mode="json") for row in generate_seed_transactions()]
    assert first == second
    assert all(row.timestamp.tzinfo == UTC for row in generate_seed_transactions())
