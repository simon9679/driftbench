# Pre-registration — Re-answer ablation (answerer-noise layer)

*Registered before the numbers. Reproduced here as written, including the recorded prediction
that the data went on to refute — the point of pre-registration is that the losing call is
not erased.*

## Question
A full re-ingest had dropped the conflict-detection subset from 0.85 to 0.45. Was that drop
caused by the **answerer** (the LLM that reads the memory and writes an answer, re-run at
temp=0 but not byte-exact), or by the **input** it was given (the re-extracted graph / its
rendering)?

## Design (one variable)
- **Input:** the byte-identical frozen v1.0 memory render strings.
- **Variable:** a fresh answerer + judge pass only. No re-ingest, no render change.
- **Held constant:** same answer/judge prompts, same official 0/1/2 judge, temp=0, same
  representation budget. One run, no re-rolls. All 60 QA (not just the conflict subset), to
  measure the answerer-noise floor across every capability.

## Pre-registered outcomes
- **A — conflict recovers to ~0.85 on the v1.0 input.** Then the −0.40 was caused by the
  changed input (graph/render), not the answerer. Next step: isolate render format.
- **B — conflict stays ~0.45 on identical v1.0 input.** Then the −0.40 is answerer
  non-determinism; the engineering changes are exonerated and any "edges degrade conflict"
  claim is unsupported.
- **C — partial recovery.** Mixed; split by magnitude.

## Recorded prediction (before numbers)
From the disk-only forensics: **~70% that the drop was answerer non-determinism** (the
answering terms were present in the new render, yet the answerer had abstained).

## Outcome — prediction REFUTED (Outcome A)
On byte-identical v1.0 input the answerer reproduced the good scores: conflict 0.85 → **0.90**
(original vs re-answer), aggregate 0.68 → 0.72. The answerer is stable to **≈ ±0.05** on
identical input. The −0.40 therefore lives in the **input**, not the answerer — the ~70%
answerer-lottery prediction was wrong, and the next ablation (render format) followed.
