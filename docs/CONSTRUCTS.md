# DriftBench metric constructs

What each metric is *supposed* to measure, written down **before** any canary
adapter exists, so the canaries test the construct rather than the implementation
being reverse-engineered into a construct. This is phase A1 of the validity check
(falsification protocol, rule 5). It is a statement of intent; where the current
implementation departs from it, that gap is a finding for later phases, noted here
but **not fixed in this document**.

For each metric: what it measures (in one sentence, without reference to code),
what earns 1.0, what earns 0.0, what is *undefined* (`None`) and why that is not
the same as 0.0, and the arbitrary constants it rests on — each justified or
honestly marked as chosen without justification.

A cross-cutting principle, learned from the 1.0.1 NRS defect: **a non-answer must
not earn a score.** A system that emits nothing, or omits the structure a metric
needs, has not demonstrated the ability the metric measures. The honest encoding of
"the system did not give me something to judge" is `None` (undefined), not a number
— and certainly not the maximum. `0.0` means "the system answered, and the answer
was wrong/absent"; `None` means "there is nothing here to score." Conflating the two
in either direction is a construct-validity bug.

---

## CER — Conflict Edge Recovery

**Measures.** Whether the system found the *right contradictions* — the pairs of
beliefs that genuinely conflict in the conversation.

**Earns 1.0.** The set of conflict pairs the system reports is exactly the set of
true conflict pairs — every real conflict found, no invented ones. (Pairs are
**directed**: reporting *(B blocks A)* when the truth is *(A blocks B)* is wrong.)

**Earns 0.0.** The system reports conflict pairs but **none** of them is a true
pair (zero overlap with ground truth).

**Undefined (`None`).** The scenario has no conflicts to recover. There is nothing
to measure, so any number — including 0.0 — would be a fabricated verdict. This is
distinct from 0.0, which is a real failure on a scenario that *did* contain conflicts.

**Arbitrary decisions.**
- **F1** (harmonic mean of precision and recall) as the aggregate. Justified: a
  benchmark must punish *inventing* conflicts (precision) as hard as *missing* them
  (recall); F1 does both. A consequence worth stating plainly: a system that reports
  **all** possible pairs gets high recall but very low precision, so F1 stays low —
  spamming edges should not pass. (Phase A4 canary C3 tests exactly this.)
- **Directed pairs.** Justified: "A contradicts B" and "B contradicts A" are
  different causal claims.
- No numeric thresholds. Set-membership only; duplicate edges collapse.

---

## GCS — Graph Causal Score

**Measures.** Whether the conflicts the system found actually *did something* — a
belief it declared to be under attack should then measurably weaken.

**Earns 1.0.** Every conflict edge is followed, within a few turns, by the target
belief moving down.

**Earns 0.0.** Conflict edges exist and are testable (the target belief does move
in the window), but **none** of them suppressed the target — the system claimed
conflicts that had no downstream consequence.

**Undefined (`None`).** *(This is where the current construct is muddy — flagged,
not fixed.)* Today `None` is returned in two cases that mean opposite things:
  - **(A)** conflict edges exist but the target belief produced **no movement at
    all** in the window — arguably a *causality failure* the metric should score as
    0.0, not hide as "unmeasurable";
  - **(B)** the system reported **no conflict edges at all** — genuinely nothing to
    measure.
  Collapsing (A) into `None` is the same defect pattern as the NRS bug: a failure
  dressed as "not applicable." Case (A) is a candidate to become 0.0 in a later
  phase; case (B) is a real undefined. This document records the distinction; the
  canaries (C1/C2) will decide case (B).

**Arbitrary constants** (all untested until phase A5):
- **`k = 3`** — how many turns after an edge the suppression must appear. Chosen as
  a plausible "short-term" window; a calibration run over `k∈{1,2,3,4,5,8}` shows a
  plateau at 2–5, so the value is not on a suspicious peak (see SENSITIVITY.md).
- **`0.1`** — minimum total movement ("impact energy") for a zero-baseline edge to
  count, meant to reject trivial fluctuation. **Chosen without independent
  justification** — tested in A5.
