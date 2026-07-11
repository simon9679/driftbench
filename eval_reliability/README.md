# eval_reliability

Methodology and results from the LLM-as-judge reliability study on **ES-MemEval (WWW '26)** —
the calibrated-judge counterpart to DriftBench's deterministic route.

The ES-MemEval harness itself is **not** in this repo (it is a separate, closed codebase).
What lives here is the **methodology and the measured results**: a three-layer noise
decomposition and two pre-registered ablations (with the predictions recorded *before* the
numbers).

- [`EVAL_RELIABILITY_NOTE.md`](EVAL_RELIABILITY_NOTE.md) — the three-layer noise decomposition
  (judge / answerer / ingest) with numbers and method for each.
- [`prereg_reanswer.md`](prereg_reanswer.md) — pre-registration of the answerer-noise ablation.
- [`prereg_rankoff.md`](prereg_rankoff.md) — pre-registration of the render-format ablation.

## Related work
Belief-revision benchmarks (BeliefShift, STALE, TOKI) define the *task* of detecting stale /
contradicted memory. This work is complementary: a **reproducibility / measurement layer** —
deterministic scoring (no LLM judge) plus *graded* rather than binary evidence, addressing the
scoring-reliability gap those benchmarks flag but do not yet quantify.
