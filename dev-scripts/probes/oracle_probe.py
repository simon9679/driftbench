#!/usr/bin/env python3
"""
Oracle probe
============
Builds, from each scenario's ground truth, a deliberately ideal submission and
checks the metrics can reach the maximum. Without this, low canary scores mean
nothing: a metric that always returns 0.0 would pass every degeneracy check.

The construction is the substantive part (this is where a naive build fails):

* nodes for every concept in conflicts / belief_changes / identity_shift;
* ISS: confidence[to_id]=0.95, confidence[from_id]=0.15 (gap >= 0.7 -> 1.0);
* for every conflict edge, a suppressing transition on the target inside the
  window [t_create, t_create+3], and the windows for one target DO NOT overlap;
* energy escalation: a repeated target needs impact_energy > baseline_avg*1.5,
  so amplitude climbs (0.2 -> 0.35 -> 0.4x2). The 3rd edge on one target needs
  more than a single |delta|<=0.4 can carry, so its window holds two deltas;
* BDA transitions sit OUTSIDE every GCS window and outside noise_turns;
* up_then_down is realized as +0.3 then -0.3;
* no transition ever lands on a noise turn (keeps NRS = 1.0).

Everything is scored through the real ``evaluate`` path (nonce + integrity +
anti-cheat + scoring), never a bare ``compute_*`` call. Offline; the repo is not
modified.

Usage::

    python dev-scripts/probes/oracle_probe.py --out out.json
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCEN_DIR = ROOT / "standard" / "v1" / "scenarios"
METRICS = ["CER", "GCS", "BDA", "ISS", "NRS"]
NONCE = "oracle_probe"

sys.path.insert(0, str(ROOT))
from driftbench_core.core import hash_turn, _h_dict, evaluate  # noqa: E402


def _load_json(path):
    return json.loads(Path(path).read_text("utf-8-sig"))


def build_oracle(scenario):
    """Return (nodes, edges, transitions) that should score 1.0 on every metric."""
    messages = scenario["messages"]
    n = len(messages)
    gt = scenario["ground_truth"]
    conflicts = [tuple(c) for c in gt.get("conflicts", [])]
    belief_changes = gt.get("belief_changes", [])
    ishift = gt.get("identity_shift", {})
    noise = set(gt.get("noise_turns", []))
    to_id, from_id = ishift.get("to_id"), ishift.get("from_id")

    def th(turn):  # trigger/text hash for a 1-indexed turn
        m = messages[turn - 1]
        return hash_turn(turn, m["user"], m["assistant"])

    allowed = [t for t in range(1, n + 1) if t not in noise]  # turns usable for transitions

    concepts = set()
    for s, t in conflicts:
        concepts.add(s); concepts.add(t)
    for bc in belief_changes:
        concepts.add(bc["core_id"])
    for cid in (to_id, from_id):
        if cid:
            concepts.add(cid)

    def conf(cid):
        if cid == to_id:
            return 0.95
        if cid == from_id:
            return 0.15
        return 0.5

    node_id = {c: f"n_{c}" for c in concepts}
    nodes = [{"id": node_id[c], "label": c, "core_id": c, "mapping_confidence": 1.0,
              "confidence": conf(c), "evidence_turn": 1, "text_hash": th(1)} for c in sorted(concepts)]

    # --- GCS: one edge per conflict pair, non-overlapping windows per target ---
    edges = []
    transitions = []
    by_target = defaultdict(list)
    for s, t in conflicts:
        by_target[t].append(s)

    used_turns_for_target = defaultdict(list)   # target -> list of create turns
    supp_turns = set()                          # turns carrying a suppression (to keep BDA clear of them)

    for target, sources in by_target.items():
        # pick create turns for this target's edges, >=4 apart, off noise turns, windows within n
        create_turns = []
        cur_idx = 0
        for _ in sources:
            # advance to an allowed turn whose window [t,t+3] does not overlap the previous
            while cur_idx < len(allowed):
                ct = allowed[cur_idx]
                cur_idx += 1
                if create_turns and ct - create_turns[-1] < 4:
                    continue
                create_turns.append(ct)
                break
        for j, (s, ct) in enumerate(zip(sources, create_turns)):
            edges.append({
                "source_id": node_id[s], "target_id": node_id[target],
                "source_core_id": s, "target_core_id": target,
                "relation": "contradicts", "created_at_turn": ct,
                "evidence_turn": ct, "text_hash": th(ct),
            })
            used_turns_for_target[target].append(ct)
            # suppression deltas inside [ct, ct+3], off noise turns, escalating
            if j == 0:
                deltas = [(-0.2, ct)]
            elif j == 1:
                deltas = [(-0.35, ct)]
            else:
                # need energy > baseline_avg*1.5 which exceeds a single 0.4; use two
                second = next((x for x in range(ct + 1, ct + 4) if x not in noise and x <= n), ct)
                deltas = [(-0.4, ct), (-0.4, second)]
            for d, turn in deltas:
                transitions.append({"node_id": node_id[target], "core_id": target,
                                    "turn": turn, "delta": d, "trigger_text_hash": th(turn)})
                supp_turns.add(turn)

    # concepts already moved DOWN by suppression (satisfies a "down" belief change)
    suppressed = set(by_target.keys())

    # window bounds per target concept, so BDA moves can be placed AFTER them (or,
    # when a target's windows fill the timeline, inside its last dominant window)
    last_win_end, last_create = {}, {}
    for e in edges:
        t, ct = e["target_core_id"], e["created_at_turn"]
        last_win_end[t] = max(last_win_end.get(t, 0), ct + 3)
        last_create[t] = max(last_create.get(t, 0), ct)

    used_bda = defaultdict(set)  # per concept: turns already taken for its BDA moves

    def pick_turns(cid, count):
        after = [t for t in allowed if t > last_win_end.get(cid, 0) and t not in used_bda[cid]]
        if len(after) >= count:
            chosen = after[:count]
        else:  # tight target: fall back into its last (escalated, net-dominant) window
            inwin = [t for t in allowed if last_create.get(cid, 0) <= t <= n and t not in used_bda[cid]]
            pool = sorted(set(after) | set(inwin))
            chosen = pool[-count:] if len(pool) >= count else pool
        for t in chosen:
            used_bda[cid].add(t)
        return chosen

    def add_trans(cid, turn, delta):
        transitions.append({"node_id": node_id[cid], "core_id": cid, "turn": turn,
                            "delta": delta, "trigger_text_hash": th(turn)})

    for bc in belief_changes:
        cid, direction = bc["core_id"], bc["direction"]
        if direction == "down" and cid in suppressed:
            continue  # suppression already provides a down move > 0.05
        if direction == "down":
            for t in pick_turns(cid, 1):
                add_trans(cid, t, -0.2)
        elif direction == "up":
            for t in pick_turns(cid, 1):
                add_trans(cid, t, 0.2)
        elif direction == "up_then_down":
            ts = pick_turns(cid, 2)
            if len(ts) == 2:
                add_trans(cid, ts[0], 0.3)
                add_trans(cid, ts[1], -0.3)

    # --- anti-zombie: any mapped node with no edge and no meaningful transition ---
    have_edge = set()
    for e in edges:
        have_edge.add(e["source_id"]); have_edge.add(e["target_id"])
    have_trans = {t["node_id"] for t in transitions if abs(t["delta"]) > 0.01}
    for c in sorted(concepts):
        nid = node_id[c]
        if nid not in have_edge and nid not in have_trans:
            t = pick_turns(c, 1)
            turn = t[0] if t else allowed[0]
            add_trans(c, turn, 0.06)
    return nodes, edges, transitions


def score_oracle(scenario):
    nodes, edges, transitions = build_oracle(scenario)
    raw_state = {"_execution_nonce": NONCE}
    res = evaluate(nodes, edges, transitions, scenario["messages"],
                   scenario["ground_truth"], NONCE,
                   raw_state=raw_state, raw_hash=_h_dict(raw_state))
    return res


def run(out_path):
    results = {}
    for f in sorted(SCEN_DIR.glob("*.json")):
        scenario = _load_json(f)
        res = score_oracle(scenario)
        results[scenario["id"]] = {
            "status": res.get("status"),
            "ban_reason": res.get("ban_reason"),
            "scores": res.get("scores"),
        }
    Path(out_path).write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


def main():
    ap = argparse.ArgumentParser(description="Oracle probe (offline).")
    ap.add_argument("--out", type=str, default=str(ROOT / "docs" / "probes" / "oracle.json"))
    args = ap.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    results = run(args.out)
    print(f"{'scenario':32} {'status':10} {'CER':>6} {'GCS':>6} {'BDA':>6} {'ISS':>6} {'NRS':>6}")
    allmax = True
    for sid, r in results.items():
        sc = r["scores"] or {}
        def f(m):
            v = sc.get(m)
            return f"{v:.2f}" if isinstance(v, (int, float)) else str(v)
        print(f"{sid:32} {str(r['status']):10} {f('CER'):>6} {f('GCS'):>6} {f('BDA'):>6} {f('ISS'):>6} {f('NRS'):>6}")
        if r["status"] != "VALIDATED":
            allmax = False
            print(f"    -> {r['ban_reason']}")
        else:
            for m in ("CER", "GCS", "BDA", "ISS"):
                if sc.get(m) != 1.0:
                    allmax = False
    print(f"\nwrote {args.out}")
    print("ALL 7 reach 1.0 on CER/GCS/BDA/ISS:" , allmax)


if __name__ == "__main__":
    main()
