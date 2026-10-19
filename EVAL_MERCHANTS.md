# Merchant Trust Evaluation

The offline evaluator runs the fixture research provider and deterministic scoring
without MongoDB, network access, or an LLM:

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
python -m scripts.eval_merchants --no-llm
```

The expected baseline is that established merchants are trusted, suspicious and
lookalike merchants are high risk, and merchants with no evidence are unknown.
The evaluator prints each case's expected and actual level, score, confidence,
and the overall accuracy. The API evaluator additionally exercises Groq,
persistence, caching, and precheck.
