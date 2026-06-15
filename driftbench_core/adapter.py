import json
import hashlib
from typing import Dict
from pathlib import Path


class DriftBenchAdapterError(Exception):
    """Raised when an adapter produces an invalid submission."""


class BaseAdapter:
    """
    Base class for DriftBench adapters.

    Subclass this and implement :meth:`format_state` to convert your
    engine's internal log into the DriftBench submission format.

    Example::

        class MyAdapter(BaseAdapter):
            def format_state(self, raw_engine_log: dict) -> dict:
                return {
                    "nodes": [...],
                    "edges": [...],
                    "transitions": [...],
                }

        adapter = MyAdapter()
        submission = adapter.export(my_engine_log)
    """

    def __init__(self, ontology_path: str | None = None):
        if ontology_path is None:
            ontology_file = (
                Path(__file__).resolve().parent.parent
                / "standard"
                / "v1"
                / "ontology.json"
            )
        else:
            ontology_file = Path(ontology_path)

        if not ontology_file.exists():
            raise DriftBenchAdapterError(f"Ontology missing: {ontology_file}")

        self.ontology_path = ontology_file
        self.valid_ids = set(
            json.loads(ontology_file.read_text("utf-8-sig"))["concepts"].keys()
        )

    def _h(self, data: Dict) -> str:
        return "sha256:" + hashlib.sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def hash_text(self, turn_idx: int, user_text: str, assistant_text: str) -> str:
        """Compute a turn hash. Signature matches ``core.hash_turn`` exactly."""
        payload = json.dumps(
            {"t": turn_idx, "u": user_text, "a": assistant_text}, sort_keys=True
        )
        return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def format_state(self, raw_engine_log: Dict) -> Dict:
        """Convert raw engine log into DriftBench nodes/edges/transitions.

        Override this method in your subclass.
        """
        raise NotImplementedError

    def export(self, raw_engine_log: Dict) -> Dict:
        """Hash, validate, and package the submission.

        Returns a dict with keys ``raw``, ``raw_h``, ``conv``, ``conv_h``
        ready to be serialised and passed to ``driftbench-validate``.
        """
        raw_hash = self._h(raw_engine_log)
        converted = self.format_state(raw_engine_log)

        for n in converted.get("nodes", []):
            if "text_hash" not in n:
                raise DriftBenchAdapterError("Missing text_hash in node")
            if n.get("core_id") and n["core_id"] not in self.valid_ids:
                raise DriftBenchAdapterError(f"Invalid core_id: {n['core_id']}")

        for e in converted.get("edges", []):
            if "text_hash" not in e:
                raise DriftBenchAdapterError("Missing text_hash in edge")
            if e.get("source_core_id") and e["source_core_id"] not in self.valid_ids:
                raise DriftBenchAdapterError(
                    f"Invalid edge source_core_id: {e['source_core_id']}"
                )
            if e.get("target_core_id") and e["target_core_id"] not in self.valid_ids:
                raise DriftBenchAdapterError(
                    f"Invalid edge target_core_id: {e['target_core_id']}"
                )

        return {
            "raw": raw_engine_log,
            "raw_h": raw_hash,
            "conv": converted,
            "conv_h": self._h(converted),
        }
