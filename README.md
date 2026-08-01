# DriftBench

[![CI](https://github.com/simon9679/driftbench/actions/workflows/ci.yml/badge.svg)](https://github.com/simon9679/driftbench/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/spec-1.1.0-blue.svg)](standard/SPEC.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![CITATION](https://img.shields.io/badge/cite-CITATION.cff-orange.svg)](CITATION.cff)

**Deterministic benchmark for belief drift, conflict tracking, and identity transition in cognitive AI systems.**

Most memory benchmarks measure recall. DriftBench measures whether a system can track changing commitments, internal contradictions, identity reconfiguration, and causally meaningful graph updates — without relying on an LLM judge.

## Quick start

```bash
git clone https://github.com/simon9679/driftbench.git
cd driftbench
pip install -e .
driftbench-validate --sub examples/submission_minimal.json --scen examples/scenario_minimal.json --nonce local_test
```

Output:

```json
{
  "spec": "1.1.0",
  "status": "VALIDATED",
  "scores": { "CER": 1.0, "GCS": 1.0, "BDA": 1.0, "ISS": 1.0, "NRS": null }
}
```

That's it. You just validated your first submission.

> _Example validator output on the minimal dummy submission — demonstrates the harness runs
> end-to-end; **NOT** a system performance score. Real system scores require a real adapter
> and vary by run._

## How it works

```
Your cognitive engine
        │
        ▼
  ┌─────────────┐     ┌──────────────┐
  │  Adapter     │────▶│  Submission  │   JSON: raw + conv + hashes
  │  (you write) │     └──────┬──────┘
  └─────────────┘            │
                             ▼
                    ┌─────────────────┐
                    │  Zero-trust     │   nonce check, hash verification,
                    │  validator      │   delta bounds, causality checks
                    └────────┬────────┘
                             │
                     ┌───────┴───────┐
                     │  Deterministic │   CER · GCS · BDA · ISS · NRS
                     │  scores        │
                     └───────────────┘
```

1. **You write an adapter** that converts your engine's internal state into the benchmark format (nodes, edges, transitions with cryptographic trace hashes).
2. **The validator** rejects any submission with forged hashes, impossible deltas, or dummy data.
3. **The scorer** computes five deterministic metrics against ground-truth scenarios.

## Adapt your system in 5 minutes

Subclass `BaseAdapter` and implement one method — `format_state`:

```python
from driftbench_core.adapter import BaseAdapter

class MyAdapter(BaseAdapter):
    def format_state(self, raw_engine_log: dict) -> dict:
        # Convert your engine's internal format into:
        return {
            "nodes": [...],        # BeliefNode — beliefs with confidence & trace
            "edges": [...],        # BeliefEdge — conflicts, blocks, supports
            "transitions": [...],  # BeliefTransition — confidence deltas per turn
        }

adapter = MyAdapter()
submission = adapter.export(my_engine_log)  # handles hashing & validation
```

See [`adapters/template_adapter.py`](adapters/template_adapter.py) for a complete skeleton with TODO markers.

### Key contracts

- Every node/edge/transition must carry a `text_hash` bound to a specific conversation turn (computed via `hash_turn(turn_idx, user_text, assistant_text)`).
- Deltas are bounded to `[-0.4, 0.4]`.
- `core_id` must match a concept in the [frozen v1 ontology](standard/v1/ontology.json) with `mapping_confidence ≥ 0.7`.

## Metrics

The metrics sit on **two layers** — *semantic* (judged against ground truth) and
*structural / temporal* (internal coherence only). **They must not be averaged into one
score**; see [Validity checks](#validity-checks).

| Metric | Full name | Layer | What it measures |
|--------|-----------|-------|-----------------|
| **CER** | Conflict Edge Recovery | semantic | F1 against ground-truth conflict pairs |
| **BDA** | Belief Drift Accuracy | semantic | Do the right beliefs move in the right direction? |
| **ISS** | Identity Shift Score | semantic | Does the target identity overtake the source? |
| **GCS** | Graph Causal Score | structural | Do the submission's *own* conflict edges precede target suppression? (**not** compared against ground truth) |
| **NRS** | Noise Resistance Score | temporal | No belief moves on the noise *turns* (by turn index — not a semantic check) |

All metrics are deterministic. No LLM judge. Same input → same scores, always.

> **NRS empty-state defect — fixed in 1.0.1.** An empty belief graph (e.g. from a parse
> failure) used to score **NRS = 1.00**, the maximum; since 1.0.1 it returns *undefined*, so
> a system that emits nothing is no longer credited with perfect noise resistance. Found only
> by repeated runs; see [`CHANGELOG.md`](CHANGELOG.md).

## v1 Ontology (8 concepts)

| Category | Concepts |
|----------|----------|
| Identity | `ID_FOUNDER`, `ID_EMPLOYEE` |
| Values | `V_FIN_SECURITY`, `V_GROWTH` |
| Fears | `F_FAILURE`, `F_STAGNATION` |
| Goals | `G_MVP_LAUNCH`, `G_PROMOTION` |

The ontology is frozen for v1. See [`standard/v1/ontology.json`](standard/v1/ontology.json).

## Official v1 scenarios

7 scenarios covering burnout-to-founder transitions, promotion conflicts, financial identity shifts, failure recovery, delayed contradictions, and noise resistance:

| ID | Scenario |
|----|----------|
| 01 | Burnout → Founder |
| 02 | Promotion vs Founder |
| 03 | Financial Identity |
| 04 | Failure Recovery → Launch |
| 05 | Promotion after Launch |
| 10 | Delayed Contradiction |
| 11 | Noise Resistance |

All scenarios in [`standard/v1/scenarios/`](standard/v1/scenarios/). The same 7 scenarios and the
frozen ontology are also published as a dataset:
[huggingface.co/datasets/simon9679/driftbench-v1](https://huggingface.co/datasets/simon9679/driftbench-v1).

## Baselines

Reproducible single-pass LLM baselines over all 7 scenarios live in
[`baselines/BASELINES.md`](baselines/BASELINES.md). The profile
**`BDA > ISS > CER > GCS > NRS`** holds across three independent non-reasoning
models (GPT-4.1, Claude Haiku 4.5, gpt-oss-120b) — with one close pair (`CER ≈ GCS`
for Haiku, 0.259 vs 0.250) that run-to-run variance could reorder. The takeaway is
stable: today's LLMs track the *direction* of belief drift well, but recover
conflict structure weakly and resist noise not at all — `NRS = 0.0` on all three.

Repeated runs of the same model on the same scenarios are now published **with their
spread** in [`baselines/BASELINES.md`](baselines/BASELINES.md): some per-scenario
cells barely move between runs, others swing widely, so a single pass is a sample,
not a measurement — systems must not be ranked on one run.

Reproduce the table (injects the frozen ontology into each official scenario, then
scores it; needs an API key in the provider's `.env`, e.g. `_anthropic.env`):

```bash
python run_baselines.py --provider anthropic --model claude-haiku-4-5
```

For a quick harness demo — not a reproduction of the table above — the convenience
runner scores a built-in scenario:

```bash
python adapters/simple/driftbench_run.py --provider openai --model gpt-4o
```

Note its built-in scenarios use **free-form concept ids**, not the frozen v1
ontology, so they exercise the scorer but do not match the official pack.

Both paths use the canonical `driftbench_core` metrics, but neither is the
tamper-checked zero-trust validator (no nonce, no hash chain) — treat these as
orientation, not certificates.

## Validity checks

The benchmark checks itself, and publishes what it finds — following the falsification
protocol from [`simon9679/tbg-postmortem`](https://github.com/simon9679/tbg-postmortem)
(`FALSIFICATION_PROTOCOL.md`, rules 3/5/8: a degenerate-control canary before the
expensive comparison, hypotheses written before the run, effects that must survive a
repeat). Two offline probes live in [`dev-scripts/probes/`](dev-scripts/probes/); their
outputs and a guide are in [`docs/probes/`](docs/probes/).

- **Label-invariance** ([`label_invariance_probe.py`](dev-scripts/probes/label_invariance_probe.py)):
  scrambling the concept labels on real states (9500 permutations) leaves **GCS and NRS
  100% unchanged** — they measure structure/timing, not semantics — while CER/BDA/ISS
  degrade. On a fraction of permutations the semantic metrics **improve** (ISS ≈ 14%,
  BDA ≈ 8%, CER ≈ 2%; a Monte-Carlo estimate, not a constant), so a score is not by
  itself proof the *right* concepts were tracked, and CER/BDA/ISS must not be averaged
  with GCS/NRS.
- **Oracle** ([`oracle_probe.py`](dev-scripts/probes/oracle_probe.py)): an ideal
  submission built from ground truth reaches **1.000 on CER/GCS/BDA/ISS on all 7
  scenarios**, so the metrics have a real, reachable maximum. Reaching GCS = 1.0 requires
  knowing the formula (non-overlapping windows, escalating suppression energy), which is
  itself GCS's gaming vector — documented in [`standard/SPEC.md`](standard/SPEC.md).

## Roadmap

v1 is frozen for reproducibility; all future work is additive. Next up:

- **20+ scenarios across new domains** — relationships, health, money & risk, grief & loss, addiction & recovery (today's scenarios are career/identity only).
- **An ambivalence metric (`AMB`)** — scoring sustained co-activation of conflicting beliefs (holding two contradictory positions at once), alongside `OCS` and `TPS`.
- **Open metric specification** — full methodology published for independent reproduction.

See [`ROADMAP.md`](ROADMAP.md) for details. A **working preview** of the
ambivalence metric already runs — see
[`research/v1_1_draft/`](research/v1_1_draft/).

## Project layout

```
driftbench_core/     Scoring engine, validator, adapter base class
standard/v1/         Frozen ontology, scenarios, specification
adapters/            Reference integrations + template
examples/            Minimal scenario + submission
tests/               Benchmark core test suite
research/            Legacy and experimental material
```

## Specification

Full contract details in [`standard/SPEC.md`](standard/SPEC.md).

## Related work / Evaluation reliability

This deterministic harness is one half of a broader focus on evaluation reliability. The
other half studies LLM-as-judge reliability on ES-MemEval (WWW '26): a three-layer noise
decomposition (judge / answerer / ingest), per-arm judge bias validated by blind human
relabel (K=20), and the finding that subset-level capability claims are dominated by ingest
stochasticity. DriftBench takes the deterministic route (no LLM judge); the ES-MemEval study
calibrates the LLM-judge route. See [`eval_reliability/`](eval_reliability/) — now covers five
ingest-variance data points and two pre-registered negative product gates.

That reliability study is published as [`simon9679/tbg-postmortem`](https://github.com/simon9679/tbg-postmortem):
it grew out of a *negative* result on a belief-memory engine (TBG), which failed to beat simple
baselines. DriftBench is the tool built to satisfy the falsification protocol worked out there —
a deterministic, no-LLM-judge benchmark. See the postmortem for the protocol; it is not retold here.

**Belief-revision benchmarks.** Recent work (e.g.
[BeliefShift (Myakala et al., 2026)](https://arxiv.org/abs/2606.22030) — temporal belief
consistency and cross-session opinion drift, our nearest neighbour; and the broader
belief-revision / contradiction line such as STALE and TOKI) targets the same real failure mode we care about —
agents treating stale or contradicted memories as authoritative. Our focus is complementary
along two axes we make measurable rather than assert: (1) **scoring substrate** — DriftBench
scores deterministically (no LLM judge in the loop), which sidesteps the judge-reliability
problem we quantify separately; (2) **evidence granularity** — we carry *graded* confidence
per belief rather than binary held/dropped, so trajectories and partial contradictions are
representable. We see these as different design points, not competitors: the belief-revision
benchmarks define the task; our contribution is a reproducibility / measurement layer on top.

## License

Apache 2.0 — see [LICENSE](LICENSE).

---



