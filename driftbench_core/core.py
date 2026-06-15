import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any, TypedDict
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_EVEN


class BeliefNode(TypedDict):
    id: str
    label: str
    core_id: Optional[str]
    mapping_confidence: float
    confidence: float
    evidence_turn: int
    text_hash: str


class BeliefEdge(TypedDict):
    source_id: str
    target_id: str
    source_core_id: Optional[str]
    target_core_id: Optional[str]
    relation: str
    created_at_turn: int
    evidence_turn: int
    text_hash: str


class BeliefTransition(TypedDict):
    node_id: str
    core_id: Optional[str]
    turn: int
    delta: Optional[float]
    trigger_text_hash: str


def _h(data: str) -> str:
    return "sha256:" + hashlib.sha256(data.encode('utf-8')).hexdigest()


def _h_dict(data: Dict) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def hash_turn(turn_idx: int, user: str, assistant: str) -> str:
    payload = json.dumps({"t": turn_idx, "u": user, "a": assistant}, sort_keys=True)
    return _h(payload)


def _dec_str(v: float) -> str:
    return str(Decimal(str(v)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_EVEN))


def _validate_integrity(
    nodes: List[BeliefNode], edges: List[BeliefEdge], transitions: List[BeliefTransition],
    messages: List[Dict], raw_state: Dict, nonce: str
) -> Optional[str]:
    if nonce != "SKIP_NONCE" and raw_state.get("_execution_nonce") != nonce:
        return "NONCE_MISMATCH: Precomputed submission detected"

    for i, m in enumerate(messages):
        if not isinstance(m, dict):
            return f"INVALID_MESSAGES: message at index {i} is not a dict"
        if "user" not in m or "assistant" not in m:
            return f"INVALID_MESSAGES: message at index {i} missing 'user' or 'assistant' key"

    turn_hashes = {i + 1: hash_turn(i + 1, m["user"], m["assistant"]) for i, m in enumerate(messages)}
    declared_concepts = set()  # core_ids declared in nodes
    used_concepts_edges = set()  # core_ids used in edges
    used_concepts_trans = set()  # core_ids with meaningful transitions
    node_ids_with_edges = set()  # node ids that appear as source or target in edges
    trans_per_turn = defaultdict(int)  # anti-cheat: transition spam limit
    micro_delta_count = 0  # anti-cheat: micro-delta spam

    # --- Nodes ---
    node_id_set = set()
    node_core_map = {}  # node_id → core_id (for consistency check)
    for n in nodes:
        t = n["evidence_turn"]
        if t not in turn_hashes or n["text_hash"] != turn_hashes[t]:
            return "TRACE_FORGERY: Hash mismatch or temporal paradox"
        nid = n["id"]
        node_id_set.add(nid)
        cid = n.get("core_id")
        if cid:
            if n.get("mapping_confidence", 1.0) < 0.7:
                return f"WEAK_MAPPING: core_id set but mapping_confidence={n.get('mapping_confidence', 1.0)} < 0.7"
            declared_concepts.add(cid)
            node_core_map[nid] = cid

    # --- Edges ---
    for e in edges:
        t = e["evidence_turn"]
        if t not in turn_hashes or e["text_hash"] != turn_hashes[t]:
            return "TRACE_FORGERY: Edge hash mismatch"
        # Graph consistency: source_id and target_id must reference existing nodes
        if e["source_id"] not in node_id_set:
            return f"ORPHAN_EDGE: source_id {e['source_id']} does not exist in nodes"
        if e["target_id"] not in node_id_set:
            return f"ORPHAN_EDGE: target_id {e['target_id']} does not exist in nodes"
        # Edge core_ids must match declared concepts
        if e.get("source_core_id") and e["source_core_id"] not in declared_concepts:
            return f"UNDECLARED_CONCEPT: Edge source_core_id {e['source_core_id']} not in any node"
        if e.get("target_core_id") and e["target_core_id"] not in declared_concepts:
            return f"UNDECLARED_CONCEPT: Edge target_core_id {e['target_core_id']} not in any node"
        # Edge core_ids must be consistent with node→core_id mapping
        if e.get("source_core_id") and e["source_id"] in node_core_map:
            if node_core_map[e["source_id"]] != e["source_core_id"]:
                return f"INCONSISTENT_CORE_ID: Edge claims source {e['source_id']}={e['source_core_id']} but node has {node_core_map[e['source_id']]}"
        if e.get("target_core_id") and e["target_id"] in node_core_map:
            if node_core_map[e["target_id"]] != e["target_core_id"]:
                return f"INCONSISTENT_CORE_ID: Edge claims target {e['target_id']}={e['target_core_id']} but node has {node_core_map[e['target_id']]}"
        node_ids_with_edges.add(e["source_id"])
        node_ids_with_edges.add(e["target_id"])
        if e.get("source_core_id"):
            used_concepts_edges.add(e["source_core_id"])
        if e.get("target_core_id"):
            used_concepts_edges.add(e["target_core_id"])

    # --- Transitions ---
    for tr in transitions:
        t = tr["turn"]
        if t not in turn_hashes or tr.get("trigger_text_hash") != turn_hashes[t]:
            return "UNBOUND_TRANSITIONS: Fake delta without source message"
        if tr.get("delta") is not None and abs(tr["delta"]) > 0.4:
            return f"PHYSICS_IMPOSSIBLE_DELTA: |{tr['delta']}| > 0.4"
        trans_per_turn[t] += 1
        if tr.get("delta") is not None and 0 < abs(tr["delta"]) <= 0.01:
            micro_delta_count += 1
        if tr.get("core_id") and tr.get("delta") is not None and abs(tr["delta"]) > 0.01:
            used_concepts_trans.add(tr["core_id"])

    # --- Anti-cheat: transition spam (absolute threshold, not tied to user-controlled len(nodes)) ---
    if trans_per_turn and max(trans_per_turn.values()) > 20:
        return "TRANSITION_SPAM: Too many transitions in a single turn"
    if micro_delta_count > 20:
        return "MICRO_DELTA_SPAM: Excessive near-zero deltas"

    # --- UNUSED_CONCEPTS: any declared concept must participate ---
    for cid in declared_concepts:
        if cid not in used_concepts_trans and cid not in used_concepts_edges:
            return f"UNUSED_CONCEPTS: Concept {cid} declared but never used"

    # --- ZOMBIE_NODES: mapped nodes must have edges or meaningful transitions ---
    for n in nodes:
        if not n.get("core_id"):
            continue
        has_edge = n["id"] in node_ids_with_edges
        has_meaningful_trans = any(
            tr["node_id"] == n["id"] and tr.get("delta") is not None and abs(tr["delta"]) > 0.01
            for tr in transitions
        )
        if not has_edge and not has_meaningful_trans:
            return f"ZOMBIE_NODES: Node {n['id']} mapped but unused (no edges, no meaningful transitions)"

    trajectories = defaultdict(list)
    trajectories_default = defaultdict(lambda: 0.5)
    for tr in sorted(transitions, key=lambda x: x["turn"]):
        cid = tr.get("core_id")
        if not cid or tr["delta"] is None:
            continue
        new_conf = max(0.0, min(1.0, trajectories_default[cid] + tr["delta"]))
        trajectories[cid].append((tr["turn"], new_conf))
        trajectories_default[cid] = new_conf

    for e in edges:
        if e["relation"] not in ("blocks", "contradicts"):
            continue
        src = e.get("source_core_id")
        if not src:
            continue
        conf_at_creation = 0.5
        for turn, conf in trajectories.get(src, []):
            if turn <= e["created_at_turn"]:
                conf_at_creation = conf
        if conf_at_creation < 0.2:
            return "DEAD_CAUSALITY: Source was weak when edge created"
    return None


