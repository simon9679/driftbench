# What we measured — evaluation-reliability program (ES-MemEval, 2026)

*Dry, chronological summary of measured results. Numbers are from pre-registered experiments on
an internal harness over the public ES-MemEval benchmark; raw per-item dumps are available on
request. Negatives are on equal footing with positives; n's are small — read the caveats.*

## Summary — what survived, what failed
| thing | verdict |
|---|---|
| **Evaluation-reliability layer** (noise decomposition, judge-bias, ingest-variance) | **survived every test** |
| Memory as an aggregate product (belief-graph beats baselines) | **failed** (no aggregate edge, two ingests) |
| Conflict feature (state block over retrieval) | **parity / redundant** |
| Belief-dynamics ranking as a product | **failed** (blind reader did not confirm the ranking) |
| AMF (ambivalence signal) | **dead** (mechanistic) |
| Extraction contract (semantic correctness) | **clean** (not itself a product) |

## Measurements (claim → number → method)

1. **Three-layer noise stack, orders of magnitude apart.** judge ≈ **0.10**, answerer ≈ **±0.05**,
   ingest ≈ **±0.40** subset swing. Method: K=20 blind human relabel (judge); re-answer on
   byte-identical input (answerer); controlled re-ingest (ingest).

2. **A "significant" subset claim does not survive re-ingestion — the significant subgroup flips.**
   Ingest A: long-horizon gap **+0.60 significant** (short +0.23, not sig). Ingest B (full re-ingest,
   same system): **short +0.31 significant**, long inconclusive. The significant subgroup moved from
   long to short between two ingests. Method: identical harness, two independent ingests.

3. **On a long conversation, re-ingestion shares almost nothing with the prior graph.**
   Fresh vs prior 33-session graph: **94.7%** label-level symdiff. Caveat: label-level overstates
   concept-level divergence (paraphrase), but the surface a reader/judge sees differs ~95%.

4. **Wall-clock non-determinism is NOT a noise source (hypothesis honestly closed).** Realistic
   inter-turn timing: max Δ = **0.0012** (≈0); divergence only at a 5-day injected gap (**0.24**);
   logical clock exactly deterministic (0.0). Method: 0-call replay of cached provenance, three timings.

5. **Adding a computed state block over retrieval does not raise conflict detection — it is redundant.**
   Pre-registered gate: conflict delta **+0.10** (win threshold was +0.30) → **parity**; aggregate
   guard held. Style attribution: the answer cited the state block **0 / 60** times — the answerer
   takes the conflict from the retrieved text, not the block. Method: same retrieval + a fixed-size
   state block from a prior graph, same judge, one split, no new ingest.

6. **A domain-naive blind reader could not confirm the belief-dynamics ranking.** Blind top-5 match
   **2 / 5** (needed ≥3/5), overall **44%** (below chance). Controls passed: 5 no-dynamics decoy
   dialogues all ranked at the bottom; 23/23 dialogues on a foreign corpus survived extraction with
   0 format-driven failures. Method: pre-registered blind human relabel, key hidden.

7. **The evolving-state benchmark material is not guaranteed single-person coherent.** One flagged
   conversation chained disparate topics over 32 sessions with the speaker unnamed early and named
   late. "Did the person change?" is only as well-posed as single-person coherence. Reported as a
   finding, **respectful to the benchmark authors** — it bears on the validity of the evolving-state
   benchmark class and on any system measured on it, including ours.

## Discrepancy check (not smoothed)
- judge-noise **0.15 → 0.10**: auto-reports used 0.15 provisional; the K=20 relabel finalized 0.10.
- short-gap **+0.23 vs +0.31**: not a conflict — different ingests; their divergence *is* result 2.

## Caveats
Small n (subset n≈10–20, blind read n=10, extraction n=2 dialogues). Lexical (BM25) retrieval, not
embedding. Single answerer/judge model. The state-block result is a lower bound. These bound
generalization; they do not flip any verdict.
