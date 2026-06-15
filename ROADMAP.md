# DriftBench Roadmap

This roadmap describes planned development across future spec versions.
The v1 spec and ontology are **frozen** — all additions are additive and backward-compatible.

---

## ✅ v1.0.0 — Released (May 2026)

- Deterministic scoring engine with zero external dependencies
- Five metrics: CER, GCS, BDA, ISS, NRS
- Zero-trust validator with anti-cheat guards
- v1 ontology: 8 concepts (Identity, Values, Fears, Goals)
- 7 official scenarios covering burnout, conflict, identity shift, noise resistance
- Universal runner for OpenAI / Anthropic / Gemini / custom endpoints
- CLI tool `driftbench-validate`

---

## 🔄 v1.1 — In Design

**New metrics:**

| Metric | Name | Description |
|--------|------|-------------|
| `AMB` | Ambivalence Score | Whether two conflicting beliefs stay *simultaneously* active (sustained co-activation) instead of one simply replacing the other |
| `OCS` | Oscillation Calibration Score | Whether conflicting beliefs settle near calibrated uncertainty (0.5) rather than oscillating |
| `TPS` | Turning Point Score | Whether the system correctly identifies key reversal moments in the narrative |

`AMB` formalizes the signal that originally motivated DriftBench: holding two
contradictory positions at once, and which one eventually wins. v1 detects the
conflict *structure* (CER); `AMB` turns sustained ambivalence into a
deterministic score.

**Domain expansion — from 7 scenarios to 20+:**

The v1 scenarios all live in a single domain (career / identity). v1.1 broadens
coverage so the benchmark is useful for any cognitive AI system:

- Career & identity
- Relationships
- Health
- Money & risk
- Grief & loss
- Addiction & recovery

Each new domain ships with the canonical concepts it needs and a v1 → v1.1
migration guide.

**Open methodology:**
- Full metric specification and scoring methodology published as open-access
  material, so any researcher can reproduce results independently.

**Tooling:**
- `driftbench-run` as an official CLI entry point (wrapping the universal runner)
- PyPI package release

---

## 🔮 v1.2 — Planned

**More official scenarios:**
- Delayed contradiction with noise injection
- Multi-agent conflict (two perspectives in one conversation)
- Long-horizon (12+ turn) belief trajectories

**Community scenario packs:**
- Formalized process for community-contributed scenario packs
- Scenario pack validation tool

---

## 🚀 v2.0 — Long-term

**Semantic grounding layer:**

The v1 validator checks structural and cryptographic integrity but does not verify that node labels, `core_id` mappings, or edge relations are actually supported by the source text. v2 adds a semantic validation layer:

- Lightweight deterministic extraction of semantic triples from conversation turns
- Cross-check against submitted graph structure
- Hybrid approach: deterministic where possible, minimal LLM assistance for ambiguous cases

**Goal:** maintain full reproducibility while closing the semantic self-reporting gap.

---

## How to influence the roadmap

- Open a GitHub issue with `[roadmap]` in the title
- Join the discussion on existing roadmap issues
- Submit a PR with a proposed scenario or metric spec

The spec is community-driven. Production use cases and failure modes from real integrations are the primary input for prioritization.
