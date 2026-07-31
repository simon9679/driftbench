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

> 🕰 **Historical — not reproducible.** These numbers were measured via GitHub Models, which GitHub shut down on **2026-07-30** (playground, model catalog, inference API and BYOK endpoints — for everyone, including existing users). The table is kept as a record of the measurement; the endpoint no longer exists, so it cannot be re-run.

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

These results were produced through a **convenience runner**
(`adapters/simple/driftbench_run.py` — its `build_prompt` / `parse_belief_state`),
and the metric math is imported unchanged from the canonical `driftbench_core`.
However, this is **NOT** the tamper-checked zero-trust validator: no nonce, no
raw/conv hash chain, no integrity bans. Treat these as **baselines for orientation,
not official certificates**.

Low scores here are **expected headroom** for an early benchmark — they mark the
gap a stronger system is meant to close, not a bug in the harness.

Reasoning models spend their token budget on hidden reasoning and truncate /
malform the JSON — hence the coverage caveats. Non-reasoning instruct models emit
valid JSON reliably and are the fair comparison points.

## Repeated-run variance (same model, same scenarios)

3 runs of one model on the same seven scenarios, `temperature=0`, **nothing changed between runs**. The spread below is what the same configuration produced on repeat. The range sits next to each number on purpose — a single run is not a measurement.

### `gpt-oss-120b` — 3 runs, same model, nothing changed between runs

**CER**

| Scenario | run1 | run2 | run3 | mean (min–max, Δrange) |
|---|---|---|---|---|
| 01_burnout_to_founder | 0.2500 | 0.2500 | 0.3333 | 0.2778 (0.25–0.33, Δ0.08) |
| 02_promotion_vs_founder | 0.2500 | 0.2500 | 0.2500 | 0.2500 (0.25–0.25, Δ0.00) |
| 03_financial_identity | 0.3333 | 0.3333 | 0.3333 | 0.3333 (0.33–0.33, Δ0.00) |
| 04_failure_recovery_to_launch | 0.2500 | 0.5000 | 0.2500 | 0.3333 (0.25–0.50, Δ0.25) |
| 05_promotion_after_launch | 0.2857 | 0.2857 | 0.2857 | 0.2857 (0.29–0.29, Δ0.00) |
| 10_delayed_contradiction | 0.3333 | 0.4000 | 0.4000 | 0.3778 (0.33–0.40, Δ0.07) |
| 11_noise_resistance | 0.0000 | fail | fail | 0.0000 (1/3 runs — range needs ≥2 good runs) |
| **benchmark mean** | 0.2432 | 0.3365 | 0.3087 | 0.2961 (0.24–0.34, Δ0.09) |

**GCS**

| Scenario | run1 | run2 | run3 | mean (min–max, Δrange) |
|---|---|---|---|---|
| 01_burnout_to_founder | 0.0000 | 0.0000 | — | 0.0000 (0.00–0.00, Δ0.00) (2/3 runs) |
| 02_promotion_vs_founder | 1.0000 | 0.5000 | 0.5000 | 0.6667 (0.50–1.00, Δ0.50) |
| 03_financial_identity | 0.0000 | — | 0.0000 | 0.0000 (0.00–0.00, Δ0.00) (2/3 runs) |
| 04_failure_recovery_to_launch | 0.5000 | 0.2500 | 0.5000 | 0.4167 (0.25–0.50, Δ0.25) |
| 05_promotion_after_launch | 0.3333 | 0.3333 | 0.3333 | 0.3333 (0.33–0.33, Δ0.00) |
| 10_delayed_contradiction | 0.5000 | 0.0000 | 0.0000 | 0.1667 (0.00–0.50, Δ0.50) |
| 11_noise_resistance | — | fail | fail | — (2/3 failed, no data) |
| **benchmark mean** | 0.3889 | 0.2167 | 0.2667 | 0.2907 (0.22–0.39, Δ0.17) |

**BDA**

