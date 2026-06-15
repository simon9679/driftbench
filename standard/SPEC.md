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

- `CER`: conflict edge recovery against ground-truth conflict pairs
- `GCS`: do conflict edges cause downstream suppression of the target belief? (causal = net_impact < −0.05 within k=3 turns after edge creation)
- `BDA`: whether the right canonical beliefs move in the right direction
- `ISS`: whether the target identity overtakes the source identity
- `NRS`: noise resistance — no significant confidence deltas on noise turns

### GCS limitation

GCS checks that conflict edges (blocks/contradicts) are followed by net-negative movement of the target belief within k=3 turns. If the target grows instead, the edge is not counted as causal. Zero-baseline edges require impact_energy ≥ 0.1 (absolute threshold) to avoid false positives from trivial fluctuations.

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
