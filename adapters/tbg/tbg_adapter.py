import warnings
from typing import Any, Dict, List

from driftbench_core.adapter import BaseAdapter


class TBGAdapter(BaseAdapter):
    """
    Reference DriftBench adapter for a Temporal Belief Graph (TBG) engine.

    This adapter only maps a TBG engine's output into the DriftBench submission
    format — it does NOT contain the engine itself. The engine is loaded
    separately (see the runner scripts kept alongside the private TBG codebase).

    Consumes raw_engine_log of shape:
        {
            "_execution_nonce": str,
            "messages": [{"user": str, "assistant": str}, ...],   # 1-indexed by position
            "turns": [
                {
                    "turn": int,
                    "nodes_added": [node_id, ...],
                    "nodes_modified": [node_id, ...],
                    "edges_added": [edge_key, ...],
                    "confidence_deltas": {node_id: float, ...},
                },
                ...
            ],
            "final_nodes": {node_id: dict, ...},   # node.model_dump() from TBG
            "final_edges": {edge_key: dict, ...},  # edge.model_dump() from TBG
        }
    """

    def __init__(self, ontology_path: str | None = None):
        super().__init__(ontology_path=ontology_path)

    def _resolve_core_id(self, concept_id: str | None) -> tuple[str | None, float]:
        if concept_id and concept_id in self.valid_ids:
            return concept_id, 1.0
        return None, 0.0

    def _evidence_turn_for_node(self, node_id: str, turns: List[Dict]) -> int:
        for t in turns:
            if node_id in t.get("nodes_added", []):
                return int(t["turn"])
        warnings.warn(f"Node {node_id} not found in nodes_added, defaulting to turn 1")
        return 1

    def _created_turn_for_edge(self, edge_key: str, turns: List[Dict]) -> int:
        for t in turns:
            if edge_key in t.get("edges_added", []):
                return int(t["turn"])
        warnings.warn(f"Edge {edge_key} not found in edges_added, defaulting to turn 1")
        return 1

    def _msg_for_turn(self, turn_idx: int, messages: List[Dict]) -> Dict[str, str]:
        if 1 <= turn_idx <= len(messages):
            m = messages[turn_idx - 1]
            return {"user": m.get("user", ""), "assistant": m.get("assistant", "")}
        return {"user": "", "assistant": ""}

    def format_state(self, raw_engine_log: Dict[str, Any]) -> Dict[str, Any]:
        messages: List[Dict] = raw_engine_log.get("messages", [])
        turns: List[Dict] = raw_engine_log.get("turns", [])
        final_nodes: Dict[str, Dict] = raw_engine_log.get("final_nodes", {})
        final_edges: Dict[str, Dict] = raw_engine_log.get("final_edges", {})

        # Node id → (core_id, mapping_confidence) — used by edges and transitions.
        node_core_map: Dict[str, tuple[str | None, float]] = {}
        for nid, node in final_nodes.items():
            node_core_map[nid] = self._resolve_core_id(node.get("concept_id"))

        nodes = []
        for nid, node in final_nodes.items():
            core_id, mapping_conf = node_core_map[nid]
            evidence_turn = self._evidence_turn_for_node(nid, turns)
            msg = self._msg_for_turn(evidence_turn, messages)
            nodes.append({
                "id": nid,
                "label": node.get("label", nid),
                "core_id": core_id,
                "mapping_confidence": mapping_conf,
                "confidence": round(float(node.get("confidence", 0.5)), 4),
                "evidence_turn": evidence_turn,
                "text_hash": self.hash_text(evidence_turn, msg["user"], msg["assistant"]),
            })

        edges = []
        for ekey, edge in final_edges.items():
            src_id = edge.get("source_id")
            tgt_id = edge.get("target_id")
            src_core = node_core_map.get(src_id, (None, 0.0))[0]
            tgt_core = node_core_map.get(tgt_id, (None, 0.0))[0]
            created = self._created_turn_for_edge(ekey, turns)
            msg = self._msg_for_turn(created, messages)
            edges.append({
                "source_id": src_id,
                "target_id": tgt_id,
                "source_core_id": src_core,
                "target_core_id": tgt_core,
                "relation": edge.get("relation", ""),
                "created_at_turn": created,
                "evidence_turn": created,
                "text_hash": self.hash_text(created, msg["user"], msg["assistant"]),
            })

        transitions = []
        for t in turns:
            turn_idx = int(t["turn"])
            msg = self._msg_for_turn(turn_idx, messages)
            trigger_hash = self.hash_text(turn_idx, msg["user"], msg["assistant"])
            for nid, raw_delta in t.get("confidence_deltas", {}).items():
                core_id = node_core_map.get(nid, (None, 0.0))[0]
                delta = max(-0.4, min(0.4, float(raw_delta)))
                transitions.append({
                    "node_id": nid,
                    "core_id": core_id,
                    "turn": turn_idx,
                    "delta": round(delta, 4),
                    "trigger_text_hash": trigger_hash,
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "transitions": transitions,
        }
