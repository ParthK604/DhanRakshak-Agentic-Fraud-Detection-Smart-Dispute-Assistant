# Phase 3 Risk Evaluation

Rules-only evaluation command:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m scripts.eval_risk --rules-only
```

| Scenario | Count | Mean | Low | Medium | High | Top signals |
|---|---:|---:|---:|---:|---:|---|
| baseline | 27 | 8.0 | 100.0% | 0.0% | 0.0% | - |
| duplicate_charge | 4 | 9.5 | 100.0% | 0.0% | 0.0% | possible_duplicate |
| geo_anomaly | 2 | 46.0 | 50.0% | 0.0% | 50.0% | unusual_amount, new_payee_large, geo_anomaly |
| new_payee_large | 1 | 70.0 | 0.0% | 0.0% | 100.0% | unusual_amount, new_payee_large |
| suspicious_merchant | 1 | 70.0 | 0.0% | 0.0% | 100.0% | unusual_amount, new_payee_large |
| unusual_amount | 1 | 38.0 | 0.0% | 100.0% | 0.0% | unusual_amount |
| velocity_burst | 9 | 44.4% low / 55.6% medium | 44.4% | 55.6% | 0.0% | velocity |

`possible_duplicate` is intentionally informational and low weight. The first row of
a geographic or velocity scenario is a legitimate precondition row; later rows
trigger the anomaly or velocity signal. Scenario is used only for evaluation grouping,
not by signal logic or the Groq prompt.

## Full pipeline smoke evaluation

The full Groq-backed command was also run:

```powershell
python -m scripts.eval_risk
```

| Scenario | Count | Mean | Low | Medium | High |
|---|---:|---:|---:|---:|---:|
| baseline | 27 | 11.7 | 96.3% | 3.7% | 0.0% |
| duplicate_charge | 4 | 9.0 | 100.0% | 0.0% | 0.0% |
| geo_anomaly | 2 | 34.0 | 50.0% | 50.0% | 0.0% |
| new_payee_large | 1 | 38.0 | 0.0% | 100.0% | 0.0% |
| suspicious_merchant | 1 | 55.0 | 0.0% | 100.0% | 0.0% |
| unusual_amount | 1 | 38.0 | 0.0% | 100.0% | 0.0% |
| velocity_burst | 9 | 10.8 | 100.0% | 0.0% | 0.0% |

The rules-only table is the deterministic acceptance baseline. The full model run
confirmed real Groq responses and score clamping, but model reasoning sometimes
underweighted a deterministic signal; this is a known tuning item before the demo.
