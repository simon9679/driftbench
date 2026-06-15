"""
Test suite for driftbench_core.

Run:
    py -3 -m pytest tests/test_core.py -v

Layout:
    A. hash functions          (5 tests)
    B. integrity validator    (10 tests)
    C. metrics                (10 tests)
    D. evaluate() end-to-end   (3 tests)
    E. hash stability          (2 tests)

Total: 30 tests.
"""
import json
from pathlib import Path

import pytest

from driftbench_core import evaluate, hash_turn, compute_nrs
from driftbench_core.core import (
    _h_dict,
    compute_bda,
    compute_cer,
    compute_gcs,
    compute_iss,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

MSGS = [
    {"user": "u1", "assistant": "a1"},
    {"user": "u2", "assistant": "a2"},
    {"user": "u3", "assistant": "a3"},
    {"user": "u4", "assistant": "a4"},
    {"user": "u5", "assistant": "a5"},
]
H = {i + 1: hash_turn(i + 1, m["user"], m["assistant"]) for i, m in enumerate(MSGS)}


def make_node(nid="n1", core_id=None, conf=0.5, turn=1, mapping_conf=0.9, label="x"):
    return {
        "id": nid,
        "label": label,
        "core_id": core_id,
        "mapping_confidence": mapping_conf,
        "confidence": conf,
        "evidence_turn": turn,
        "text_hash": H[turn],
    }


def make_edge(src="n1", tgt="n2", src_core=None, tgt_core=None,
              rel="contradicts", turn=1):
    return {
        "source_id": src,
        "target_id": tgt,
        "source_core_id": src_core,
        "target_core_id": tgt_core,
        "relation": rel,
        "created_at_turn": turn,
        "evidence_turn": turn,
        "text_hash": H[turn],
    }


def make_trans(node_id="n1", core_id=None, turn=1, delta=0.1):
    return {
        "node_id": node_id,
        "core_id": core_id,
        "turn": turn,
        "delta": delta,
        "trigger_text_hash": H[turn],
    }


def run_eval(nodes, edges, transitions, msgs=None, gt=None,
             nonce="SKIP_NONCE", raw_state=None):
    return evaluate(
        nodes=nodes, edges=edges, transitions=transitions,
        messages=msgs if msgs is not None else MSGS,
        gt=gt or {}, nonce=nonce, raw_state=raw_state,
    )


def _valid_two_concept_setup():
    """
    Two declared concepts, both used in edges *and* meaningful transitions.
    Passes the full integrity gauntlet: nonce, hashes, mapping_confidence,
    UNUSED_CONCEPTS, ZOMBIE_NODES, DEAD_CAUSALITY.
    """
    n1 = make_node("n1", core_id="ID_FOUNDER", conf=0.7, turn=1)
    n2 = make_node("n2", core_id="ID_EMPLOYEE", conf=0.3, turn=2)
    e = make_edge("n2", "n1", src_core="ID_EMPLOYEE", tgt_core="ID_FOUNDER",
                  rel="blocks", turn=2)
    t1 = make_trans("n1", "ID_FOUNDER", turn=1, delta=0.2)
    t2 = make_trans("n2", "ID_EMPLOYEE", turn=2, delta=-0.2)
    return [n1, n2], [e], [t1, t2]


def _edge_simple(src, tgt, rel="contradicts"):
    return {
        "source_id": "a", "target_id": "b",
        "source_core_id": src, "target_core_id": tgt,
        "relation": rel, "created_at_turn": 1, "evidence_turn": 1,
        "text_hash": "sha256:0",
    }


def _trs_simple(core_id, turn, delta):
    return {
        "node_id": "n1", "core_id": core_id, "turn": turn,
        "delta": delta, "trigger_text_hash": "sha256:0",
    }


def _node_simple(core_id, conf):
    return {
        "id": "n_" + core_id, "label": core_id, "core_id": core_id,
        "mapping_confidence": 0.9, "confidence": conf,
        "evidence_turn": 1, "text_hash": "sha256:0",
    }


# ===========================================================================
# Group A — hash functions
# ===========================================================================

def test_A1_hash_turn_deterministic():
    h1 = hash_turn(1, "hello", "world")
    h2 = hash_turn(1, "hello", "world")
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_A2_hash_turn_differs_on_turn_idx():
    assert hash_turn(1, "x", "y") != hash_turn(2, "x", "y")


def test_A3_hash_turn_differs_on_user():
    assert hash_turn(1, "user_a", "asst") != hash_turn(1, "user_b", "asst")


def test_A4_hash_turn_differs_on_assistant():
    assert hash_turn(1, "user", "asst_a") != hash_turn(1, "user", "asst_b")


def test_A5_h_dict_independent_of_key_order():
    d1 = {"a": 1, "b": 2, "c": [1, 2]}
    d2 = {"c": [1, 2], "b": 2, "a": 1}
    d3 = {"b": 2, "a": 1, "c": [1, 2]}
    assert _h_dict(d1) == _h_dict(d2) == _h_dict(d3)


# ===========================================================================
# Group B — integrity validator
# ===========================================================================

def test_B1_valid_minimal_submission_validated():
    nodes, edges, trs = _valid_two_concept_setup()
    r = run_eval(nodes, edges, trs)
    assert r["status"] == "VALIDATED", r.get("ban_reason")


def test_B2_nonce_mismatch_rejected():
    r = evaluate(
        nodes=[], edges=[], transitions=[],
        messages=MSGS, gt={}, nonce="wrong",
        raw_state={"_execution_nonce": "right"},
    )
    assert r["status"] == "REJECTED"
    assert "NONCE_MISMATCH" in r["ban_reason"]


def test_B3_node_text_hash_forgery():
    n = make_node("n1", core_id="ID_FOUNDER", turn=1)
    n["text_hash"] = "sha256:" + "0" * 64
    r = run_eval([n], [], [])
    assert r["status"] == "REJECTED"
    assert "TRACE_FORGERY" in r["ban_reason"]


def test_B4_edge_text_hash_forgery():
    nodes, edges, trs = _valid_two_concept_setup()
    edges[0]["text_hash"] = "sha256:" + "f" * 64
    r = run_eval(nodes, edges, trs)
    assert r["status"] == "REJECTED"
    assert "TRACE_FORGERY" in r["ban_reason"]


def test_B5_delta_above_upper_bound_rejected():
    n = make_node("n1", core_id="ID_FOUNDER", turn=1)
    t = make_trans("n1", "ID_FOUNDER", turn=1, delta=0.5)
    r = run_eval([n], [], [t])
    assert r["status"] == "REJECTED"
    assert "PHYSICS_IMPOSSIBLE_DELTA" in r["ban_reason"]


def test_B6_delta_below_lower_bound_rejected():
    n = make_node("n1", core_id="ID_FOUNDER", turn=1)
    t = make_trans("n1", "ID_FOUNDER", turn=1, delta=-0.5)
    r = run_eval([n], [], [t])
    assert r["status"] == "REJECTED"
    assert "PHYSICS_IMPOSSIBLE_DELTA" in r["ban_reason"]


def test_B7_zombie_node_no_edge_no_meaningful_transition():
    """
    Mapped node lacks edges and lacks |delta| > 0.01 transitions.
    Concept is "used" via a sibling node so UNUSED_CONCEPTS doesn't fire first.
    """
    n1 = make_node("n1", core_id="ID_FOUNDER", turn=1)  # zombie
    n2 = make_node("n2", core_id="ID_FOUNDER", turn=2)  # carries the concept
    t = make_trans("n2", "ID_FOUNDER", turn=2, delta=0.2)
    r = run_eval([n1, n2], [], [t])
    assert r["status"] == "REJECTED"
    assert "ZOMBIE_NODES" in r["ban_reason"]


def test_B8_weak_mapping_now_rejects_with_weak_mapping():
    """
    NOTE: ТЗ описывает старое поведение («core_id обнуляется, не банится»).
    Текущий validator банит c WEAK_MAPPING — закрепляем актуальное поведение.
    """
    n = make_node("n1", core_id="ID_FOUNDER", mapping_conf=0.5, turn=1)
    r = run_eval([n], [], [])
    assert r["status"] == "REJECTED"
    assert "WEAK_MAPPING" in r["ban_reason"]


def test_B9_dead_causality_when_source_weak_at_edge_creation():
    """
    Source ID_FOUNDER drops to 0.1 by turn 1 (delta -0.4 from default 0.5);
    edge created at turn 2 with that source → DEAD_CAUSALITY.
    """
    n1 = make_node("n1", core_id="ID_FOUNDER", turn=1)
    n2 = make_node("n2", core_id="ID_EMPLOYEE", turn=1)
    t1 = make_trans("n1", "ID_FOUNDER", turn=1, delta=-0.4)
    t2 = make_trans("n2", "ID_EMPLOYEE", turn=1, delta=0.2)
    e = make_edge("n1", "n2", src_core="ID_FOUNDER", tgt_core="ID_EMPLOYEE",
                  rel="blocks", turn=2)
    r = run_eval([n1, n2], [e], [t1, t2])
    assert r["status"] == "REJECTED"
    assert "DEAD_CAUSALITY" in r["ban_reason"]


def test_B10_unused_concept_dummy_node():
    """Single concept declared in nodes, never referenced by edges/transitions."""
    n = make_node("n1", core_id="ID_FOUNDER", turn=1)
    r = run_eval([n], [], [])
    assert r["status"] == "REJECTED"
    assert "UNUSED_CONCEPTS" in r["ban_reason"]


# ===========================================================================
# Group C — metrics
# ===========================================================================

def test_C1_cer_empty_gt_returns_none():
    assert compute_cer([], []) is None


def test_C2_cer_perfect_match():
    edges = [_edge_simple("A", "B")]
    assert compute_cer(edges, [["A", "B"]]) == 1.0


def test_C3_cer_zero_no_overlap():
    edges = [_edge_simple("A", "B")]
    assert compute_cer(edges, [["C", "D"]]) == 0.0


def test_C4_cer_partial_f1():
    # pred = {(A,B), (X,Y)}, gt = {(A,B), (C,D)}
    # tp=1, fp=1, fn=1 → F1 = 2 / (2 + 1 + 1) = 0.5
    edges = [_edge_simple("A", "B"), _edge_simple("X", "Y")]
    gt = [["A", "B"], ["C", "D"]]
    assert compute_cer(edges, gt) == 0.5


def test_C5_bda_up_with_positive_delta_matches():
    trs = [_trs_simple("V_GROWTH", 2, 0.10)]
    gt = [{"core_id": "V_GROWTH", "direction": "up"}]
    assert compute_bda(trs, gt) == 1.0


def test_C6_bda_up_then_down_temporal_order_matches():
    trs = [
        _trs_simple("ID_FOUNDER", 1, 0.15),
        _trs_simple("ID_FOUNDER", 5, -0.20),
    ]
    gt = [{"core_id": "ID_FOUNDER", "direction": "up_then_down"}]
    assert compute_bda(trs, gt) == 1.0


def test_C7_iss_zero_when_gap_below_threshold():
    nodes = [_node_simple("A", 0.5), _node_simple("B", 0.4)]
    # gap = 0.5 - 0.4 = 0.1 < 0.2 → 0.0
    assert compute_iss(nodes, {"to_id": "A", "from_id": "B"}) == 0.0


def test_C8_iss_full_score_when_gap_clamps_to_one():
    # Use a wide gap (0.95 - 0.05 = 0.9) so that (gap - 0.2) / 0.5 = 1.4
    # is clamped to 1.0 — avoids IEEE-754 artefacts at the exact boundary.
    nodes = [_node_simple("A", 0.95), _node_simple("B", 0.05)]
    assert compute_iss(nodes, {"to_id": "A", "from_id": "B"}) == 1.0


def test_C9_nrs_none_without_noise_turns():
    assert compute_nrs([], {}) is None


def test_C10_nrs_perfect_when_all_noise_deltas_below_threshold():
    trs = [_trs_simple("x", 1, 0.02), _trs_simple("x", 2, -0.05)]
    gt = {"noise_turns": [1, 2]}
    # |0.02| ≤ 0.05 and |-0.05| ≤ 0.05 → 0 intrusions → 1.0
    assert compute_nrs(trs, gt) == 1.0


# ===========================================================================
# Group D — evaluate() end-to-end
# ===========================================================================

def test_D1_minimal_valid_submission_all_scores_present_except_nrs():
    """
    Adds a turn-3 transition for ID_FOUNDER so GCS has a non-empty impact
    window (it returns 0.0, not None — net_impact fails causality threshold).
    """
    nodes, edges, trs = _valid_two_concept_setup()
    trs.append(make_trans("n1", "ID_FOUNDER", turn=3, delta=-0.1))

    gt = {
        "conflicts": [["ID_EMPLOYEE", "ID_FOUNDER"]],
        "belief_changes": [
            {"core_id": "ID_FOUNDER", "direction": "up"},
            {"core_id": "ID_EMPLOYEE", "direction": "down"},
        ],
        "identity_shift": {"from_id": "ID_EMPLOYEE", "to_id": "ID_FOUNDER"},
    }
    r = run_eval(nodes, edges, trs, gt=gt)
    assert r["status"] == "VALIDATED", r.get("ban_reason")
    s = r["scores"]
    for k in ("CER", "GCS", "BDA", "ISS"):
        assert s[k] is not None, f"{k} should not be None, got {s}"
    assert s["NRS"] is None  # no noise_turns in gt


def test_D2_empty_submission_does_not_crash():
    """Empty nodes/edges/transitions: integrity passes (nothing to ban), all metrics None."""
    r = evaluate(
        nodes=[], edges=[], transitions=[],
        messages=MSGS, gt={}, nonce="SKIP_NONCE",
    )
    assert r["status"] == "VALIDATED"
    for k in ("CER", "GCS", "BDA", "ISS", "NRS"):
        assert r["scores"][k] is None


def test_D3_tampered_raw_hash_rejected():
    raw = {"_execution_nonce": "nx", "anything": 1}
    bad_hash = "sha256:" + "0" * 64
    r = evaluate(
        nodes=[], edges=[], transitions=[],
        messages=MSGS, gt={}, nonce="nx",
        raw_state=raw, raw_hash=bad_hash,
    )
    assert r["status"] == "REJECTED"
    assert r.get("reason") == "RAW_TAMPERED"


# ===========================================================================
# Group E — hash stability
# ===========================================================================

def test_E1_evaluate_hash_idempotent_for_identical_inputs():
    nodes, edges, trs = _valid_two_concept_setup()
    gt = {"conflicts": [["ID_EMPLOYEE", "ID_FOUNDER"]]}
    r1 = run_eval(nodes, edges, trs, gt=gt)
    r2 = run_eval(nodes, edges, trs, gt=gt)
    assert r1["status"] == "VALIDATED"
    assert r1["hash"] == r2["hash"]


def test_E2_minimal_submission_hash_regression():
    """
    Pinned canonical hash for examples/submission_minimal.json + scenario_minimal.json
    with nonce="local_test". A change here means scoring semantics drifted —
    bump spec version explicitly if intentional.
    """
    root = Path(__file__).resolve().parents[1]
    sub = json.loads((root / "examples" / "submission_minimal.json").read_text("utf-8-sig"))
    scen = json.loads((root / "examples" / "scenario_minimal.json").read_text("utf-8-sig"))
    r = evaluate(
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
    assert r["status"] == "VALIDATED", r.get("ban_reason")
    assert r["hash"] == "sha256:1b50b46aaf5f85bdbe84e42d34fe4e62a366f15b6ea493e4b3d1061b0fa142e5"


# ===========================================================================
# Group F — Task 1: GCS consistency tests
# ===========================================================================

def test_gcs_comment_consistency():
    """GCS: both paths (zero baseline and no baseline) use same 0.1 energy threshold"""
    from driftbench_core.core import compute_gcs

    edges = [{
        "source_id": "n1", "target_id": "n2",
        "source_core_id": "ID_EMPLOYEE", "target_core_id": "ID_FOUNDER",
        "relation": "blocks", "created_at_turn": 2, "evidence_turn": 2,
        "text_hash": "sha256:x"
    }]
    transitions = [
        {"node_id": "n2", "core_id": "ID_FOUNDER", "turn": 2, "delta": -0.12, "trigger_text_hash": "x"},
    ]
    result = compute_gcs(edges, transitions, k=3)
    assert result == 1.0, f"Expected 1.0, got {result}"


def test_gcs_no_baseline_low_energy():
    """GCS: no baseline, energy < 0.1 -> not causal"""
    from driftbench_core.core import compute_gcs

    edges = [{
        "source_id": "n1", "target_id": "n2",
        "source_core_id": "ID_EMPLOYEE", "target_core_id": "ID_FOUNDER",
        "relation": "blocks", "created_at_turn": 2, "evidence_turn": 2,
        "text_hash": "sha256:x"
    }]
    transitions = [
        {"node_id": "n2", "core_id": "ID_FOUNDER", "turn": 2, "delta": -0.05, "trigger_text_hash": "x"},
    ]
    result = compute_gcs(edges, transitions, k=3)
    assert result == 0.0, f"Expected 0.0, got {result}"


# ===========================================================================
# Group G — Task 2: BDA up_then_down behavior tests
# ===========================================================================

def test_bda_up_then_down_partial_no_credit():
    """BDA: up_then_down without subsequent down -> 0 for this concept"""
    from driftbench_core.core import compute_bda

    transitions = [
        {"node_id": "n1", "core_id": "ID_FOUNDER", "turn": 1, "delta": 0.2, "trigger_text_hash": "x"},
    ]
    gt = [{"core_id": "ID_FOUNDER", "direction": "up_then_down"}]
    result = compute_bda(transitions, gt)
    assert result == 0.0, f"Expected 0.0, got {result}"


def test_bda_up_then_down_full_cycle():
    """BDA: up_then_down with full cycle -> counts"""
    from driftbench_core.core import compute_bda

    transitions = [
        {"node_id": "n1", "core_id": "ID_FOUNDER", "turn": 1, "delta": 0.2, "trigger_text_hash": "x"},
        {"node_id": "n1", "core_id": "ID_FOUNDER", "turn": 3, "delta": -0.15, "trigger_text_hash": "x"},
    ]
    gt = [{"core_id": "ID_FOUNDER", "direction": "up_then_down"}]
    result = compute_bda(transitions, gt)
    assert result == 1.0, f"Expected 1.0, got {result}"


def test_bda_up_then_down_wrong_order():
    """BDA: down before up -> does not count"""
    from driftbench_core.core import compute_bda

    transitions = [
        {"node_id": "n1", "core_id": "ID_FOUNDER", "turn": 1, "delta": -0.15, "trigger_text_hash": "x"},
        {"node_id": "n1", "core_id": "ID_FOUNDER", "turn": 3, "delta": 0.2, "trigger_text_hash": "x"},
    ]
    gt = [{"core_id": "ID_FOUNDER", "direction": "up_then_down"}]
    result = compute_bda(transitions, gt)
    assert result == 0.0, f"Expected 0.0, got {result}"


# ===========================================================================
# Group H — Task 3: Message validation tests
# ===========================================================================

def test_validate_messages_missing_keys():
    """_validate_integrity: message missing 'user' -> INVALID_MESSAGES"""
    from driftbench_core.core import evaluate, hash_turn

    messages = [
        {"turn": 1, "user": "Hello", "assistant": "Hi"},
        {"turn": 2, "text": "missing user and assistant"},
    ]
    h1 = hash_turn(1, "Hello", "Hi")

    nodes = [{
        "id": "n1", "label": "test", "core_id": "ID_FOUNDER",
        "mapping_confidence": 0.9, "confidence": 0.8,
        "evidence_turn": 1, "text_hash": h1
    }]
    edges = []
    transitions = [
        {"node_id": "n1", "core_id": "ID_FOUNDER", "turn": 1,
         "delta": 0.2, "trigger_text_hash": h1}
    ]
    gt = {"conflicts": [], "belief_changes": [], "identity_shift": {}}

    result = evaluate(
        nodes=nodes, edges=edges, transitions=transitions,
        messages=messages, gt=gt, nonce="SKIP_NONCE"
    )
    assert result["status"] == "REJECTED"
    assert "INVALID_MESSAGES" in result.get("ban_reason", "")


def test_validate_messages_not_dict():
    """_validate_integrity: message is string instead of dict -> INVALID_MESSAGES"""
    from driftbench_core.core import evaluate

    messages = ["not a dict"]
    result = evaluate(
        nodes=[], edges=[], transitions=[],
        messages=messages,
        gt={"conflicts": [], "belief_changes": [], "identity_shift": {}},
        nonce="SKIP_NONCE"
    )
    assert result["status"] == "REJECTED"
    assert "INVALID_MESSAGES" in result.get("ban_reason", "")
