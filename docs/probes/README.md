# Validity probes

Two offline probes that check whether the metrics measure what the spec claims.
They read only committed artifacts — no keys, no network — and do not modify the
repository. Both are deterministic: run twice, get byte-identical JSON.

```bash
python dev-scripts/probes/label_invariance_probe.py --seeds 50   # -> docs/probes/label_invariance.json
python dev-scripts/probes/oracle_probe.py                        # -> docs/probes/oracle.json
```

## `label_invariance_probe.py`

Takes the real belief states in `baselines/variance/gpt-oss-120b/{run1,run2,run3}/`,
applies a **consistent** random permutation of the eight ontology `core_id`s across
every node/edge/transition (structure kept, meaning destroyed), and rescores. The
published default is **500 seeds** × 19 states (2 skipped for `parse_error`) = 9500
permutations. (50 seeds is too few — the pathological-reversal rates are unstable
there and *understate* the effect; see the caveat below.)

Reading the numbers:

- **`pct_unchanged` = 100** → the metric ignores the labels entirely. It is a
  **structural / temporal** diagnostic, not a semantic-correctness one.
- **`pct_improved_pathological` > 0** → scrambling the labels sometimes *raises* the
  score, so that metric can be optimised in the wrong direction.

Result (this corpus, `--seeds 500` = 9500 permutations):

| metric | mean before | mean after | % unchanged | % improved (pathological) |
|--------|-------------|------------|-------------|---------------------------|
| CER | 0.2934 | 0.0606 | 21.5 | 1.9 |
| GCS | 0.2969 | 0.2969 | **100.0** | 0.0 |
| BDA | 0.6071 | 0.4006 | 26.0 | 7.8 |
| ISS | 0.4779 | 0.1779 | 35.2 | **14.4** |
| NRS | 0.0 | 0.0 | **100.0** | 0.0 |

**GCS and NRS are perfectly label-invariant** — they measure structure/timing, not
semantics. CER, BDA, ISS all degrade under permutation (they *are* semantic), and
each can **pathologically improve** on some permutations (ISS most, ~14%).

> **These are a Monte-Carlo estimate, not fixed constants.** `mean_before` is exact
> (it does not depend on the permutation), but `mean_after` and the unchanged/improved
> rates carry sampling noise of order ~1% between independent RNG streams. At 50 seeds
> the estimate is unstable and *understates* the reversal rate (ISS ≈ 10.6% at 50 vs
> ≈ 14% at 500); 500 is used for the published figures. Someone re-running with a
> different seed count or RNG will get slightly different `_after` numbers — that is
> sampling noise, not a discrepancy. What is invariant to the sample: **GCS/NRS at
> 100% unchanged / 0% improved**, and the ordering ISS > BDA > CER on reversals.

## `oracle_probe.py`

Builds, from each scenario's ground truth, a deliberately ideal submission and scores
it through the **real** `evaluate` path (nonce + integrity + anti-cheat + scoring).
Without this, low canary scores would prove nothing — a metric that always returned
0.0 would pass every degeneracy check.

The construction is the substantive part (a naive build fails GCS):

- non-overlapping suppression windows per conflict target;
- **energy escalation** for a repeated target (`0.2 → 0.35 → 0.4×2`), because GCS
  requires `impact_energy > baseline_avg × 1.5` for later edges on the same target;
- BDA moves placed after each concept's last window (or, for a target whose windows
  fill the timeline, inside its last dominant window, where a `+0.2` cannot flip the
  net);
- no transition on any noise turn (keeps NRS = 1.0).

Result: **1.000 on CER/GCS/BDA/ISS on all 7 scenarios** (NRS 1.000 on
`11_noise_resistance`, `None` elsewhere — no noise turns). The metrics have a
ground-truth-reachable maximum; a naive oracle that scored GCS < 1.0 was a
construction error, not a metric ceiling.
