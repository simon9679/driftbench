# Changelog

All notable changes to DriftBench will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **LLM baselines** over the 7 official v1 scenarios — `baselines/BASELINES.md` plus
  per-scenario JSON in `baselines/llm/` for GPT-4.1, Claude Haiku 4.5, gpt-oss-120b,
  and zai-glm-4.7. Scored with the canonical `driftbench_core` metrics (not the
  zero-trust validator); coverage-honest (parse failures excluded from means).
- **`run_baselines.py`** — multi-provider orchestrator (Cerebras / Anthropic) that
  injects the frozen ontology into each official scenario before scoring, so emitted
  `core_id`s match v1.

---

## [1.1.0] — 2026-08-01

### Changed
- **GCS degenerate-input semantics.** `compute_gcs` no longer collapses two different
  cases into `None`: conflict edges declared but with no target movement in the window
  now score **0.0** (a causality failure), while genuinely having no conflict edges stays
  `None` (nothing to measure — already penalized by CER). One published aggregate moves as
  a result — repeated-run GCS spread **Δ0.17 → Δ0.15** (6 corpus values shift `None → 0.0`);
  CER/BDA/ISS spreads are unchanged. A metric definition changed, so this is a minor release.
- **ISS symmetry.** A missing *source* concept now scores **0.0**, matching the missing
  *target* case, instead of the old `None`. 0 firings in the current corpus, so no
  published number moves.

### Added
- **Validity probes** under `dev-scripts/probes/` (offline, deterministic, no keys): a
  label-invariance probe (GCS/NRS 100% label-invariant; CER/BDA/ISS degrade and can
  pathologically improve) and an oracle probe (an ideal submission reaches 1.000 on
  CER/GCS/BDA/ISS on all 7 scenarios — the metrics have a reachable maximum). Outputs and
  a guide under `docs/probes/`.

### Documentation
- **Overclaim removed from `SPEC.md`.** GCS and NRS are now described as **structural /
  temporal** diagnostics (internal coherence / turn-level stability), **not** semantic
  metrics — the probe shows both are 100% invariant to label scrambling. Added: the two
  layers must not be averaged with CER/BDA/ISS; the GCS gaming vector (non-overlapping
  windows + energy escalation, with scenario `03` as the worked example); and the
  label-permutation reversal rates (ISS ≈ 14%, BDA ≈ 8%, CER ≈ 2%, a Monte-Carlo estimate).
- README gains a **Validity checks** section; the stale "NRS defect is a v1.1 candidate"
  note (left over from before the 1.0.1 fix) is corrected to "fixed in 1.0.1".
- Related work cites **BeliefShift (Myakala et al., 2026)** and links the falsification
  protocol the check follows.

---

## [1.0.1] — 2026-08-01

### Fixed
- **`NRS = 1.00` on an empty state.** A scored response that failed to parse yielded an
  empty belief graph, which the Noise Resistance Score rewarded with the maximum (1.00)
  rather than an undefined result — a system that emitted nothing scored as perfectly
  noise-resistant. `compute_nrs` now returns *undefined* (`None`) for an empty state (no
  transitions); a legitimate 1.00 (transitions present, none crossing the noise-turn
  threshold) is unaffected. Found only by repeated baseline runs (2 of 21 parse failures,
  both on `11_noise_resistance`; see `baselines/BASELINES.md`). Because scores change on
  one input (empty-state `NRS` on `11_noise_resistance`: `1.00 → undefined`), the emitted
  `spec` bumps `1.0.0 → 1.0.1`. The frozen `standard/v1/` ontology and scenarios are
  untouched.

### Added
- **`run_baselines.py --rescore`** — recompute `scores` from each saved `state` under
  `baselines/llm/**` and `baselines/variance/**`, entirely offline (no keys, no network),
  then regenerate `baselines/BASELINES.md`. Lets historical runs be rescored from frozen
  artifacts without re-calling any provider; used here to apply the NRS fix to the corpus.

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
