import argparse
import json
import sys
from pathlib import Path
from .core import evaluate, _h_dict


def _reject(reason_code: str, message: str) -> dict:
    return {
        "spec": "1.0.0",
        "status": "REJECTED",
        "reason_code": reason_code,
        "ban_reason": message,
        "scores": {"CER": 0.0, "GCS": 0.0, "BDA": 0.0, "ISS": 0.0, "NRS": 0.0, "PENALTY": reason_code},
        "hash": "sha256:0000",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sub", required=True, type=Path)
    p.add_argument("--scen", required=True, type=Path)
    p.add_argument("--nonce", required=True, type=str)
    args = p.parse_args()

    # --- Load and validate JSON structure ---
    try:
        sub = json.loads(args.sub.read_text('utf-8-sig'))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        result = _reject("MALFORMED_SUBMISSION", f"Cannot parse submission JSON: {exc}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    try:
        scen = json.loads(args.scen.read_text('utf-8-sig'))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        result = _reject("MALFORMED_SCENARIO", f"Cannot parse scenario JSON: {exc}")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    # --- Structural validation ---
    for key in ("raw", "raw_h", "conv", "conv_h"):
        if key not in sub:
            result = _reject("MISSING_FIELD", f"Submission missing required field: {key}")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(1)

    for key in ("nodes", "edges", "transitions"):
        if key not in sub["conv"]:
            result = _reject("MISSING_FIELD", f"Submission conv missing required field: {key}")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(1)
        if not isinstance(sub["conv"][key], list):
            result = _reject("INVALID_STRUCTURE", f"Submission conv.{key} must be a list")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(1)

    if "messages" not in scen or "ground_truth" not in scen:
        result = _reject("MISSING_FIELD", "Scenario missing required field: messages or ground_truth")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    # --- Hash integrity (using single source of truth from core) ---
    if _h_dict(sub["raw"]) != sub["raw_h"]:
        result = _reject("RAW_TAMPERED", "Raw hash does not match raw_h")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)
    if _h_dict(sub["conv"]) != sub["conv_h"]:
        result = _reject("CONV_TAMPERED", "Converted hash does not match conv_h")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    # --- Evaluate ---
    result = evaluate(
        nodes=sub["conv"]["nodes"],
        edges=sub["conv"]["edges"],
        transitions=sub["conv"]["transitions"],
        messages=scen["messages"],
        gt=scen["ground_truth"],
        nonce=args.nonce,
        raw_state=sub["raw"],
        raw_hash=sub["raw_h"],
        conv_hash=sub["conv_h"],
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] == "REJECTED":
        sys.exit(1)


if __name__ == "__main__":
    main()
