# Changelog

All notable changes to DriftBench will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-05-30

### Added
- **`driftbench_core`** — deterministic scoring engine with zero external dependencies
- **Five metrics**: CER, GCS, BDA, ISS, NRS — all fully deterministic, no LLM judge
- **Zero-trust validator** — rejects forged hashes, impossible deltas, zombie nodes, transition spam, dead causality
- **v1 Ontology** — 8 frozen concepts across 4 categories (Identity, Values, Fears, Goals)
- **7 official scenarios** in `standard/v1/scenarios/`
- **`BaseAdapter`** — base class for integrating any cognitive engine
- **`TBGAdapter`** — reference adapter showing how a Temporal Belief Graph engine maps into the submission format (engine not included)
- **Universal Runner** (`adapters/simple/driftbench_run.py`) — evaluate any LLM (OpenAI, Anthropic, Gemini, custom endpoint) via CLI
- **CLI tool** `driftbench-validate` — validate and score any submission against any scenario
- **GitHub CI** — automated testing on Python 3.10, 3.11, 3.12
- **Apache 2.0 license**

### Spec
- `standard/SPEC.md` — full submission contract
- `standard/v1/` — frozen ontology and scenarios

---

## [0.3.0] — 2026-04 (research phase)

- Added GCS (Graph Causal Score) metric with k=3 window and direction check
- Added NRS (Noise Resistance Score) for turns marked as irrelevant
- Anti-cheat: TRANSITION_SPAM and MICRO_DELTA_SPAM guards

## [0.2.0] — 2026-03 (research phase)

- Added ISS (Identity Shift Score)
- Added BDA (Belief Drift Accuracy) with up/down/up_then_down directions
- Introduced zero-trust nonce validation

## [0.1.0] — 2026-02 (research phase)

- Initial belief-graph data model: nodes, edges, transitions
- CER (Conflict Edge Recovery) metric
- SHA-256 trace hashing bound to conversation turns

---

## Upcoming

### [1.1.0] — planned

- `OCS`: Oscillation Calibration Score — conflicting beliefs settle near calibrated uncertainty
- `TPS`: Turning Point Score — detects key reversal moments
- Expanded ontology (v1.1): additional domains beyond career/identity

### [2.0.0] — planned

- Semantic grounding layer: verify node labels and edge relations against source text
- Hybrid deterministic + lightweight semantic validation
