"""
DriftBench v1.1 DRAFT — Ambivalence metric (`AMB`).

Prototype for the grant deliverable. NOT part of the frozen v1 spec.

What it measures
----------------
Ambivalence = holding two *conflicting* beliefs simultaneously active, with
neither one clearly winning, sustained over time. This is distinct from a simple
replacement, where one belief rises only as the other falls.

The metric is fully deterministic — same input, same score, always. No LLM, no
randomness. It reads the same `transitions` already present in a DriftBench
submission, reconstructs each concept's confidence trajectory (baseline 0.5,
deltas applied cumulatively and clamped to [0, 1] — exactly as core.py does),
and checks the ground-truth ambivalence pairs.

A pair (A, B) is scored as ambivalent if there is a run of at least `min_turns`
turns where BOTH beliefs are genuinely held (confidence >= active_floor) AND
neither dominates (|conf_A - conf_B| <= balance_gap).

    AMB = (# ambivalence pairs satisfied) / (# ground-truth ambivalence pairs)
"""
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


def _reconstruct_trajectories(transitions: List[Dict]) -> Dict[str, List[Tuple[int, float]]]:
    """{core_id: [(turn, confidence), ...]} from cumulative deltas, baseline 0.5."""
    traj: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
    current: Dict[str, float] = defaultdict(lambda: 0.5)
    for tr in sorted(transitions, key=lambda x: x["turn"]):
        cid = tr.get("core_id")
        if not cid or tr.get("delta") is None:
            continue
        current[cid] = max(0.0, min(1.0, current[cid] + tr["delta"]))
        traj[cid].append((tr["turn"], current[cid]))
    return traj


def _conf_at(series: List[Tuple[int, float]], turn: int) -> Optional[float]:
    """Confidence carried forward to `turn`; None if the concept is not active yet."""
    value: Optional[float] = None
    for t, c in series:
        if t <= turn:
            value = c
        else:
            break
    return value


def compute_amb(
    transitions: List[Dict],
    gt_pairs: List[Tuple[str, str]],
    active_floor: float = 0.45,
    balance_gap: float = 0.20,
    min_turns: int = 2,
) -> Optional[float]:
    if not gt_pairs:
        return None
    traj = _reconstruct_trajectories(transitions)
    turns = sorted({tr["turn"] for tr in transitions if tr.get("delta") is not None})

    satisfied = 0
    for a, b in gt_pairs:
        sa, sb = traj.get(a), traj.get(b)
        if not sa or not sb:
            continue
        run = best = 0
        for turn in turns:
            ca, cb = _conf_at(sa, turn), _conf_at(sb, turn)
            if ca is None or cb is None:
                run = 0
                continue
            if min(ca, cb) >= active_floor and abs(ca - cb) <= balance_gap:
                run += 1
                best = max(best, run)
            else:
                run = 0
        if best >= min_turns:
            satisfied += 1
    return satisfied / len(gt_pairs)


# ─── Demonstration ───────────────────────────────────────────────────────────
# Two systems process the same grief scenario. The ground-truth ambivalence pair
# is (GR_LOYALTY_PAST, GR_OPENNESS_NEW). A good system keeps both co-active for
# several turns; a naive "replacement" system drops loyalty the moment openness
# rises. AMB separates them; a direction-only metric would not.

def _demo():
    GT_AMBIVALENCE = [("GR_LOYALTY_PAST", "GR_OPENNESS_NEW")]

    def tr(cid, turn, delta):
        return {"node_id": "n_" + cid, "core_id": cid, "turn": turn, "delta": delta}

    # System A — tracks sustained ambivalence (loyalty stays high while openness grows)
    good_system = [
        tr("GR_LOYALTY_PAST", 2, 0.10),   # 0.60
        tr("GR_OPENNESS_NEW", 3, 0.08),   # 0.58  -> both ~0.6, co-active
        tr("GR_OPENNESS_NEW", 6, 0.07),   # 0.65  -> still co-active with loyalty 0.60
        tr("GR_LOYALTY_PAST", 9, -0.20),  # 0.40  -> loyalty finally releases
        tr("GR_OPENNESS_NEW", 10, 0.10),  # 0.75
    ]

    # System B — sees a simple replacement (loyalty collapses as openness rises)
    naive_system = [
        tr("GR_LOYALTY_PAST", 2, 0.10),   # 0.60
        tr("GR_LOYALTY_PAST", 3, -0.20),  # 0.40  (immediately drops)
        tr("GR_OPENNESS_NEW", 3, 0.20),   # 0.70  (jumps up)
        tr("GR_OPENNESS_NEW", 6, 0.05),   # 0.75
    ]

    amb_good = compute_amb(good_system, GT_AMBIVALENCE)
    amb_naive = compute_amb(naive_system, GT_AMBIVALENCE)

    # Cross-check against the existing v1 direction metric (BDA) from the core.
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from driftbench_core.core import compute_bda

    gt_bda = [
        {"core_id": "GR_LOYALTY_PAST", "direction": "up_then_down"},
        {"core_id": "GR_OPENNESS_NEW", "direction": "up"},
    ]
    bda_good = compute_bda(good_system, gt_bda)
    bda_naive = compute_bda(naive_system, gt_bda)

    print("DriftBench v1.1 DRAFT — Ambivalence metric (AMB)")
    print("Same grief conversation, two AIs. Did each notice the person held")
    print("loyalty-to-the-past and openness-to-the-new AT THE SAME TIME?")
    print("-" * 64)
    print(f"  {'':24}  BDA (old: direction)  AMB (new: mixed feelings)")
    print(f"  System A (got it right) : {bda_good:>10.2f}        {amb_good:>10.2f}")
    print(f"  System B (missed it)    : {bda_naive:>10.2f}        {amb_naive:>10.2f}")
    print("-" * 64)
    print("  The old direction-only check (BDA) scores both AIs the same: 1.00.")
    print("  Only the new check (AMB) tells them apart — 1.00 vs 0.00 — by seeing")
    print("  that just one AI actually held the two opposite beliefs at once.")


if __name__ == "__main__":
    _demo()
