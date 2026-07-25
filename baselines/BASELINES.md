# DriftBench LLM Baselines

**Spec:** `1.0.0`  ·  Pure LLM baselines over the 7 official v1 scenarios — the
LLM builds the belief graph, scoring uses the canonical `driftbench_core` metrics.
Dash (—) = metric not applicable to that scenario (null).

### `claude-haiku-4-5`

**Provider:** anthropic  ·  **Model:** `claude-haiku-4-5`  ·  **Temp:** 0  ·  **max_tokens:** 4000  ·  **reasoning_effort:** n/a  ·  **Run:** 2026-07-25 15:35 UTC

| Scenario | CER | GCS | BDA | ISS | NRS |
|----------|-----|-----|-----|-----|-----|
| 01_burnout_to_founder | 0.0000 | 0.6667 | 1.0000 | 1.0000 | — |
| 02_promotion_vs_founder | 0.2857 | 0.0000 | 0.8571 | 1.0000 | — |
| 03_financial_identity | 0.6667 | 0.0000 | 0.7500 | 0.0000 | — |
| 04_failure_recovery_to_launch | 0.5714 | — | 0.6667 | 0.4600 | — |
| 05_promotion_after_launch | 0.0000 | 0.5000 | 1.0000 | 0.9200 | — |
| 10_delayed_contradiction | 0.2857 | 0.0000 | 0.7500 | 0.0000 | — |
| 11_noise_resistance | 0.0000 | 0.3333 | 0.6667 | 1.0000 | 0.0000 |
| **mean (valid only, n=7)** | 0.2585 | 0.2500 | 0.8129 | 0.6257 | 0.0000 |

### `gpt-oss-120b`

**Provider:** cerebras  ·  **Model:** `gpt-oss-120b`  ·  **Temp:** 0  ·  **max_tokens:** 20000  ·  **reasoning_effort:** low  ·  **Run:** 2026-07-25 15:09 UTC

| Scenario | CER | GCS | BDA | ISS | NRS |
|----------|-----|-----|-----|-----|-----|
| 01_burnout_to_founder | 0.2857 | 0.0000 | 0.6667 | 0.9000 | — |
| 02_promotion_vs_founder | 0.2500 | 0.6667 | 0.8571 | 0.5200 | — |
| 03_financial_identity | 0.4000 | 0.0000 | 0.7500 | 0.0000 | — |
| 04_failure_recovery_to_launch | 0.3333 | 0.5000 | 0.8333 | 0.4000 | — |
| 05_promotion_after_launch | 0.5714 | 0.0000 | 0.7143 | 0.7200 | — |
| 10_delayed_contradiction | 0.0000 | 0.0000 | 0.2500 | 0.0000 | — |
| 11_noise_resistance | 0.0000 | — | 0.6667 | 1.0000 | 0.0000 |
| **mean (valid only, n=7)** | 0.2629 | 0.1944 | 0.6769 | 0.5057 | 0.0000 |

### `openai/gpt-4.1`

**Provider:** github  ·  **Model:** `openai/gpt-4.1`  ·  **Temp:** 0  ·  **max_tokens:** 4000  ·  **reasoning_effort:** n/a  ·  **Run:** 2026-07-25 15:46 UTC

| Scenario | CER | GCS | BDA | ISS | NRS |
|----------|-----|-----|-----|-----|-----|
| 01_burnout_to_founder | 0.2222 | 0.2500 | 1.0000 | 1.0000 | — |
| 02_promotion_vs_founder | 0.4444 | 0.2000 | 1.0000 | 1.0000 | — |
| 03_financial_identity | 0.5714 | 0.0000 | 0.5000 | 0.0000 | — |
| 04_failure_recovery_to_launch | 0.4444 | 0.0000 | 1.0000 | 0.6000 | — |
| 05_promotion_after_launch | 0.0000 | 0.0000 | 1.0000 | 1.0000 | — |
| 10_delayed_contradiction | 0.3333 | 0.5000 | 0.0000 | 0.0000 | — |
| 11_noise_resistance | 0.3333 | 0.0000 | 0.6667 | 1.0000 | 0.0000 |
| **mean (valid only, n=7)** | 0.3356 | 0.1357 | 0.7381 | 0.6571 | 0.0000 |

### `zai-glm-4.7`

**Provider:** cerebras  ·  **Model:** `zai-glm-4.7`  ·  **Temp:** 0  ·  **max_tokens:** 20000  ·  **reasoning_effort:** low  ·  **Run:** 2026-07-25 15:12 UTC

> ⚠ **Coverage: 1/7 scenarios produced a valid graph.** Rows marked ⚠ failed JSON parsing or truncated — their `0.0`/`—` (and any `NRS=1.0` from an empty graph) reflect **no usable output, not belief tracking**. They are excluded from the mean.

| Scenario | CER | GCS | BDA | ISS | NRS |
|----------|-----|-----|-----|-----|-----|
| 01_burnout_to_founder ⚠ | 0.0000 | — | 0.0000 | 0.0000 | — |
| 02_promotion_vs_founder ⚠ | 0.0000 | — | 0.0000 | 0.0000 | — |
| 03_financial_identity | 0.2857 | — | 0.7500 | 0.0000 | — |
| 04_failure_recovery_to_launch ⚠ | 0.0000 | — | 0.0000 | 0.0000 | — |
| 05_promotion_after_launch ⚠ | 0.0000 | — | 0.0000 | 0.0000 | — |
| 10_delayed_contradiction ⚠ | 0.0000 | — | 0.0000 | 0.0000 | — |
| 11_noise_resistance ⚠ | 0.0000 | — | 0.0000 | 0.0000 | 1.0000 |
| **mean (valid only, n=1)** | 0.2857 | — | 0.7500 | 0.0000 | — |

## Provenance & honesty note

These results were produced by the orchestrator `run_baselines.py` (repo
root), which injects the frozen ontology into each of the 7 official scenarios and
scores them on the canonical `driftbench_core` metrics via the convenience runner's
helpers (`adapters/simple/driftbench_run.py` — its `build_prompt` /
`parse_belief_state`). The metric math is imported unchanged from `driftbench_core`.
However, this is **NOT** the tamper-checked zero-trust validator: no nonce, no
raw/conv hash chain, no integrity bans. Treat these as **baselines for orientation,
not official certificates**.

**Single-run caveat.** Each cell is one run at `temperature=0`. On hosted models
(request batching, MoE routing, floating-point non-associativity) the output varies
run-to-run even at `temperature=0`, so these numbers are **samples from a
distribution, not fixed points**. For publication, run each model 3–5× and report
mean ± spread rather than a single value.

Low scores here are **expected headroom** for an early benchmark — they mark the
gap a stronger system is meant to close, not a bug in the harness.

Reasoning models (e.g. `zai-glm-4.7`) spend their token budget on hidden reasoning
and truncate / malform the JSON — hence the coverage caveats. Non-reasoning
instruct models emit valid JSON reliably and are the fair comparison points.
