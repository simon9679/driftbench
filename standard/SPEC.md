# DriftBench Standard Specification v1.0.0

## What v1 is

DriftBench v1 is a **structural validator with proxy metrics**. It guarantees that submissions are internally consistent, tamper-free, and graph-coherent. It does **not** verify that labels, mappings, or edges are semantically grounded in the source text. That is a v2 concern (semantic grounding layer).

## Submission contract

Every evaluated system must submit a JSON document with:
- `raw`: original engine log or export
- `raw_h`: sha256 over `raw`
- `conv`: converted benchmark representation
- `conv_h`: sha256 over `conv`

## Converted representation

### Node
- `id`: system-local node identifier
- `label`: human-readable label
- `core_id`: canonical ontology id or `null`
- `mapping_confidence`: confidence for `core_id` mapping (**UNVERIFIED FIELD** — self-reported by adapter, not validated against source text)
- `confidence`: final belief confidence in `[0,1]`
- `evidence_turn`: source turn index
- `text_hash`: turn hash from user and assistant text

### Edge
- `source_id`, `target_id` (must reference existing nodes)
- `source_core_id`, `target_core_id` (must match declared concepts and node→core_id mapping)
- `relation`: currently `blocks` or `contradicts` count toward conflict metrics
- `created_at_turn`
- `evidence_turn`
- `text_hash`

### Transition
- `node_id`
- `core_id`
- `turn`
- `delta`: bounded to `[-0.4, 0.4]`
- `trigger_text_hash`

## v1 metrics

The five metrics sit on **two different measurement layers**, which must **not** be
averaged into one number (see below).

**Layer 1 — semantic** (are the beliefs the *right* ones, judged against ground truth):
- `CER`: conflict edge recovery against ground-truth conflict pairs
- `BDA`: whether the right canonical beliefs move in the right direction
- `ISS`: whether the target identity overtakes the source identity

**Layer 2 — structural / temporal** (is the submission internally coherent — **not**
judged against ground truth):
- `GCS`: do the submission's *own* conflict edges precede downstream suppression of their target? (causal = net_impact < −0.05 within k=3 turns after edge creation). This is **internal causal coherence; it does not compare against ground truth**, and is therefore invariant to a permutation of the concept labels.
- `NRS`: noise resistance — no significant confidence deltas on the noise **turns**. Counted by turn index, **not a semantic check**, and likewise label-invariant.

> **Do not average across layers.** A label-invariance probe over 9500 permutations of
> the eight `core_id`s found **GCS and NRS 100% unchanged** while CER/BDA/ISS degraded —
> direct evidence the two groups measure different things. A single "overall score"
> mixing them is not meaningful. Probe: [`../docs/probes/`](../docs/probes/).

### Known limitation: label-permutation *raises* some Layer-1 scores

Scrambling the semantic labels does not merely lower CER/BDA/ISS — on a fraction of
permutations it **raises** them (measured over 9500 permutations, a Monte-Carlo
estimate, not a fixed constant): **ISS ≈ 14%, BDA ≈ 8%, CER ≈ 2%**. So these metrics
can be optimised in the wrong direction, and a score is not by itself evidence the
*right* concepts were tracked. GCS/NRS never rise under permutation (0%). Reproduce:
[`../dev-scripts/probes/label_invariance_probe.py`](../dev-scripts/probes/label_invariance_probe.py).

### GCS: degenerate inputs and gaming vector

GCS checks that conflict edges (blocks/contradicts) are followed by net-negative movement of the target belief within k=3 turns. If the target grows instead, the edge is not counted as causal. Zero-baseline edges require impact_energy ≥ 0.1 (absolute threshold) to avoid false positives from trivial fluctuations.

**Degenerate inputs (1.1.0).** Two cases that both returned `None` before 1.1.0 are now
separated: conflict edges declared but **no** target movement in-window → **0.0** (a
causality failure, not "unmeasurable"); **no** conflict edges at all → `None` (nothing
to measure — their absence is already penalized by CER, so it is not scored twice).

**GCS is a structural proxy and is gameable by construction.** Because it never sees
ground truth, a submission that knows the formula can reach 1.0 without tracking
anything correctly: keep each target's suppression windows non-overlapping, and
**escalate the suppression energy** for a repeated target (0.2 → 0.35 → 0.4, hitting
the `|delta| ≤ 0.4` ceiling on a target's fourth edge). Ground truth fixes *what*
conflicts exist, but not the *timing and amplitude* GCS rewards. The clearest case is
scenario **`03`**: `V_GROWTH` is a three-times conflict target that must **also end
higher**, and its three windows fill all 12 turns — so the required rise has to be
declared **inside** the last suppression window, where the −0.8 suppression dominates
and the rise cannot flip the net. A faithful oracle is thus *forced* to co-locate a
rise and a suppression in one window to score 1.0 — an artifact of the metric, not of
the data. Demonstrated by [`../dev-scripts/probes/oracle_probe.py`](../dev-scripts/probes/oracle_probe.py),
which reaches 1.000 on CER/GCS/BDA/ISS on all 7 scenarios.

**Run-to-run instability.** Across three identical runs of the same model
(`temperature=0`, nothing changed between runs), GCS was the **most unstable of the five
metrics**: **Δ0.15 on the aggregate** (1.1.0; Δ0.17 before the case-A fix) and **up to
Δ0.50 on individual scenarios**, more than any other metric (CER/BDA up to Δ0.25, ISS up
to Δ0.20). See [`../baselines/BASELINES.md`](../baselines/BASELINES.md). Treat single-run
GCS values with particular caution.

## Zero-trust validation

The validator rejects submissions for:
- nonce mismatch (`NONCE_MISMATCH`)
- forged hashes (`TRACE_FORGERY`)
- unbound transitions (`UNBOUND_TRANSITIONS`)
- impossible deltas (`PHYSICS_IMPOSSIBLE_DELTA`)
- weak mapping confidence (`WEAK_MAPPING` — core_id set but mapping_confidence < 0.7)
- undeclared concepts in edges (`UNDECLARED_CONCEPT`)
- inconsistent node↔edge core_id mapping (`INCONSISTENT_CORE_ID`)
- edges referencing non-existent nodes (`ORPHAN_EDGE`)
- dummy or zombie mapped concepts (`UNUSED_CONCEPTS`, `ZOMBIE_NODES`)
- dead causality (`DEAD_CAUSALITY`)
- transition spam (`TRANSITION_SPAM`)
- micro-delta spam (`MICRO_DELTA_SPAM`)

## Versioning

`standard/v1` is frozen once official scenarios are published.
Future metrics such as `TPS` and `OCS` belong to `v1.1+` once formalized in the same deterministic style.

### v1.1 candidates

- `AMB`: ambivalence score — whether two conflicting beliefs stay simultaneously active (sustained co-activation) rather than one replacing the other. v1 detects the conflict structure (CER); `AMB` scores how long both sides remain held at once.
- `OCS`: oscillation calibration — whether conflicting beliefs settle near calibrated uncertainty
- `TPS`: turning point score — whether the system detects key reversal moments

### v1.1 scope

- Scenario library expanded from 7 to 20+ across multiple belief domains (career & identity, relationships, health, money & risk, grief & loss, addiction & recovery).
- Full metric specification and methodology published as open-access material for independent reproduction.

### v2 candidates

- Semantic grounding layer: verify that node labels, core_id mappings, and edge relations are supported by source text (hybrid deterministic + LLM-assisted)