def compute_cer(edges: List[BeliefEdge], gt: List[Tuple[str, str]]) -> Optional[float]:
    if not gt:
        return None
    pred = {
        (e["source_core_id"], e["target_core_id"])
        for e in edges
        if e["relation"] in ("blocks", "contradicts") and e.get("source_core_id") and e.get("target_core_id")
    }
    gt_set = set(tuple(c) for c in gt)
    tp = len(pred & gt_set)
    if tp == 0:
        return 0.0
    fp, fn = len(pred - gt_set), len(gt_set - pred)
    return (2 * tp) / ((2 * tp) + fp + fn)


def compute_gcs(edges: List[BeliefEdge], transitions: List[BeliefTransition], k: int = 3) -> Optional[float]:
    valid = 0
    causal_count = 0

    trans_by_cid = defaultdict(list)
    for t in transitions:
        if t.get("core_id") and t.get("delta") is not None:
            trans_by_cid[t["core_id"]].append(t)

    for e in edges:
        if e["relation"] not in ("blocks", "contradicts") or not e.get("target_core_id"):
            continue
        target_id = e["target_core_id"]
        t_create = e["created_at_turn"]

        window_deltas = [
            t["delta"] for t in trans_by_cid[target_id]
            if t_create <= t["turn"] <= t_create + k
        ]
        if not window_deltas:
            continue
        valid += 1

        impact_energy = sum(abs(d) for d in window_deltas)

        baseline_deltas = [
            t["delta"] for t in trans_by_cid[target_id]
            if t["turn"] < t_create
        ]

        # Direction check: conflict edge should suppress target (net negative movement)
        net_impact = sum(window_deltas)
        is_causal = False
        if baseline_deltas:
            baseline_avg = sum(abs(d) for d in baseline_deltas) / len(baseline_deltas)
            if baseline_avg < 0.01 or impact_energy > baseline_avg * 1.5:
                is_causal = net_impact < -0.05 and impact_energy >= 0.1
        else:
            # No prior history for this concept — require absolute energy threshold
            is_causal = net_impact < -0.05 and impact_energy >= 0.1

        if is_causal:
            causal_count += 1

    return causal_count / valid if valid > 0 else None


