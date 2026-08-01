#!/usr/bin/env python3
"""
Label-invariance probe
=======================
A metric that measures *semantic correctness* must break when the semantic labels
are scrambled. This probe takes the real belief states committed under
``baselines/variance/gpt-oss-120b/{run1,run2,run3}/``, applies a **consistent**
random permutation of the eight ontology ``core_id`` values across every node,
edge and transition (structure preserved, meaning destroyed), rescores the five
metrics with the canonical scorer and compares to the originals.

A metric that never changes under permutation is not measuring semantics. A
metric whose score sometimes **goes up** under permutation can be optimised in the
wrong direction — a stronger warning still.

Fully offline: no keys, no network, and the repository is not modified. Reuses the
canonical ``score_state`` so the metric math is never re-implemented here.

Usage::

    python dev-scripts/probes/label_invariance_probe.py --seeds 50 --out out.json
"""

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VARIANCE_DIR = ROOT / "baselines" / "variance" / "gpt-oss-120b"
SCEN_DIR = ROOT / "standard" / "v1" / "scenarios"
ONTOLOGY = ROOT / "standard" / "v1" / "ontology.json"
METRICS = ["CER", "GCS", "BDA", "ISS", "NRS"]

sys.path.insert(0, str(ROOT))
from run_baselines import score_state  # noqa: E402  (canonical scoring, reused)


def _load_json(path):
    return json.loads(Path(path).read_text("utf-8-sig"))


def load_ground_truths():
    out = {}
    for f in SCEN_DIR.glob("*.json"):
        sc = _load_json(f)
        out[sc["id"]] = sc.get("ground_truth", {})
    return out


def load_states():
    """Return ([(label, scenario_id, state)], skipped_parse_error)."""
    states, skipped = [], 0
    for run_dir in sorted(p for p in VARIANCE_DIR.glob("run*") if p.is_dir()):
        for jf in sorted(run_dir.glob("*.json")):
            rec = _load_json(jf)
            if "parse_error" in (rec.get("note") or ""):
                skipped += 1
                continue
            states.append((f"{run_dir.name}/{jf.stem}",
                           rec.get("scenario_id", jf.stem),
                           rec.get("state", {})))
    return states, skipped


def permute_state(state, perm):
    """Apply the core_id map ``perm`` consistently to nodes, edges, transitions."""
    def rid(v):
        return perm.get(v, v)
    nodes = [{**n, "core_id": rid(n.get("core_id"))} for n in state.get("nodes", [])]
    edges = [{**e,
              "source_core_id": rid(e.get("source_core_id")),
              "target_core_id": rid(e.get("target_core_id"))}
             for e in state.get("edges", [])]
    trans = [{**t, "core_id": rid(t.get("core_id"))} for t in state.get("transitions", [])]
    return {"nodes": nodes, "edges": edges, "transitions": trans}


def run(seeds, out_path):
    core_ids = sorted(_load_json(ONTOLOGY)["concepts"].keys())
    gts = load_ground_truths()
    states, skipped = load_states()

    before_vals = {m: [] for m in METRICS}
    after_vals = {m: [] for m in METRICS}
    unchanged = {m: 0 for m in METRICS}
    improved = {m: 0 for m in METRICS}
    total = {m: 0 for m in METRICS}
    examples = {m: [] for m in METRICS}

    n_perms = 0
    for seed in range(seeds):
        shuffled = core_ids[:]
        random.Random(seed).shuffle(shuffled)
        perm = dict(zip(core_ids, shuffled))
        for label, sid, state in states:
            gt = gts.get(sid, {})
            before = score_state(state, gt)
            after = score_state(permute_state(state, perm), gt)
            n_perms += 1
            for m in METRICS:
                b, a = before.get(m), after.get(m)
                total[m] += 1
                if b == a:                       # None == None counts as unchanged
                    unchanged[m] += 1
                if isinstance(b, (int, float)):
                    before_vals[m].append(b)
                if isinstance(a, (int, float)):
                    after_vals[m].append(a)
                if isinstance(b, (int, float)) and isinstance(a, (int, float)) and a > b:
                    improved[m] += 1
                    if len(examples[m]) < 5:
                        examples[m].append({"state": label, "seed": seed,
                                            "before": round(b, 4), "after": round(a, 4)})

    def mean(xs):
        return round(sum(xs) / len(xs), 4) if xs else None

    result = {
        "config": {
            "seeds": seeds,
            "states_used": len(states),
            "states_skipped_parse_error": skipped,
            "permutations": n_perms,
            "source": "baselines/variance/gpt-oss-120b/{run1,run2,run3}",
        },
        "metrics": {
            m: {
                "mean_before": mean(before_vals[m]),
                "mean_after": mean(after_vals[m]),
                "pct_unchanged": round(100 * unchanged[m] / total[m], 1) if total[m] else None,
                "pct_improved_pathological": round(100 * improved[m] / total[m], 1) if total[m] else None,
                "n_defined_before": len(before_vals[m]),
                "examples_improved": examples[m],
            }
            for m in METRICS
        },
    }
    Path(out_path).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    ap = argparse.ArgumentParser(description="Label-invariance probe (offline).")
    ap.add_argument("--seeds", type=int, default=500,
                    help="Monte-Carlo permutation count. 50 is too few (unstable "
                         "rates); 500 is the published default.")
    ap.add_argument("--out", type=str,
                    default=str(ROOT / "docs" / "probes" / "label_invariance.json"))
    args = ap.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    res = run(args.seeds, args.out)
    c = res["config"]
    print(f"states_used={c['states_used']} skipped_parse_error={c['states_skipped_parse_error']} "
          f"permutations={c['permutations']}")
    print(f"{'metric':6} {'mean_before':>12} {'mean_after':>11} {'%unchanged':>11} {'%improved':>10}")
    for m in METRICS:
        d = res["metrics"][m]
        print(f"{m:6} {str(d['mean_before']):>12} {str(d['mean_after']):>11} "
              f"{str(d['pct_unchanged']):>11} {str(d['pct_improved_pathological']):>10}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
