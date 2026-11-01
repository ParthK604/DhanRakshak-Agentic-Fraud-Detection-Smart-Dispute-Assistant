"""Generate a Postman v2.1 collection from the FastAPI OpenAPI schema."""

import json
from pathlib import Path
from typing import Any

from app.main import app

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "postman" / "DhanRakshak.postman_collection.json"

EXAMPLES: dict[str, Any] = {
    "/api/risk/score-transaction": {
        "txn_id": "postman-suspicious-1", "user_id": "{{demo_user_id}}",
        "amount": 1250, "currency": "USD", "merchant_name": "Northstar Electronics",
        "country": "US", "payee_email": "orders@example.com", "direction": "outgoing",
        "timestamp": "2026-01-15T12:00:00Z", "status": "PENDING",
    },
    "/api/disputes/chat": {
        "user_id": "{{demo_user_id}}", "session_id": None,
        "message": "I was charged twice for Netflix", "action": None, "payload": None,
    },
    "/api/merchants/trust": {"merchant_name": "Northstar Electronics", "refresh": False},
    "/api/merchants/precheck": {
        "user_id": "{{demo_user_id}}", "merchant_name": "Flash Prize Outlet",
        "merchant_url": None, "amount": 299, "currency": "USD",
    },
    "/api/risk/score": {"txn_id": "{{txn_id}}", "force": False},
    "/api/risk/score-batch": {"user_id": "{{demo_user_id}}", "limit": 10, "only_unscored": True},
    "/api/merchants/trust-batch": ["Northstar Electronics", "Flash Prize Outlet"],
}


def _test_script(path: str, method: str) -> list[str]:
    tests = [
        "pm.test('status is successful', function () { pm.expect(pm.response.code).to.be.within(200, 299); });",
    ]
    if path in {"/api/transactions", "/api/risk/scores", "/api/merchants"}:
        tests.append("pm.test('paged response has items and total', function () { const body = pm.response.json(); pm.expect(body).to.have.property('items'); pm.expect(body).to.have.property('total'); });")
    if path == "/api/transactions":
        tests.append("const body = pm.response.json(); if (body.items.length) pm.collectionVariables.set('txn_id', body.items[0].txn_id);")
    if path.startswith("/api/risk/score"):
        tests.append("pm.test('score is between 0 and 100', function () { pm.expect(pm.response.json().risk_score).to.be.within(0, 100); });")
    if path == "/api/disputes/chat":
        tests.append("pm.test('chat has a reply', function () { pm.expect(pm.response.json()).to.have.property('reply'); });")
        tests.append("pm.collectionVariables.set('session_id', pm.response.json().session_id);")
    if path == "/api/disputes":
        tests.append("pm.test('disputes expose submission mode', function () { const body = pm.response.json(); if (body.items.length) pm.expect(body.items[0]).to.have.property('submission_mode'); });")
    if path == "/api/merchants/trust":
        tests.append("pm.test('trust response has a score', function () { pm.expect(pm.response.json()).to.have.property('trust_score'); });")
    if path == "/api/merchants/trust-batch":
        tests.append("pm.test('trust batch has scores', function () { const body = pm.response.json(); if (body.length) pm.expect(body[0]).to.have.property('trust_score'); });")
    if path == "/api/merchants/precheck":
        tests.append("pm.test('precheck has a verdict', function () { pm.expect(pm.response.json()).to.have.property('combined_verdict'); });")
    return tests


def _request(path: str, method: str, operation: dict[str, Any]) -> dict[str, Any]:
    url = "{{base_url}}" + path
    item: dict[str, Any] = {
        "name": operation.get("summary") or f"{method} {path}",
        "request": {"method": method, "header": [], "url": url},
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": _test_script(path, method)}}],
    }
    if method == "POST":
        item["request"]["header"] = [{"key": "Content-Type", "value": "application/json"}]
        item["request"]["body"] = {"mode": "raw", "raw": json.dumps(EXAMPLES.get(path, {}), indent=2)}
    return item


def main() -> None:
    schema = app.openapi()
    groups: dict[str, list[dict[str, Any]]] = {}
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            if method.upper() not in {"GET", "POST"}:
                continue
            tag = (operation.get("tags") or ["misc"])[0]
            groups.setdefault(tag, []).append(_request(path, method.upper(), operation))
    story = [
        ("/healthz", "GET"), ("/api/transactions", "GET"), ("/api/risk/score", "POST"),
        ("/api/risk/score-transaction", "POST"), ("/api/disputes/chat", "POST"),
        ("/api/merchants/trust", "POST"), ("/api/merchants/precheck", "POST"),
    ]
    ordered: list[dict[str, Any]] = []
    for path, method in story:
        for items in groups.values():
            ordered.extend(item for item in items if item["request"]["method"] == method and item["request"]["url"] == "{{base_url}}" + path)
    chat = next((item for item in ordered if item["request"]["url"].endswith("/api/disputes/chat")), None)
    if chat is not None:
        confirmation = json.loads(json.dumps(chat))
        confirmation["name"] = "Confirm dispute submission"
        body = json.loads(confirmation["request"]["body"]["raw"])
        body.update({"session_id": "{{session_id}}", "message": None, "action": "confirm"})
        confirmation["request"]["body"]["raw"] = json.dumps(body, indent=2)
        ordered.insert(ordered.index(chat) + 1, confirmation)
    remaining = [item for items in groups.values() for item in items if item not in ordered]
    folders = [{"name": "Story", "item": ordered}]
    folders.extend({"name": tag, "item": items} for tag, items in sorted(groups.items()) if items)
    collection = {
        "info": {"name": "DhanRakshak", "_postman_id": "dhanrakshak-phase-7b", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
        "variable": [{"key": "base_url", "value": "http://localhost:8000"}, {"key": "demo_user_id", "value": "demo-user-1"}, {"key": "txn_id", "value": "seed-netflix-duplicate-1"}],
        "item": folders + ([{"name": "Other endpoints", "item": remaining}] if remaining else []),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
