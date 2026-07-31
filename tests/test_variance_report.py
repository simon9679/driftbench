"""Offline tests for the baseline variance report: range math, undefined (—) and
parse-failure (fail) handling."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from baselines.variance_report import (  # noqa: E402
    summarize,
    per_run_benchmark_means,
    build_markdown,
    FAIL,
)


def test_range_is_max_minus_min():
    st = summarize([0.20, 0.50, 0.30])
    assert st["kind"] == "ok"
    assert st["min"] == 0.20 and st["max"] == 0.50
    assert abs(st["range"] - 0.30) < 1e-9
    assert abs(st["mean"] - (1.0 / 3)) < 1e-9
    assert st["n_ok"] == 3 and st["n_total"] == 3


def test_zero_range_when_all_equal():
    st = summarize([0.4, 0.4, 0.4])
    assert st["kind"] == "ok"
    assert st["range"] == 0.0
    assert abs(st["mean"] - 0.4) < 1e-9


def test_undefined_values_skipped_not_break():
    st = summarize([0.4, None, 0.6])
    assert st["kind"] == "ok"
    assert st["n_ok"] == 2 and st["n_total"] == 3
    assert st["min"] == 0.4 and st["max"] == 0.6
    assert abs(st["range"] - 0.20) < 1e-9


def test_all_undefined_returns_undef():
    assert summarize([None, None])["kind"] == "undef"
    assert summarize([])["kind"] == "undef"


# ─── parse-failure handling ──────────────────────────────────────────────────

def test_parse_failure_excluded_from_stats_and_counted():
    st = summarize([0.5, FAIL, 0.7])
    assert st["kind"] == "ok"
    assert st["n_ok"] == 2          # the fail run is not counted
    assert st["n_fail"] == 1
    assert st["n_total"] == 3
    assert abs(st["range"] - 0.20) < 1e-9


def test_run_count_shown_when_fewer_than_total():
    # 2 good of 3 → summary cell must expose the "(2/3 runs)" count.
    from baselines.variance_report import _summary_cell
    cell = _summary_cell(summarize([0.5, FAIL, 0.7]))
    assert "(2/3 runs)" in cell


def test_fewer_than_two_good_runs_does_not_break():
    # one good run + fails: range not computed, no crash.
    st = summarize([FAIL, 0.5, FAIL])
    assert st["kind"] == "insufficient"
    assert st["n_ok"] == 1
    from baselines.variance_report import _summary_cell
    assert "range needs ≥2" in _summary_cell(st)


def test_all_failed_reports_no_data_not_crash():
    st = summarize([FAIL, FAIL])
    assert st["kind"] == "insufficient"
    assert st["n_ok"] == 0 and st["n_fail"] == 2
    from baselines.variance_report import _summary_cell
    assert "no data" in _summary_cell(st)


def test_benchmark_means_skip_failed_and_undefined():
    scenarios = {
        "s1": {"M": [0.2, 0.4, 0.6]},
        "s2": {"M": [0.8, FAIL, None]},
    }
    means = per_run_benchmark_means(scenarios, "M", 3)
    assert abs(means[0] - 0.5) < 1e-9      # (0.2 + 0.8) / 2
    assert abs(means[1] - 0.4) < 1e-9      # s2 failed → only s1
    assert abs(means[2] - 0.6) < 1e-9      # s2 undefined → only s1


def test_build_markdown_renders_fail_range_and_legend():
    models = {
        "demo": {
            "n_runs": 3,
            "scenarios": {"s1": {m: ([0.2, FAIL, 0.6] if m == "CER" else [None, None, None])
                                  for m in ["CER", "GCS", "BDA", "ISS", "NRS"]}},
        }
    }
    md = build_markdown(models)
    assert "fail" in md                                  # failure marker rendered
    assert "0.4000 (0.20–0.60, Δ0.40) (2/3 runs)" in md  # range + count inline
    assert "Legend:" in md and "did not parse" in md     # legend distinguishes — / fail
