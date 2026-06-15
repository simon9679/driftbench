# DriftBench — Abstract

---

## AI Safety Framing

**One sentence:**
DriftBench is an open, deterministic benchmark that measures whether AI systems can maintain belief consistency, resist manipulation, and track identity under adversarial pressure — without relying on an LLM judge.

**The problem:**
Current AI evaluation relies almost exclusively on static question-answer benchmarks (MMLU, HellaSwag) or LLM-as-judge setups. Neither captures a safety-critical property: whether an AI system's *internal belief state* remains coherent and manipulation-resistant across a multi-turn conversation. A system that gives correct final answers but arrives at them through internally inconsistent or drift-prone reasoning is a latent safety risk — especially in therapeutic, coaching, or high-stakes advisory contexts.

**What DriftBench measures:**
- **Belief consistency (BDA)** — do the right internal beliefs move in the right direction?
- **Manipulation resistance (NRS)** — does the system ignore adversarially injected irrelevant turns?
- **Conflict coherence (CER, GCS)** — are detected contradictions causally meaningful, not hallucinated?
- **Identity stability (ISS)** — can the system track a persona transition without drift?

**Why determinism matters for safety:**
Non-deterministic LLM judges cannot be audited or reproduced. DriftBench produces the same scores for the same inputs, always. This makes it suitable for safety certification, regression testing, and formal audits — use cases where LLM judges are structurally inadequate.

**Current state:**
- v1.0.0 released, Apache 2.0, zero external dependencies
- 7 official scenarios, 5 deterministic metrics, zero-trust validator with cryptographic trace hashing
- Universal runner supports OpenAI, Anthropic, Gemini, and any custom endpoint

---

## Public Goods / Open Infrastructure Framing

**One sentence:**
DriftBench is an open protocol and benchmark for evaluating the cognitive coherence of AI agents — a missing piece of public infrastructure for the emerging ecosystem of autonomous AI systems.

**The problem:**
The AI ecosystem lacks a shared, neutral standard for measuring *how well* an agent maintains a coherent internal model of the world across a conversation. Every team building cognitive agents (memory systems, belief graphs, persona engines) invents its own evaluation criteria — making it impossible to compare systems, reproduce results, or build shared knowledge.

**What DriftBench provides:**
- A **frozen, versioned specification** (like an RFC) that any team can implement against
- **Fully reproducible metrics** — no cloud API calls, no LLM judges, no randomness
- A **zero-trust submission format** with cryptographic hashes that make result tampering impossible
- An **open adapter API** — integrate any cognitive engine in under 30 minutes

**Why this is public goods infrastructure:**
DriftBench is to cognitive AI evaluation what RFC 6749 is to OAuth: a shared protocol that prevents fragmentation and enables an ecosystem to form around a common standard. Without it, every benchmark is proprietary, every result is incomparable, and the field cannot accumulate shared knowledge.

**Decentralization alignment:**
- Zero external dependencies — runs fully locally, no cloud lock-in
- Verifiable results — cryptographic hashing enables trustless result submission
- Open standard — Apache 2.0, community-governed roadmap
- Designed for permissionless extension — any team can add scenarios, adapters, or metric packs

**Current state:**
- v1.0.0 released with 7 scenarios and 5 metrics
- Python package, CLI tool, universal LLM runner
- Roadmap: v1.1 (new metrics + ontology), v2.0 (semantic grounding layer)
