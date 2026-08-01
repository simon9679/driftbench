# Canary pre-registration

Phase A2 of the validity check (falsification protocol, rule 8): the hypotheses
and thresholds are written **before any canary adapter exists**, so the exercise
cannot decay into picking a flattering interpretation after the fact. This is the
second commit of the branch; `git log --stat` shows it landed before
`tests/canaries/`.

The predictions here are **mine**. Where they differ from the predictions in the
task, the difference and the reasoning are stated explicitly — that is the point of
registering before running. Every prediction is derived by reading the scoring and
**validation** code (canaries run through `driftbench_core.validator`, the full
hash + nonce + anti-cheat path), not by running it. Phase A4 runs it; §14 of the
task reports every hit and miss, including mine.

---

## Failure threshold — and a refinement I am registering

**Task's rule:** any score **≥ 0.5** on a degenerate control (C1–C4) means the
metric does not discriminate.

I am keeping this **for the label-dependent metrics — CER, BDA, ISS** — on the
controls that scramble or withhold labels. I am **refining it for GCS and NRS**,
before running, with reasons:

- **GCS never receives ground truth.** `compute_gcs(edges, transitions, k)` checks
  only *internal* coherence — "did the conflict edges I declared precede a drop in
  the targets I declared." A self-consistent fabrication therefore scores well.
- **NRS is turn-level, not label-level.** It counts deltas on noise *turns*
  regardless of which concept they belong to.

Consequence: **C4 (shuffle) is a degenerate control only for CER/BDA/ISS.** For GCS
and NRS, C4 preserves exactly what they measure (internal causal structure; turn
timing), so a high value there is *expected* and is **not** evidence of
non-discrimination — it is a separate finding about *what those two metrics
actually measure*. C1/C2/C3 remain valid nulls for all five. I register this now so
that a high GCS/NRS on C4 in A4 is not retro-spun either way.

---

## Predicted scores (mine)

`R` = I predict the submission is **rejected by the validator before scoring**
(all five metrics become 0.0 via the REJECTED path). `—` = undefined (`None`).
Predictions are the typical case across the 7 scenarios; per-scenario detail comes
in `CANARY_RESULTS.md`.

| canary | what it is | CER | GCS | BDA | ISS | NRS |
|---|---|---|---|---|---|---|
| **C1 null** | empty state | 0.0 | — | 0.0 | **0.0** | — |
| **C2 constant** | 8 nodes @0.5, no edges, no transitions | R (0.0) | R (0.0) | R (0.0) | R (0.0) | R (0.0) |
| **C3 spam** | `contradicts` between all pairs, transitions each turn | see §C3 | see §C3 | low | low/— | low |
| **C4 shuffled** | correct structure, `core_id` permuted (fixed seed) | ~0.0 | **≈ oracle (high)** | ~0.0 | ~0.0 | **≈ oracle (high)** |
| **C5 oracle** | ground truth rewritten as a submission | **1.0** | **1.0** | **1.0** | high | **1.0** |

**Differences from the task's table, stated up front:**

1. **C1 / ISS = 0.0, not `—`.** With an empty node set, `to_id` is absent from the
   confidence map, and the code returns **0.0** (`if to_id not in cm: return 0.0`),
   not `None`. A null system scoring 0.0 on ISS is still correct discrimination, so
   the validity verdict is unchanged — but the *number* is 0.0, and I predict 0.0.
2. **C2 is rejected, not scored.** All eight nodes carry a `core_id` but appear in
   no edge and no meaningful transition, so `UNUSED_CONCEPTS` fires and the whole
   submission is REJECTED → every metric 0.0 (not GCS `—` / NRS `—`). The
   discrimination here is done by the **validator's anti-cheat, upstream of the
   metric** — worth stating, because it means C2 does not actually exercise the
   scoring functions.
3. **C4 / GCS and NRS ≈ oracle, not ~0.0** — see the refinement above.

---

## C3 — the open question, two competing predictions (register both)

The task frames C3 as genuinely open. I register **three** outcomes, ranked by what
I think the code does, all falsifiable in A4:

