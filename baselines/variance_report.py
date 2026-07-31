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

For every metric on every scenario it reports each run's value, the min, the max,
the range (max − min) and the mean, with the range **next to** the number (e.g.
``0.2778 (0.25–0.33, Δ0.08)``).

Two kinds of empty cell are kept distinct:
  * ``—``    the metric is undefined for that scenario on a run that answered;
  * ``fail`` the run's JSON did not parse (``note`` contains ``parse_error``) and
             its state came out empty. Such runs are **excluded** from min / max /
             range / mean — a non-answer is not a low score. When a summary is
             computed on fewer than all runs, the count is shown, e.g. ``(2/3
             runs)``; with fewer than two good runs the range is not computed.

Usage::

    python baselines/variance_report.py            # prints markdown to stdout
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VARIANCE_DIR = ROOT / "baselines" / "variance"
METRICS = ["CER", "GCS", "BDA", "ISS", "NRS"]

FAIL = "fail"  # sentinel: a run whose JSON failed to parse


# ─── Pure helpers (unit-tested) ──────────────────────────────────────────────

def summarize(entries):
    """Summarize per-run entries. Each entry is a float, ``None`` (metric
    undefined on a run that answered), or ``FAIL`` (run did not parse).

    ``FAIL`` and ``None`` never enter the arithmetic. Returns a dict:

      {"kind": "undef"}                              # nothing to report
      {"kind": "insufficient", "n_ok", "n_total", "n_fail", "only"}
      {"kind": "ok", "mean","min","max","range","n_ok","n_total","n_fail"}
    """
    n_total = len(entries)
    n_fail = sum(1 for e in entries if e == FAIL)
    nums = [e for e in entries if isinstance(e, (int, float))]
    n_ok = len(nums)

    if n_ok == 0:
        if n_fail == 0:
            return {"kind": "undef"}
        return {"kind": "insufficient", "n_ok": 0, "n_total": n_total,
                "n_fail": n_fail, "only": None}
    if n_ok < 2:
        return {"kind": "insufficient", "n_ok": n_ok, "n_total": n_total,
                "n_fail": n_fail, "only": nums[0]}
    lo, hi = min(nums), max(nums)
    return {"kind": "ok", "mean": sum(nums) / n_ok, "min": lo, "max": hi,
            "range": hi - lo, "n_ok": n_ok, "n_total": n_total, "n_fail": n_fail}


def per_run_benchmark_means(scenarios, metric, n_runs):
    """One whole-benchmark mean per run for a metric, over scenarios whose value
    is numeric on that run (``FAIL`` and undefined scenarios are skipped)."""
    out = []
    for ri in range(n_runs):
        vals = [scenarios[s][metric][ri] for s in scenarios
                if isinstance(scenarios[s][metric][ri], (int, float))]
        out.append(sum(vals) / len(vals) if vals else None)
    return out


def metric_max_range(models, metric):
    """Largest range for a metric across scenarios where it is computable (≥2
    good runs). Returns None if never computable."""
    widest = None
    for info in models.values():
        for scen in info["scenarios"].values():
            st = summarize(scen[metric])
            if st["kind"] == "ok" and (widest is None or st["range"] > widest):
                widest = st["range"]
    return widest


def count_parse_failures(models):
    """(#failed run-cells, #total run-cells) across all models/scenarios."""
    failed = total = 0
    for info in models.values():
        for scen in info["scenarios"].values():
            # any metric marked FAIL means the whole run-cell failed; count once.
            for ri in range(info["n_runs"]):
                total += 1
                if scen[METRICS[0]][ri] == FAIL:
                    failed += 1
    return failed, total


# ─── Loading ─────────────────────────────────────────────────────────────────

def load_runs(variance_dir=VARIANCE_DIR):
    """Return {model: {"n_runs": int, "scenarios": {sid: {metric: [entry]}}}}.

    entry ∈ float | None (undefined) | FAIL (run did not parse).
    """
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
                d = scenarios.setdefault(
                    sid, {m: [None] * len(run_dirs) for m in METRICS})
                failed = "parse_error" in (rec.get("note") or "")
                scores = rec.get("scores", {})
                for m in METRICS:
                    if failed:
                        d[m][ri] = FAIL
                    else:
                        v = scores.get(m)
                        d[m][ri] = v if isinstance(v, (int, float)) else None
        models[model_dir.name] = {"n_runs": len(run_dirs), "scenarios": scenarios}
    return models


# ─── Formatting ──────────────────────────────────────────────────────────────

