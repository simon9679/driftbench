# Pre-registration — Render-format (rank-OFF) ablation (ingest-noise layer)

*Registered before the numbers. Two independent predictions were recorded — and they were
opposite. The data settled them; both are reproduced here, the losing one included.*

## Question
The re-answer ablation showed the conflict drop lives in the **input**, not the answerer. The
input differs in two ways at once: a new graph (from re-extraction) **and** a new conflict
render format (rank-based instead of thresholded). Which one caused the −0.40?

## Design (one variable)
- **Input:** the same re-extracted (v1.1) belief graphs, unchanged.
- **Variable:** the conflict render format only — re-render with the **old** thresholded
  format instead of the rank-based one, then re-answer.
- **Held constant:** same graphs, same answer/judge prompts, same official judge, temp=0,
  same budget. No re-ingest. One run.

## Pre-registered outcomes
- **R1 — conflict recovers to ~0.75–0.90.** The **render format** was the cause → revert the
  rank format on the machine-consumed path.
- **R2 — conflict stays ~0.45.** The **re-extracted graph** was the cause, not the format →
  the format is exonerated, and the "single-ingest, ingest variance substantial" caveat lands
  on every subset claim (including the flagship conflict number).
- **In-between → mixed.**

## Recorded predictions (before numbers) — OPPOSITE
- **Prediction 1: R2 ~65%** — the cause is the graph, not the format.
- **Prediction 2: leaned R1** — the cause is the format (the answering content was present in
  the new render, and format was the only thing that had changed at that render step).

## Outcome — R2 confirmed
Re-rendering the same v1.1 graphs with the old format left conflict at **0.45 → 0.45**
(identical); all collapsed conflict items stayed collapsed. Restoring the v1.0 *graph* had
recovered them; changing only the *format* did not. **The cause is the re-extracted graph;
the render format is exonerated.** Prediction 1 (R2) held; Prediction 2 (R1) was wrong.

## Consequence
Subset-level capability scores on this benchmark are dominated by ingest stochasticity: a
single re-ingest swung conflict −0.40 and user-modeling +0.15 (both directions), far beyond
judge (~0.10) or answerer (~0.05) noise. Aggregate verdicts were unchanged across both
ingests. See `EVAL_RELIABILITY_NOTE.md`.
