#!/usr/bin/env python3
"""
Baseline variance report
========================
Aggregate N repeated baseline runs of the *same* model into a spread table.

Runs entirely OFFLINE on committed results — no API keys, no network. It reads
per-scenario JSONs written by ``run_baselines.py`` and laid out as::

    baselines/variance/<model>/run1/<scenario>.json
    baselines/variance/<model>/run2/<scenario>.json
    ...

For every metric on every scenario it reports: each run's value, the min, the
max, the range (max − min) and the mean. The range sits **next to** the number
(e.g. ``0.2585 (0.19–0.33, Δ0.14)``) because a single number without a spread is
not a measurement. Metrics that are undefined for a scenario (``—``) are shown as
such and excluded from the arithmetic without breaking it.

Usage::

    python baselines/variance_report.py            # prints markdown to stdout
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARIANCE_DIR = ROOT / "baselines" / "variance"
METRICS = ["CER", "GCS", "BDA", "ISS", "NRS"]


# ─── Pure helpers (unit-tested) ──────────────────────────────────────────────

def summarize(values):
    """Summary of a list of per-run values (floats and/or None).

    Returns None if no value is defined; otherwise a dict with mean/min/max/range
    computed over the defined (numeric) values only. Undefined entries never break
    the arithmetic — they are simply skipped.
    """
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    lo, hi = min(nums), max(nums)
    return {"mean": sum(nums) / len(nums), "min": lo, "max": hi,
            "range": hi - lo, "n": len(nums)}


def per_run_benchmark_means(scenarios, metric, n_runs):
    """For a single metric, one whole-benchmark mean per run.

    ``scenarios`` maps scenario_id → {metric: [v_run0, v_run1, ...]}. For each run
    index we average that metric over the scenarios where it is defined; a run with
    no defined value for the metric contributes None.
    """
    out = []
    for ri in range(n_runs):
        vals = [scenarios[s][metric][ri] for s in scenarios
                if isinstance(scenarios[s][metric][ri], (int, float))]
        out.append(sum(vals) / len(vals) if vals else None)
    return out


# ─── Loading ─────────────────────────────────────────────────────────────────

def load_runs(variance_dir=VARIANCE_DIR):
    """Return {model: {"n_runs": int, "scenarios": {sid: {metric: [v_per_run]}}}}."""
    models = {}
    for model_dir in sorted(p for p in Path(variance_dir).glob("*") if p.is_dir()):
        run_dirs = sorted(p for p in model_dir.glob("run*") if p.is_dir())
        if not run_dirs:
            continue
        scenarios = {}
        for ri, rd in enumerate(run_dirs):
            for jf in sorted(rd.glob("*.json")):
                rec = json.loads(jf.read_text("utf-8"))
                sid = rec.get("scenario_id", jf.stem)
                scores = rec.get("scores", {})
                d = scenarios.setdefault(
                    sid, {m: [None] * len(run_dirs) for m in METRICS})
                for m in METRICS:
                    v = scores.get(m)
                    d[m][ri] = v if isinstance(v, (int, float)) else None
        models[model_dir.name] = {"n_runs": len(run_dirs), "scenarios": scenarios}
    return models


# ─── Formatting ──────────────────────────────────────────────────────────────

def _num(v):
    return f"{v:.4f}" if isinstance(v, (int, float)) else "—"


def _summary_cell(st):
    if st is None:
        return "—"
    return f"{st['mean']:.4f} ({st['min']:.2f}–{st['max']:.2f}, Δ{st['range']:.2f})"


def build_markdown(models):
    """Render the whole variance report as markdown."""
    if not models:
        return "_No variance runs found under `baselines/variance/`._\n"

    out = []
    for model, info in models.items():
        n = info["n_runs"]
        scen = info["scenarios"]
        sids = sorted(scen)
        run_cols = " | ".join(f"run{i+1}" for i in range(n))

        out.append(f"### `{model}` — {n} runs, same model, nothing changed between runs\n")
        for m in METRICS:
            out.append(f"**{m}**\n")
            out.append(f"| Scenario | {run_cols} | mean (min–max, Δrange) |")
            out.append("|" + "---|" * (n + 2))
            for sid in sids:
                vals = scen[sid][m]
                cells = " | ".join(_num(v) for v in vals)
                out.append(f"| {sid} | {cells} | {_summary_cell(summarize(vals))} |")
            bench = per_run_benchmark_means(scen, m, n)
            bench_cells = " | ".join(_num(v) for v in bench)
            out.append(
                f"| **benchmark mean** | {bench_cells} | "
                f"{_summary_cell(summarize(bench))} |")
            out.append("")
    return "\n".join(out) + "\n"


def max_cell_range(models):
    """Largest single (scenario, metric) range observed across all models."""
    widest = None
    for info in models.values():
        for scen in info["scenarios"].values():
            for vals in scen.values():
                st = summarize(vals)
                if st and (widest is None or st["range"] > widest):
                    widest = st["range"]
    return widest


def build_section():
    """Markdown section for inclusion in BASELINES.md."""
    models = load_runs()
    body = build_markdown(models)
    widest = max_cell_range(models)
    n_runs = next((info["n_runs"] for info in models.values()), 0) if models else 0
    swing = (f"The widest single (scenario, metric) swing here was "
             f"**Δ{widest:.2f}**. " if widest is not None else "")
    conclusion = (
        "**What to take from this.** Numbers that read as clean in a one-shot table "
        f"move on repeat — some cells not at all, others by a large margin (the Δrange "
        f"column). {swing}A single run of a single model on a single scenario is not a "
        "measurement; do not rank systems on one run. And "
        f"{n_runs} runs of one model on seven scenarios is itself a small sample — it "
        "says nothing beyond this exact configuration, and a small spread here is not "
        "proof of reliability.\n")
    return (
        "## Repeated-run variance (same model, same scenarios)\n\n"
        f"{n_runs} runs of one model on the same seven scenarios, `temperature=0`, "
        "**nothing changed between runs**. The spread below is what the same "
        "configuration produced on repeat. The range sits next to each number on "
        "purpose — a single run is not a measurement.\n\n"
        + body + "\n" + conclusion)


def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(build_section())


if __name__ == "__main__":
    main()