def _cell(entry):
    if entry == FAIL:
        return "fail"
    if isinstance(entry, (int, float)):
        return f"{entry:.4f}"
    return "—"


def _summary_cell(st):
    kind = st["kind"]
    if kind == "undef":
        return "—"
    if kind == "insufficient":
        if st["n_ok"] == 0:
            return f"— ({st['n_fail']}/{st['n_total']} failed, no data)"
        return (f"{st['only']:.4f} "
                f"(1/{st['n_total']} runs — range needs ≥2 good runs)")
    tail = f" ({st['n_ok']}/{st['n_total']} runs)" if st["n_ok"] < st["n_total"] else ""
    return f"{st['mean']:.4f} ({st['min']:.2f}–{st['max']:.2f}, Δ{st['range']:.2f}){tail}"


def build_markdown(models):
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
                cells = " | ".join(_cell(e) for e in scen[sid][m])
                out.append(f"| {sid} | {cells} | {_summary_cell(summarize(scen[sid][m]))} |")
            bench = per_run_benchmark_means(scen, m, n)
            bench_cells = " | ".join(_cell(e) for e in bench)
            out.append(f"| **benchmark mean** | {bench_cells} | "
                       f"{_summary_cell(summarize(bench))} |")
            out.append("")
    out.append("_Legend: `—` = metric undefined for that scenario · `fail` = the run's "
               "JSON did not parse (empty state); `fail` runs are excluded from "
               "min / max / range / mean._\n")
    return "\n".join(out) + "\n"


def _fmt_max(metric, models):
    r = metric_max_range(models, metric)
    return f"{metric} up to **Δ{r:.2f}**" if r is not None else f"{metric} not computable"


def build_section():
    """The full 'Repeated-run variance' + metric-defect markdown for BASELINES.md."""
    models = load_runs()
    if not models:
        return "## Repeated-run variance\n\n_No variance runs committed yet._\n"

    n_runs = next(iter(models.values()))["n_runs"]
    n_fail, n_total = count_parse_failures(models)
    maxima = " · ".join(_fmt_max(m, models) for m in ("CER", "GCS", "BDA", "ISS"))

    variance = (
        "## Repeated-run variance (same model, same scenarios)\n\n"
        f"{n_runs} runs of one model on the same seven scenarios, `temperature=0`, "
        "**nothing changed between runs**. The spread below is what the same "
        "configuration produced on repeat. The range sits next to each number on "
        "purpose — a single run is not a measurement.\n\n"
        + build_markdown(models))

    conclusion = (
        "### What the spread shows\n\n"
        "On the runs that answered, metrics diverge noticeably between identical "
        f"repeats: {maxima}.\n\n"
        f"Separately, **{n_fail} of {n_total} runs did not parse** (empty state) and "
        "are marked `fail`; they are excluded from the variance figures above. Both "
        "parse failures fell on the same scenario (`11_noise_resistance`), but three "
        "runs are too few to conclude why, and no cause is claimed here.\n\n"
        "The takeaway is unchanged and is not softened: a single run of a single "
        "model on a single scenario is not a measurement — systems must not be "
        "ranked on one run.\n")

    defect = (
        "## Metric defect (v1.1 candidate): empty state scores NRS = 1.00\n\n"
        f"On repeated runs, {n_fail} of {n_total} scored responses failed to parse "
        "and produced an empty belief graph (`{\"nodes\": [], \"edges\": [], "
        "\"transitions\": []}`). The benchmark assigned that empty state "
        "**NRS = 1.00 — the maximum** noise-resistance score. On the run that "
        "answered, the same scenario scored NRS = 0.00.\n\n"
        "This is a defect in the metric's semantics, not a scoring bug: a system "
        "that emits nothing is credited with perfect resistance to noise. The logic "
        "is understandable (no beliefs, nothing to shift) but the result is absurd "
        "and easy to exploit — a silent adapter earns top marks.\n\n"
        "**The v1 specification is frozen, so v1 behaviour does not change.** The "
        "defect is recorded and carried to v1.1 as a fix candidate. Proposed "
        "direction (named, not implemented here): an empty or invalid state should "
        "yield an *undefined* result, not a maximum score.\n\n"
        "**This defect was found by repeated runs and could not have been found any "
        "other way.** A single run gave NRS = 0.00 on scenario 11 and raised no "
        "questions — the same input scored the opposite once its parse failed on "
        "repeat. That is the direct point of running more than once.\n")

    return variance + "\n" + conclusion + "\n" + defect


def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(build_section())


if __name__ == "__main__":
    main()
