"""
Generate a minimal DriftBench submission from a scenario file.

Usage:
    python examples/generate_submission.py examples/scenario_minimal.json

Then validate:
    driftbench-validate --sub submission.json --scen examples/scenario_minimal.json --nonce local_test
"""
import json
import hashlib
import sys
from pathlib import Path

from driftbench_core.core import hash_turn


def _h_dict(data: dict) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def generate_submission(scenario_path: Path, nonce: str = "local_test") -> dict:
    scenario = json.loads(scenario_path.read_text("utf-8-sig"))
    messages = scenario["messages"]

    # Precompute turn hashes
    turn_hashes = {}
    for m in messages:
        t = m["turn"]
        turn_hashes[t] = hash_turn(t, m["user"], m["assistant"])

    raw_engine_log = {
        "engine": "fake_engine",
        "status": "success",
        "_execution_nonce": nonce,
    }

    conv = {
        "nodes": [
            {
                "id": "n1",
                "label": "Wants to be founder",
                "core_id": "ID_FOUNDER",
                "mapping_confidence": 0.9,
                "confidence": 0.9,
                "evidence_turn": 2,
                "text_hash": turn_hashes[2],
            },
            {
                "id": "n2",
                "label": "Hates job",
                "core_id": "ID_EMPLOYEE",
                "mapping_confidence": 0.9,
                "confidence": 0.1,
                "evidence_turn": 1,
                "text_hash": turn_hashes[1],
            },
        ],
        "edges": [
            {
                "source_id": "n2",
                "target_id": "n1",
                "source_core_id": "ID_EMPLOYEE",
                "target_core_id": "ID_FOUNDER",
                "relation": "blocks",
                "created_at_turn": 2,
                "evidence_turn": 2,
                "text_hash": turn_hashes[2],
            }
        ],
        "transitions": [
            {"node_id": "n2", "core_id": "ID_EMPLOYEE", "turn": 2, "delta": -0.2, "trigger_text_hash": turn_hashes[2]},
            {"node_id": "n1", "core_id": "ID_FOUNDER", "turn": 2, "delta": -0.1, "trigger_text_hash": turn_hashes[2]},
            {"node_id": "n1", "core_id": "ID_FOUNDER", "turn": 6, "delta": 0.4, "trigger_text_hash": turn_hashes[6]},
        ],
    }

    return {
        "raw": raw_engine_log,
        "raw_h": _h_dict(raw_engine_log),
        "conv": conv,
        "conv_h": _h_dict(conv),
    }


if __name__ == "__main__":
    scenario_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/scenario_minimal.json")
    submission = generate_submission(scenario_path)
    out_path = Path("submission.json")
    out_path.write_text(json.dumps(submission, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Submission written to {out_path}")