- **П1 — rejected.** "Transitions each turn" over a spam of edges most likely trips
  an anti-cheat gate first: `TRANSITION_SPAM` (> 20 transitions in one turn) if the
  adapter is dense, or `DEAD_CAUSALITY` (a `contradicts` edge whose source sat below
  0.2 confidence when created), or `ZOMBIE_NODES`. → all 0.0.
- **П2′ — scored, but CER ≈ 0.13, not > 0.5.** If it slips past the gates, CER is
  `F1` of "all directed pairs" vs the true few. With ~4 true pairs out of 8×7 = 56
  directed pairs: `tp=4, fp=52, fn=0 → F1 = 8/60 ≈ 0.13`. **Precision collapses, so
  F1 stays well under 0.5.** NRS in this branch should be **low** (transitions on
  noise turns are intrusions). GCS ambiguous.
- **П2 (the task's worry) — CER > 0.5.** I predict this is **false**, and I am
  saying so before the run: F1 arithmetic forbids it unless the true-conflict set is
  a large fraction of all pairs, which it is not. **If A4 shows CER ≥ 0.5 on C3, I
  was wrong and it is an NRS-level finding — recorded, not smoothed.**

The number of edges/transitions per turn in the C3 adapter is a design choice that
decides П1 vs П2′. I will build C3 to stay **just under** the anti-cheat limits
(≤ 20/turn), so that C3 tests the **metric**, not only the gate — otherwise C3
tells us only that the anti-cheat works, which C2 already shows.

---

## C5 — the positive control, blocking

C5 rewrites each scenario's ground truth into a valid submission: an edge for every
true conflict pair, a transition realizing every true belief change, node
confidences that make the target identity overtake the source, and no movement on
noise turns.

**Prediction: CER = GCS = BDA = NRS ≈ 1.0, ISS high (≥ 0.5).**

**This is a hard gate (task §7.4).** If C5 does **not** reach ~1.0 on CER/GCS/BDA/NRS,
I stop and report before touching anything else — because a benchmark whose own
ground truth cannot score well invalidates every published baseline, and no result
past that point is trustworthy. C1–C4 are meaningless without C5: a metric that
always returns 0.0 would "pass" every degenerate control for the wrong reason.

---

## Held-out canaries H1–H4 — sealed

Written as adapters in phase A4 **but not run** until the very end of PR-B, opened
exactly once (task §4, §11). Their predictions are registered here and **must not be
consulted while making any fix** — a fix that is tuned until H1–H4 look good is a
fit, and the set is declared burned if it is run more than once.

| held-out | what it is | prediction |
|---|---|---|
| **H1 partial** | half the concepts tracked correctly, half ignored | **middling** (≈ 0.4–0.6 on CER/BDA); not 0, not 1 |
| **H2 delayed** | correct tracking, every transition shifted +2 turns later | tests whether a *timing* error is punished; GCS most exposed (window `k=3`), BDA should stay high (direction unchanged) |
| **H3 overconfident** | correct structure, deltas ×2 (within the 0.4 cap) | tests scale sensitivity; I predict **little movement** in CER/BDA/NRS (thresholds are one-sided), possible ISS increase |
| **H4 inverted** | correct structure, all directions reversed | **≈ 0** on BDA (wrong directions) and GCS (no suppression); **if either stays high, the metric measures presence of structure, not correctness** — the same lesson C4 previews for GCS |

H4 and C4 together bracket the deepest question: **do GCS (and BDA) score being
*right*, or only being *structured*?** C4 scrambles labels, H4 flips directions. I
predict BDA catches H4 (direction-aware) but that **GCS may not** (it has no notion
of the "correct" direction relative to ground truth, only "downward"). Registered
before the run.

---

## GCS case-B, registered for PR-B (competing, decided by C1/C2 data)

From task §9.1: when a system reports **no conflict edges at all**, GCS returns
`None`. Two candidate resolutions, both registered now, chosen later **by C1/C2
behavior, not by argument**:

- **→ 0.0:** `None` hides a failure — the same logic that fixed NRS.
- **→ stays `None`:** absence of edges is already punished by CER = 0.0; scoring it
  0.0 in GCS too is a double penalty for one omission.

The distinct case-A (edges present, no downstream movement → currently `None`, a
hidden causality failure) I predict **should** become 0.0; that is a PR-B change, not
pre-judged here.
