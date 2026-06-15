# Contributing to DriftBench

Thank you for your interest in contributing! DriftBench is an open standard — its value grows with every system that integrates it.

## Ways to contribute

### 1. Evaluate your system and share results

The fastest way to contribute is to run your cognitive AI system through the benchmark and open a PR with your results in `baselines/`.

```bash
pip install -e .
# Run the universal runner against your LLM:
python adapters/simple/driftbench_run.py --provider openai --model gpt-4o
# Or validate a custom submission:
driftbench-validate --sub your_submission.json --scen standard/v1/scenarios/01_burnout_to_founder.json --nonce YOUR_NONCE
```

### 2. Write an adapter

If you have a cognitive engine (belief graph, memory system, agent framework), write an adapter by subclassing `BaseAdapter`:

```python
from driftbench_core.adapter import BaseAdapter

class MyAdapter(BaseAdapter):
    def format_state(self, raw_engine_log: dict) -> dict:
        return {
            "nodes": [...],
            "edges": [...],
            "transitions": [...],
        }
```

See [`adapters/template_adapter.py`](adapters/template_adapter.py) for the full skeleton with `TODO` markers.

### 3. Propose new scenarios

Scenarios live in `standard/v1/scenarios/`. A scenario is a JSON file with:
- `messages` — the conversation turns
- `ground_truth` — conflict pairs, belief change directions, identity shift, noise turns

Open an issue with `[scenario]` in the title and describe the psychological transition you want to model.

### 4. Propose new metrics or ontology concepts

- New metrics for v1.1+ (OCS, TPS) → open an issue with `[metric]`
- New ontology concepts → open an issue with `[ontology]`

The v1 spec and ontology are **frozen** for reproducibility. Additions go into `v1.1+` branches.

### 5. Report bugs

Open an issue with:
- Python version
- Exact command run
- Full error output
- Input files (submission + scenario) if possible

## Running tests locally

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Code style

- Python 3.10+, no external dependencies in `driftbench_core`
- Type hints on all public functions
- No LLM calls in `driftbench_core` — it must stay deterministic

## License

By contributing, you agree that your contributions will be licensed under [Apache 2.0](LICENSE).