- **`1.5`** — how much bigger than its prior baseline a movement must be to count as
  caused by the edge. **Chosen without justification** — tested in A5.
- **`-0.05`** — the movement must be net *downward* by at least this much. Shares
  the 0.05 "material change" threshold used elsewhere; **not independently justified**.

---

## BDA — Belief Drift Accuracy

**Measures.** Whether the beliefs that *should* change over the conversation move in
the *right direction* (up, down, or up-then-down).

**Earns 1.0.** Every belief the ground truth says should move does move, the right way.

**Earns 0.0.** None of the beliefs that should move does so correctly — either they
did not move materially, or they moved the wrong way.

**Undefined (`None`).** The scenario specifies no belief changes to check. (In
practice every official scenario has some, so `None` is a guard, not an expected
score.) A concept that simply has no transitions is **not** undefined — it counts as
"did not move" and lowers the score, which is correct: silence about a belief that
should have moved is a failure, not a non-answer.

**Arbitrary constants.**
- **`0.05`** — how big a delta counts as "moved" rather than noise. Shared with NRS.
  **Chosen without independent justification** — tested in A5.
- **`up_then_down` requires both legs in order.** Justified: a full reversal is the
  claimed construct; a partial (only the "up") is not the same phenomenon and scores
  0 for that concept.

---

## ISS — Identity Shift Score

**Measures.** Whether, by the end, the *new* identity has clearly overtaken the
*old* one in the system's belief state.

**Earns 1.0.** The target identity ends far more confident than the source
(a large positive gap).

**Earns 0.0.** The target does not meaningfully lead the source (gap below the
threshold), **or** the system never built the target identity at all.

**Undefined (`None`).** The scenario specifies no identity shift to look for.
*(Flagged, not fixed:)* the implementation also returns `None` in a second,
inconsistent case — when the **source** identity was never built — while the
mirror case (the **target** never built) returns 0.0. Both mean "the system failed
to construct a concept the metric needs," yet one is punished (0.0) and the other
excused (`None`). This asymmetry is a construct bug; phase A4 canary C4 will show
whether it affects any real number. The principled resolution (both → 0.0, since a
missing required concept is a failure to answer, not an unmeasurable scenario) is a
candidate for a later phase.

**Arbitrary constants.**
- **`0.2`** — the minimum gap that counts as a shift at all (below it → 0.0).
  **Chosen without justification** — tested in A5.
- **`0.5`** — the gap span over which the score ramps from 0 to 1 (a gap of
  0.2 → 0.0, a gap of 0.7 → 1.0). **Chosen without justification** — tested in A5.
- **default 0.5** for a missing source confidence. A modelling choice: absent
  evidence, assume the source sat at neutral. **Weakly justified.**

---

## NRS — Noise Resistance Score

**Measures.** Whether the system *ignored the turns designed to distract it* — the
noise turns should move no belief.

**Earns 1.0.** No belief moves materially on any noise turn — **and** the system
actually produced a belief trajectory to begin with.

**Earns 0.0.** Every noise turn moved a belief past the threshold — the system was
maximally distractible.

**Undefined (`None`).** Two real cases: the scenario marks **no** noise turns (there
is nothing to resist), **or** the system produced **no transitions at all** (an empty
state — a non-answer, fixed in 1.0.1 to return `None` instead of the maximum). The
second is the whole reason this document exists: "the system emitted nothing" is not
"the system perfectly resisted noise."

**Arbitrary constants.**
- **`0.05`** — how big a delta on a noise turn counts as being distracted ("an
  intrusion"). Shared with BDA. **Chosen without independent justification** —
  tested in A5.

---

## Summary of construct-level flags (for later phases, not fixed here)

1. **GCS** returns `None` for both "causality tested and failed" and "nothing to
   test" — the first should likely be 0.0 (§9.1 candidate).
2. **ISS** punishes a missing *target* (0.0) but excuses a missing *source*
   (`None`) — an asymmetry that should be unified (§9.2 candidate).
3. Six of the metrics' constants (`0.05`, `0.1`, `1.5`, `0.2`, `0.5`, and the GCS
   `-0.05`) currently rest on no independent justification and are tested for the
   first time in phase A5.
