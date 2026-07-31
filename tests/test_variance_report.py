"""Offline tests for the baseline variance report: range math + undefined handling."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from baselines.variance_report import (  # noqa: E402
    summarize,
    per_run_benchmark_means,
    build_markdown,
)


def test_range_is_max_minus_min():
    st = summarize([0.20, 0.50, 0.30])
    assert st["min"] == 0.20
    assert st["max"] == 0.50
    assert abs(st["range"] - 0.30) < 1e-9
    assert abs(st["mean"] - (1.0 / 3)) < 1e-9
    assert st["n"] == 3


def test_zero_range_when_all_equal():
    st = summarize([0.4, 0.4, 0.4])
    assert st["range"] == 0.0
    assert abs(st["mean"] - 0.4) < 1e-9


def test_undefined_values_skipped_not_break():
    # None entries must be ignored, not counted, not crash.
    st = summarize([0.4, None, 0.6])
    assert st["n"] == 2
    assert st["min"] == 0.4
    assert st["max"] == 0.6
    assert abs(st["range"] - 0.20) < 1e-9


def test_all_undefined_returns_none():
    assert summarize([None, None]) is None
    assert summarize([]) is None


def test_benchmark_means_per_run_and_none_handling():
    # Two scenarios, three runs. Metric M defined except one run of s2.
    scenarios = {
        "s1": {"M": [0.2, 0.4, 0.6]},
        "s2": {"M": [0.8, None, 0.0]},
    }
    means = per_run_benchmark_means(scenarios, "M", 3)
    assert abs(means[0] - 0.5) < 1e-9      # (0.2 + 0.8) / 2
    assert abs(means[1] - 0.4) < 1e-9      # only s1 defined this run
    assert abs(means[2] - 0.3) < 1e-9      # (0.6 + 0.0) / 2


def test_benchmark_mean_none_when_metric_all_undefined_in_run():
    scenarios = {"s1": {"M": [None, 0.5]}}
    means = per_run_benchmark_means(scenarios, "M", 2)
    assert means[0] is None
    assert abs(means[1] - 0.5) < 1e-9


def test_build_markdown_renders_range_next_to_number():
    models = {
        "demo": {
            "n_runs": 2,
            "scenarios": {"s1": {m: ([0.2, 0.6] if m == "CER" else [None, None])
                                  for m in ["CER", "GCS", "BDA", "ISS", "NRS"]}},
        }
    }
    md = build_markdown(models)
    # Range appears inline with the value, and dashes render for undefined metrics.
    assert "Δ0.40" in md
    assert "0.4000 (0.20–0.60, Δ0.40)" in md
    assert "—" in md
