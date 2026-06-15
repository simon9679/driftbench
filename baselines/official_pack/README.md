# baselines/official_pack/

This directory will contain official benchmark results once v1 evaluation runs are complete.

**Results will be added here after the v1 public launch.**

Planned baseline submissions covering all 7 official scenarios:

| System | CER | GCS | BDA | ISS | NRS |
|--------|-----|-----|-----|-----|-----|
| TBG reference implementation | — | — | — | — | — |
| Naive last-message memory | — | — | — | — | — |
| Fact-store memory | — | — | — | — | — |
| Graph memory | — | — | — | — | — |

Run your own evaluation against any LLM:

```bash
python adapters/simple/driftbench_run.py --provider openai --model gpt-4o
```

Or validate a submission produced by your own adapter:

```bash
driftbench-validate --sub your_submission.json \
    --scen standard/v1/scenarios/01_burnout_to_founder.json --nonce YOUR_NONCE
```

See [`adapters/tbg/README.md`](../../adapters/tbg/README.md) for the reference
adapter and [`adapters/template_adapter.py`](../../adapters/template_adapter.py)
to integrate your own engine.
