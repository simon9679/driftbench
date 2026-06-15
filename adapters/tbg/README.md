# TBG reference adapter

`tbg_adapter.py` is a reference adapter that maps the output of a **Temporal
Belief Graph (TBG)** engine into the DriftBench submission format.

It is included as a worked example of how a real belief-tracking engine plugs
into DriftBench. It implements only the format mapping — `BaseAdapter` →
`nodes` / `edges` / `transitions` with turn-bound trace hashes.

## What is and isn't here

- **Included:** the adapter (the input/output contract — what fields a TBG
  trace must provide and how they map to DriftBench).
- **Not included:** the TBG engine itself, and the runner scripts that drive it.
  The engine is a separate system; the adapter does not depend on it at import
  time.

## Expected input

The adapter consumes a raw engine trace of the shape documented in the
`TBGAdapter` docstring (`messages`, per-turn `nodes_added` / `edges_added` /
`confidence_deltas`, and `final_nodes` / `final_edges`). See
[`tbg_adapter.py`](tbg_adapter.py).

## Writing your own

To integrate a different engine, copy
[`../template_adapter.py`](../template_adapter.py) and implement `format_state`.
