# Baselines

Reproducible single-pass LLM baselines over the 7 official v1 scenarios live in
[`BASELINES.md`](BASELINES.md), with per-scenario JSON under [`llm/`](llm/).

The profile `BDA > ISS > CER > GCS > NRS` holds across three independent
non-reasoning models — with one close pair (`CER ≈ GCS` for Haiku, 0.259 vs 0.250)
that run-to-run variance could reorder. LLMs track the *direction* of belief drift
well, but recover conflict structure weakly and resist noise not at all (`NRS = 0.0`).

These come from the convenience runner (`adapters/simple/driftbench_run.py`): the
metric math is the canonical `driftbench_core`, but this is **not** the zero-trust
validator. See [`BASELINES.md`](BASELINES.md) for full provenance and the honesty note.
