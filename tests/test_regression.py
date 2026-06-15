"""Regression: submission_minimal.json + scenario_minimal.json -> VALIDATED, scores unchanged."""
import json
from pathlib import Path
from driftbench_core.core import evaluate, _h_dict

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_minimal_submission_validated():
    sub = json.loads((EXAMPLES / "submission_minimal.json").read_text("utf-8-sig"))
    scen = json.loads((EXAMPLES / "scenario_minimal.json").read_text("utf-8-sig"))

    assert _h_dict(sub["raw"]) == sub["raw_h"], "raw_h mismatch"
    assert _h_dict(sub["conv"]) == sub["conv_h"], "conv_h mismatch"

    result = evaluate(
        nodes=sub["conv"]["nodes"],
        edges=sub["conv"]["edges"],
        transitions=sub["conv"]["transitions"],
        messages=scen["messages"],
        gt=scen["ground_truth"],
        nonce="local_test",
        raw_state=sub["raw"],
        raw_hash=sub["raw_h"],
        conv_hash=sub["conv_h"],
    )

    assert result["status"] == "VALIDATED", f"Got: {result}"
    assert result["scores"]["CER"] == 1.0
    assert result["scores"]["BDA"] == 1.0
    assert result["scores"]["ISS"] == 1.0
    assert result["scores"]["NRS"] is None