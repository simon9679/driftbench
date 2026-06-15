"""
Template adapter for DriftBench.

Copy this file, rename the class, and implement format_state().
Run: python -m driftbench_core.validator --sub my_submission.json --scen scenario.json --nonce YOUR_NONCE
"""
from typing import Any, Dict

from driftbench_core.adapter import BaseAdapter


class TemplateAdapter(BaseAdapter):
    """
    TODO: Rename to YourSystemAdapter.

    Consumes raw_engine_log of shape:
        { ... your engine's internal format ... }

    Produces the DriftBench converted representation with
    nodes, edges, and transitions — all carrying trace hashes.
    """

    def format_state(self, raw_engine_log: Dict[str, Any]) -> Dict[str, Any]:
        messages = raw_engine_log.get("messages", [])

        # ------------------------------------------------------------------
        # 1. NODES
        #    Each node = a belief/concept your engine tracks.
        #    Required fields: id, label, core_id, mapping_confidence,
        #                    confidence, evidence_turn, text_hash
        # ------------------------------------------------------------------
        nodes = []
        for node in self._extract_nodes(raw_engine_log):
            evidence_turn = node["evidence_turn"]
            msg = self._msg_for_turn(evidence_turn, messages)
            nodes.append({
                "id": node["id"],
                "label": node["label"],
                "core_id": node.get("core_id"),          # must match ontology.json
                "mapping_confidence": node.get("mapping_confidence", 0.0),
                "confidence": node["confidence"],         # float in [0, 1]
                "evidence_turn": evidence_turn,
                "text_hash": self.hash_text(evidence_turn, msg["user"], msg["assistant"]),
            })

        # ------------------------------------------------------------------
        # 2. EDGES
        #    Relations between beliefs: blocks, contradicts, supports, etc.
        #    Only "blocks" and "contradicts" count toward CER/GCS.
        #    Required fields: source_id, target_id, source_core_id,
        #                    target_core_id, relation, created_at_turn,
        #                    evidence_turn, text_hash
        # ------------------------------------------------------------------
        edges = []
        for edge in self._extract_edges(raw_engine_log):
            created = edge["created_at_turn"]
            msg = self._msg_for_turn(created, messages)
            edges.append({
                "source_id": edge["source_id"],
                "target_id": edge["target_id"],
                "source_core_id": edge.get("source_core_id"),
                "target_core_id": edge.get("target_core_id"),
                "relation": edge["relation"],
                "created_at_turn": created,
                "evidence_turn": edge.get("evidence_turn", created),
                "text_hash": self.hash_text(created, msg["user"], msg["assistant"]),
            })

        # ------------------------------------------------------------------
        # 3. TRANSITIONS
        #    Confidence deltas per turn. Delta bounded to [-0.4, 0.4].
        #    Required fields: node_id, core_id, turn, delta,
        #                    trigger_text_hash
        # ------------------------------------------------------------------
        transitions = []
        for tr in self._extract_transitions(raw_engine_log):
            turn_idx = tr["turn"]
            msg = self._msg_for_turn(turn_idx, messages)
            delta = max(-0.4, min(0.4, tr["delta"]))
            transitions.append({
                "node_id": tr["node_id"],
                "core_id": tr.get("core_id"),
                "turn": turn_idx,
                "delta": round(delta, 4),
                "trigger_text_hash": self.hash_text(turn_idx, msg["user"], msg["assistant"]),
            })

        return {"nodes": nodes, "edges": edges, "transitions": transitions}

    # ------------------------------------------------------------------
    # TODO: Implement these three methods for your engine
    # ------------------------------------------------------------------

    def _extract_nodes(self, raw_engine_log: Dict) -> list:
        """Return a list of dicts with at least: id, label, confidence, evidence_turn."""
        # Example:
        # return [{"id": n["id"], "label": n["label"], "confidence": n["confidence"],
        #          "evidence_turn": n["first_seen_turn"], "core_id": None,
        #          "mapping_confidence": 0.0} for n in raw_engine_log["nodes"]]
        raise NotImplementedError

    def _extract_edges(self, raw_engine_log: Dict) -> list:
        """Return a list of dicts with at least: source_id, target_id, relation, created_at_turn."""
        # Example:
        # return [{"source_id": e["src"], "target_id": e["tgt"],
        #          "relation": e["type"], "created_at_turn": e["turn"]} for e in raw_engine_log["edges"]]
        raise NotImplementedError

    def _extract_transitions(self, raw_engine_log: Dict) -> list:
        """Return a list of dicts with at least: node_id, turn, delta."""
        # Example:
        # return [{"node_id": t["node"], "turn": t["turn"], "delta": t["delta"]} for t in raw_engine_log["deltas"]]
        raise NotImplementedError

    def _msg_for_turn(self, turn_idx: int, messages: list) -> Dict[str, str]:
        """Get user/assistant text for a 1-indexed turn."""
        if 1 <= turn_idx <= len(messages):
            m = messages[turn_idx - 1]
            return {"user": m.get("user", ""), "assistant": m.get("assistant", "")}
        return {"user": "", "assistant": ""}


# ------------------------------------------------------------------
# Usage example
# ------------------------------------------------------------------
if __name__ == "__main__":
    import json

    adapter = TemplateAdapter()

    # TODO: Load your engine's actual output
    raw_engine_log = {
        "_execution_nonce": "your_nonce_here",
        "messages": [],  # fill with scenario messages
    }

    submission = adapter.export(raw_engine_log)
    print(json.dumps(submission, indent=2))