def compute_nrs(transitions: List[BeliefTransition], gt: Dict) -> Optional[float]:
    noise_turns = set(gt.get("noise_turns", []))
    if not noise_turns:
        return None

    noise_deltas = [
        t["delta"] for t in transitions
        if t["turn"] in noise_turns and t.get("delta") is not None
    ]

    if not noise_deltas:
        return 1.0

    intrusions = sum(1 for d in noise_deltas if abs(d) > 0.05)
    return 1.0 - (intrusions / len(noise_deltas))


def compute_bda(transitions: List[BeliefTransition], gt: List[Dict]) -> Optional[float]:
    if not gt:
        return None
    matched = 0
    for c in gt:
        cid_trs = [(t["turn"], t["delta"]) for t in transitions if t.get("core_id") == c["core_id"] and t["delta"] is not None]
        if not cid_trs:
            continue
        deltas = [d for _, d in cid_trs]
        if c["direction"] == "up" and any(x > 0.05 for x in deltas):
            matched += 1
        elif c["direction"] == "down" and any(x < -0.05 for x in deltas):
            matched += 1
        elif c["direction"] == "up_then_down":
            # Requires BOTH up > 0.05 followed by down < -0.05 in chronological order.
            # Partial match (only up, no subsequent down) scores 0 for this concept.
            # This is intentional: up_then_down represents a full reversal cycle.
            sorted_trs = sorted(cid_trs, key=lambda x: x[0])
            has_up = False
            for _, d in sorted_trs:
                if d > 0.05:
                    has_up = True
                elif d < -0.05 and has_up:
                    matched += 1
                    break
    return matched / len(gt)


def compute_iss(nodes: List[BeliefNode], gt: Dict) -> Optional[float]:
    to_id, from_id = gt.get("to_id"), gt.get("from_id")
    if not to_id:
        return None
    cm = {n["core_id"]: n["confidence"] for n in nodes if n.get("core_id")}
    if to_id not in cm:
        return 0.0
    if from_id and from_id not in cm:
        return None
    from_conf = cm.get(from_id, 0.5) if from_id else 0.5
    gap = cm[to_id] - from_conf
    return min(1.0, max(0.0, (gap - 0.2) / 0.5)) if gap >= 0.2 else 0.0


def evaluate(
    nodes: List[BeliefNode], edges: List[BeliefEdge], transitions: List[BeliefTransition],
    messages: List[Dict], gt: Dict[str, Any], nonce: str,
    raw_state: Optional[Dict] = None, raw_hash: Optional[str] = None, conv_hash: Optional[str] = None
) -> Dict[str, Any]:
    inputs_hash = _h_dict({"gt": gt, "nonce": nonce, "msgs": messages})
    if raw_state and raw_hash and _h_dict(raw_state) != raw_hash:
        return {"status": "REJECTED", "reason": "RAW_TAMPERED", "hash": "sha256:err"}
    ban = _validate_integrity(nodes, edges, transitions, messages, raw_state or {}, nonce)
    if ban:
        return {
            "spec": "1.0.0", "status": "REJECTED", "ban_reason": ban,
            "reason_code": ban.split(":")[0],
            "scores": {"CER": 0.0, "GCS": 0.0, "BDA": 0.0, "ISS": 0.0, "NRS": 0.0, "PENALTY": ban.split(":")[0]},
            "hash": "sha256:0000",
        }

    scores = {
        "CER": compute_cer(edges, gt.get("conflicts", [])),
        "GCS": compute_gcs(edges, transitions),
        "BDA": compute_bda(transitions, gt.get("belief_changes", [])),
        "ISS": compute_iss(nodes, gt.get("identity_shift", {})),
        "NRS": compute_nrs(transitions, gt),
    }

    can_scores = {k: (_dec_str(v) if isinstance(v, float) else v) for k, v in scores.items() if v is not None}
    payload = json.dumps({"s": can_scores, "i": inputs_hash}, sort_keys=True, separators=(',', ':'))
    return {
        "spec": "1.0.0", "status": "VALIDATED", "ban_reason": None,
        "scores": scores,
        "hash": "sha256:" + hashlib.sha256(payload.encode()).hexdigest(),
    }
