# Phase 4 Dispute Evaluation

The deterministic fallback evaluation was run with:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m scripts.eval_disputes --no-llm
```

Result: **12/12 cases passed (100.0%)** after tuning phrase variants for duplicate
payments and cancellation wording.

The cases cover Netflix duplicate phrasing, Spotify and Amazon variants, wrong
amount, cancelled subscription, unauthorized charge, not received, no-issue,
off-topic, and instruction-override input.

The live smoke test also completed:

- First turn: duplicate Netflix evidence, one-charge refund estimate, grounded letter,
  and explicit confirmation requested.
- Confirm turn: PayPal create was attempted with an idempotency header.
- PayPal sandbox returned HTTP 400 for the create request, so the record was retained
  as `submission_mode="prepared"` with a plain explanation that it was not filed.

This matches the Phase 2 probe: OAuth and dispute listing worked, but create capability
was not confirmed. The official reference for the create route is
<https://developer.paypal.com/api/customer-disputes/v1/>.