| Scenario | run1 | run2 | run3 | mean (min–max, Δrange) |
|---|---|---|---|---|
| 01_burnout_to_founder | 0.8333 | 0.8333 | 1.0000 | 0.8889 (0.83–1.00, Δ0.17) |
| 02_promotion_vs_founder | 0.8571 | 0.8571 | 0.8571 | 0.8571 (0.86–0.86, Δ0.00) |
| 03_financial_identity | 0.2500 | 0.2500 | 0.2500 | 0.2500 (0.25–0.25, Δ0.00) |
| 04_failure_recovery_to_launch | 0.8333 | 0.8333 | 0.8333 | 0.8333 (0.83–0.83, Δ0.00) |
| 05_promotion_after_launch | 0.5714 | 0.5714 | 0.5714 | 0.5714 (0.57–0.57, Δ0.00) |
| 10_delayed_contradiction | 0.5000 | 0.2500 | 0.2500 | 0.3333 (0.25–0.50, Δ0.25) |
| 11_noise_resistance | 0.3333 | fail | fail | 0.3333 (1/3 runs — range needs ≥2 good runs) |
| **benchmark mean** | 0.5969 | 0.5992 | 0.6270 | 0.6077 (0.60–0.63, Δ0.03) |

**ISS**

| Scenario | run1 | run2 | run3 | mean (min–max, Δrange) |
|---|---|---|---|---|
| 01_burnout_to_founder | 1.0000 | 1.0000 | 0.8000 | 0.9333 (0.80–1.00, Δ0.20) |
| 02_promotion_vs_founder | 0.8000 | 0.7200 | 0.7200 | 0.7467 (0.72–0.80, Δ0.08) |
| 03_financial_identity | 0.0000 | 0.0000 | 0.0000 | 0.0000 (0.00–0.00, Δ0.00) |
| 04_failure_recovery_to_launch | 0.5200 | 0.6000 | 0.5200 | 0.5467 (0.52–0.60, Δ0.08) |
| 05_promotion_after_launch | 0.8000 | 0.8000 | 0.8000 | 0.8000 (0.80–0.80, Δ0.00) |
| 10_delayed_contradiction | 0.0000 | 0.0000 | 0.0000 | 0.0000 (0.00–0.00, Δ0.00) |
| 11_noise_resistance | 0.0000 | fail | fail | 0.0000 (1/3 runs — range needs ≥2 good runs) |
| **benchmark mean** | 0.4457 | 0.5200 | 0.4733 | 0.4797 (0.45–0.52, Δ0.07) |

**NRS**

| Scenario | run1 | run2 | run3 | mean (min–max, Δrange) |
|---|---|---|---|---|
| 01_burnout_to_founder | — | — | — | — |
| 02_promotion_vs_founder | — | — | — | — |
| 03_financial_identity | — | — | — | — |
| 04_failure_recovery_to_launch | — | — | — | — |
| 05_promotion_after_launch | — | — | — | — |
| 10_delayed_contradiction | — | — | — | — |
| 11_noise_resistance | 0.0000 | fail | fail | 0.0000 (1/3 runs — range needs ≥2 good runs) |
| **benchmark mean** | 0.0000 | — | — | 0.0000 (1/3 runs — range needs ≥2 good runs) |

_Legend: `—` = metric undefined for that scenario · `fail` = the run's JSON did not parse (empty state); `fail` runs are excluded from min / max / range / mean._


### What the spread shows

On the runs that answered, metrics diverge noticeably between identical repeats: CER up to **Δ0.25** · GCS up to **Δ0.50** · BDA up to **Δ0.25** · ISS up to **Δ0.20**.

Separately, **2 of 21 runs did not parse** (empty state) and are marked `fail`; they are excluded from the variance figures above. Both parse failures fell on the same scenario (`11_noise_resistance`), but three runs are too few to conclude why, and no cause is claimed here.

The takeaway is unchanged and is not softened: a single run of a single model on a single scenario is not a measurement — systems must not be ranked on one run.

## Metric defect (v1.1 candidate): empty state scores NRS = 1.00

On repeated runs, 2 of 21 scored responses failed to parse and produced an empty belief graph (`{"nodes": [], "edges": [], "transitions": []}`). The benchmark assigned that empty state **NRS = 1.00 — the maximum** noise-resistance score. On the run that answered, the same scenario scored NRS = 0.00.

This is a defect in the metric's semantics, not a scoring bug: a system that emits nothing is credited with perfect resistance to noise. The logic is understandable (no beliefs, nothing to shift) but the result is absurd and easy to exploit — a silent adapter earns top marks.

**The v1 specification is frozen, so v1 behaviour does not change.** The defect is recorded and carried to v1.1 as a fix candidate. Proposed direction (named, not implemented here): an empty or invalid state should yield an *undefined* result, not a maximum score.

**This defect was found by repeated runs and could not have been found any other way.** A single run gave NRS = 0.00 on scenario 11 and raised no questions — the same input scored the opposite once its parse failed on repeat. That is the direct point of running more than once.
