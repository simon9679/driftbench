# DriftBench

[![CI](https://github.com/simon9679/driftbench/actions/workflows/ci.yml/badge.svg)](https://github.com/simon9679/driftbench/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/spec-1.0.0-blue.svg)](standard/SPEC.md)
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
  "spec": "1.0.0",
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

| Metric | Full name | What it measures |
|--------|-----------|-----------------|
| **CER** | Conflict Edge Recovery | F1 against ground-truth conflict pairs |
| **GCS** | Graph Causal Score | Do conflict edges cause downstream energy deviation? |
| **BDA** | Belief Drift Accuracy | Do the right beliefs move in the right direction? |
| **ISS** | Identity Shift Score | Does the target identity overtake the source? |
| **NRS** | Noise Resistance Score | Does the system ignore irrelevant turns? |

All metrics are deterministic. No LLM judge. Same input → same scores, always.

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

All scenarios in [`standard/v1/scenarios/`](standard/v1/scenarios/).

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
calibrates the LLM-judge route. See [`eval_reliability/`](eval_reliability/).

**Belief-revision benchmarks.** Recent work (e.g. BeliefShift, and the broader belief-revision /
contradiction line such as STALE and TOKI) targets the same real failure mode we care about —
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



