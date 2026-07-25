#!/usr/bin/env python3
"""
DriftBench LLM baselines (multi-provider)
=========================================
Runs pure LLM baselines over the 7 official v1 scenarios. The LLM builds the
belief graph; scoring uses the CANONICAL metrics from driftbench_core.core
(single source of truth — never reimplemented here).

Providers:
  --provider cerebras   OpenAI SDK, base_url=cerebras, reasoning models (gpt-oss,
                        zai-glm). reasoning_effort=low, large max_tokens.
  --provider github     OpenAI SDK, GitHub Models (base_url=models.github.ai),
                        non-reasoning instruct models (openai/gpt-4.1). Key=GITHUB_TOKEN.
  --provider anthropic  anthropic SDK, Claude Haiku/Sonnet. Key=ANTHROPIC_API_KEY.

LESSON (from the zai-glm-4.7 run): reasoning models spend the whole token budget
on hidden reasoning and truncate / malform the JSON. For a clean second/third
baseline point, prefer NON-REASONING instruct models that reliably emit valid JSON.

Critical step: official scenarios have NO `concepts` block — concepts live in the
frozen ontology. build_prompt() reads scenario["concepts"], so we inject the
ontology into each scenario before building the prompt. Without it the model
invents its own ids and CER collapses to 0 (the trap the TBG pack hit).

Usage (PowerShell, from repo root):
    # Cerebras (reasoning) — key from _cerebras.env
    py run_baselines.py --provider cerebras --model gpt-oss-120b

    # GitHub Models (non-reasoning) — key from GITHUB_TOKEN
    py run_baselines.py --provider github --model openai/gpt-4.1

    # Anthropic — key from ANTHROPIC_API_KEY
    py run_baselines.py --provider anthropic --model claude-haiku-4-5
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCEN_DIR = ROOT / "standard" / "v1" / "scenarios"
ONTOLOGY_PATH = ROOT / "standard" / "v1" / "ontology.json"
OUT_DIR = ROOT / "baselines" / "llm"

SCENARIO_FILES = [
    "01_burnout_to_founder.json",
    "02_promotion_vs_founder.json",
    "03_financial_identity.json",
    "04_failure_recovery_to_launch.json",
    "05_promotion_after_launch.json",
    "10_delayed_contradiction.json",
    "11_noise_resistance.json",
]

# Reuse the convenience runner's prompt builder / parser and the EXACT canonical
# metric calls — do not duplicate that logic here.
sys.path.insert(0, str(ROOT / "adapters" / "simple"))
from driftbench_run import build_prompt, parse_belief_state  # noqa: E402
from driftbench_core.core import (  # noqa: E402
    compute_cer,
    compute_gcs,
    compute_bda,
    compute_iss,
    compute_nrs,
)

# ─── Provider config ─────────────────────────────────────────────────────────
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"
GITHUB_BASE_URL = "https://models.github.ai/inference"
GITHUB_LEGACY_BASE_URL = "https://models.inference.ai.azure.com"  # 404 fallback
GITHUB_LEGACY_MODEL = "gpt-4o"

PROVIDER_DEFAULTS = {
    # reasoning models need a large budget; non-reasoning ones stop early.
    "cerebras":  {"max_tokens": 20000, "reasoning_effort": "low"},
    "github":    {"max_tokens": 4000,  "reasoning_effort": None},
    "anthropic": {"max_tokens": 4000,  "reasoning_effort": None},
}

RPS_DELAY_SECONDS = 13  # free-tier rate limits (cerebras / github ~10 RPM)
MAX_RETRIES = 4
METRICS = ["CER", "GCS", "BDA", "ISS", "NRS"]


def model_slug(model: str) -> str:
    return "".join(c if (c.isalnum() or c in "-._") else "_" for c in model)


# ─── Setup ───────────────────────────────────────────────────────────────────

def load_ontology() -> tuple[dict, set]:
    onto = json.loads(ONTOLOGY_PATH.read_text("utf-8-sig"))
    concepts = {
        cid: f'{c["canonical_label"]} — {c["description"]}'
        for cid, c in onto["concepts"].items()
    }
    return concepts, set(onto["concepts"].keys())


def get_api_key(provider: str) -> str:
    import os
    if provider == "cerebras":
        key = os.environ.get("CEREBRAS_API_KEY", "").strip()
        if key:
            return key
        env_file = ROOT / "_cerebras.env"
        if env_file.exists():
            for line in env_file.read_text("utf-8").splitlines():
                if line.startswith("CEREBRAS_API_KEY="):
                    return line.split("=", 1)[1].strip()
        sys.exit("CEREBRAS_API_KEY not set (env var or _cerebras.env)")
    if provider == "github":
        return _key_from_env_or_file("GITHUB_TOKEN", ROOT / "_github.env")
    if provider == "anthropic":
        return _key_from_env_or_file("ANTHROPIC_API_KEY", ROOT / "_anthropic.env")
    sys.exit(f"unknown provider: {provider}")


def _key_from_env_or_file(var: str, env_file: Path) -> str:
    import os
    key = os.environ.get(var, "").strip()
    # Reject the Cyrillic placeholder ("ghp_ВСТАВЬТЕ…") that shadows a real token.
    if key and all(ord(c) < 128 for c in key):
        return key
    if env_file.exists():
        for line in env_file.read_text("utf-8").splitlines():
            if line.startswith(f"{var}="):
                v = line.split("=", 1)[1].strip()
                if v:
                    return v
    hint = " (env var holds a non-ASCII placeholder — ignored)" if key else ""
    sys.exit(f"{var} not set: put it in {env_file.name} or the env var{hint}")


# ─── Scoring ─────────────────────────────────────────────────────────────────

def score_state(state: dict, gt: dict) -> dict:
    """Exact canonical calls, mirrored from adapters/simple/driftbench_run.py:500."""
    return {
        "CER": compute_cer(state.get("edges", []), gt.get("conflicts", [])),
        "GCS": compute_gcs(state.get("edges", []), state.get("transitions", [])),
        "BDA": compute_bda(state.get("transitions", []), gt.get("belief_changes", [])),
        "ISS": compute_iss(state.get("nodes", []), gt.get("identity_shift", {})),
        "NRS": compute_nrs(state.get("transitions", []), gt),
    }


def foreign_core_ids(state: dict, onto_ids: set) -> set:
    seen = set()
    for n in state.get("nodes", []):
        if n.get("core_id"):
            seen.add(n["core_id"])
    for e in state.get("edges", []):
        for k in ("source_core_id", "target_core_id"):
            if e.get(k):
                seen.add(e[k])
    return seen - onto_ids


# ─── Provider calls ──────────────────────────────────────────────────────────

def _openai_create_with_retry(client, model, prompt, max_tokens, reasoning_effort):
    from openai import RateLimitError, APIStatusError
    kwargs = dict(model=model, temperature=0, max_tokens=max_tokens,
                  messages=[{"role": "user", "content": prompt}])
    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort
    last = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.chat.completions.create(**kwargs)
        except (RateLimitError, APIStatusError) as exc:
            code = getattr(exc, "status_code", None)
            if code == 429 or isinstance(exc, RateLimitError):
                wait = 20 * (attempt + 1)
                print(f"      429 rate-limited, retry {attempt+1}/{MAX_RETRIES} in {wait}s")
                last = exc
                time.sleep(wait)
                continue
            raise
        content = resp.choices[0].message.content
        if not content:
            det = resp.usage.completion_tokens_details
            raise RuntimeError(
                f"empty content (finish_reason={resp.choices[0].finish_reason}, "
                f"reasoning_tokens={getattr(det, 'reasoning_tokens', '?')})")
        return content
    raise RuntimeError(f"exhausted {MAX_RETRIES} retries: {last}")


def call_cerebras(prompt, model, max_tokens, reasoning_effort):
    from openai import OpenAI
    client = OpenAI(api_key=get_api_key("cerebras"), base_url=CEREBRAS_BASE_URL)
    return _openai_create_with_retry(client, model, prompt, max_tokens, reasoning_effort)


def call_github(prompt, model, max_tokens, reasoning_effort):
    from openai import OpenAI, NotFoundError
    key = get_api_key("github")
    client = OpenAI(api_key=key, base_url=GITHUB_BASE_URL)
    try:
        return _openai_create_with_retry(client, model, prompt, max_tokens, None)
    except NotFoundError:
        # New endpoint/model not found → legacy Azure endpoint + gpt-4o.
        print(f"      404 on {model} @ github.ai — falling back to legacy endpoint + {GITHUB_LEGACY_MODEL}")
        legacy = OpenAI(api_key=key, base_url=GITHUB_LEGACY_BASE_URL)
        return _openai_create_with_retry(legacy, GITHUB_LEGACY_MODEL, prompt, max_tokens, None)


def call_anthropic(prompt, model, max_tokens, reasoning_effort):
    import anthropic
    client = anthropic.Anthropic(api_key=get_api_key("anthropic"))
    last = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.messages.create(
                model=model, max_tokens=max_tokens, temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.RateLimitError as exc:
            wait = 20 * (attempt + 1)
            print(f"      429 rate-limited, retry {attempt+1}/{MAX_RETRIES} in {wait}s")
            last = exc
            time.sleep(wait)
            continue
        parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        content = "".join(parts)
        if not content:
            raise RuntimeError(f"empty content (stop_reason={resp.stop_reason})")
        return content
    raise RuntimeError(f"exhausted {MAX_RETRIES} retries: {last}")


CALLERS = {"cerebras": call_cerebras, "github": call_github, "anthropic": call_anthropic}


# ─── Run ─────────────────────────────────────────────────────────────────────

def run_one(scenario_path, concepts, onto_ids, provider, model, model_dir,
            max_tokens, reasoning_effort):
    scenario = json.loads(scenario_path.read_text("utf-8-sig"))
    sid = scenario["id"]

    # CRITICAL: inject the ontology so build_prompt emits canonical ids.
    scenario["concepts"] = concepts
    prompt = build_prompt(scenario)

    note = None
    try:
        raw = CALLERS[provider](prompt, model, max_tokens, reasoning_effort)
        try:
            state = parse_belief_state(raw)
        except json.JSONDecodeError as exc:
            note = f"parse_error: {exc}"
            print(f"      JSON parse failed: {exc}")
            state = {"nodes": [], "edges": [], "transitions": [], "_raw_head": raw[:500]}
    except Exception as exc:
        # Empty content / exhausted retries: still emit a record so every
        # scenario appears in the table (no silent drop-outs).
        note = f"call_error: {exc}"
        print(f"      call failed: {exc}")
        state = {"nodes": [], "edges": [], "transitions": []}

    gt = scenario["ground_truth"]
    scores = score_state(state, gt)
    foreign = foreign_core_ids(state, onto_ids)

    model_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "spec": "1.0.0",
        "scenario_id": sid,
        "provider": provider,
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "reasoning_effort": reasoning_effort,
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "scores": scores,
        "note": note,
        "foreign_core_ids": sorted(foreign),
        "state": {
            "nodes": state.get("nodes", []),
            "edges": state.get("edges", []),
            "transitions": state.get("transitions", []),
        },
    }
    (model_dir / f"{sid}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")

    return {"scenario_id": sid, "scores": scores, "foreign": foreign,
            "n_edges": len(state.get("edges", [])), "state": state, "gt": gt}


def sanity_report_first(result, onto_ids):
    foreign = result["foreign"]
    print(f"\n  ── Sanity gate (after first scenario: {result['scenario_id']}) ──")
    if foreign:
        print(f"  ⚠ FOREIGN core_ids not in ontology ({len(foreign)}): {sorted(foreign)}")
        print("    → prompt/ontology injection likely did NOT take effect.")
    else:
        print("  ✓ all emitted core_ids ∈ ontology")
    print()


def cer_diagnostic(results):
    print("\n" + "=" * 64)
    print("  ⚠ SANITY GATE: CER == 0.0 on ALL 7 scenarios.")
    print("  Not a silent zero. Either a real model miss or an id desync")
    print("  (the TBG trap). Scene id comparison below:")
    print("=" * 64)
    first = next((r for r in results if r["gt"].get("conflicts")), results[0])
    gt_conflicts = [tuple(c) for c in first["gt"].get("conflicts", [])]
    edge_pairs = [
        (e.get("source_core_id"), e.get("target_core_id"))
        for e in first["state"].get("edges", [])
        if e.get("relation") in ("contradicts", "blocks")
    ]
    print(f"  scenario: {first['scenario_id']}")
    print(f"  gt['conflicts']            : {gt_conflicts}")
    print(f"  emitted conflict edge pairs: {edge_pairs}")
    overlap = set(gt_conflicts) & set(edge_pairs)
    print(f"  overlap                    : {sorted(overlap) or 'NONE — ids do not match'}")
    print("=" * 64 + "\n")


# ─── BASELINES.md ────────────────────────────────────────────────────────────

def _fmt(v) -> str:
    return f"{v:.4f}" if isinstance(v, (int, float)) else "—"


def _load_model_from_disk(model_dir: Path) -> dict:
    """Rebuild a model summary from per-scenario JSONs, with a validity flag
    (valid = the model produced a non-empty graph)."""
    scenarios, prov = [], {}
    for jf in sorted(model_dir.glob("*.json")):
        if jf.name == "summary.json":
            continue
        rec = json.loads(jf.read_text("utf-8"))
        state = rec.get("state", {})
        scenarios.append({
            "scenario_id": rec["scenario_id"],
            "scores": rec.get("scores", {}),
            "valid": len(state.get("nodes", [])) > 0,
        })
        prov = {
            "provider": rec.get("provider", model_dir.name),
            "model": rec.get("model", model_dir.name),
            "temperature": rec.get("temperature", 0),
            "max_tokens": rec.get("max_tokens"),
            "reasoning_effort": rec.get("reasoning_effort"),
            "run_utc": rec.get("run_utc", ""),
        }
    return {"prov": prov, "scenarios": scenarios}


def _model_block(summary: dict) -> str:
    p = summary["prov"]
    rows = []
    # Average only over scenarios that produced a usable graph — otherwise
    # parse-failure zeros (and empty-graph NRS=1.0 artifacts) pollute the mean.
    sums = {m: [] for m in METRICS}
    n_valid = sum(1 for sc in summary["scenarios"] if sc["valid"])
    n_total = len(summary["scenarios"])
    for sc in summary["scenarios"]:
        mark = "" if sc["valid"] else " ⚠"
        cells = []
        for m in METRICS:
            v = sc["scores"].get(m)
            cells.append(_fmt(v))
            if sc["valid"] and isinstance(v, (int, float)):
                sums[m].append(v)
        rows.append(f"| {sc['scenario_id']}{mark} | " + " | ".join(cells) + " |")
    avg_cells = [f"{sum(sums[m])/len(sums[m]):.4f}" if sums[m] else "—" for m in METRICS]
    avg_row = f"| **mean (valid only, n={n_valid})** | " + " | ".join(avg_cells) + " |"

    run_utc = (p.get("run_utc") or "")[:16].replace("T", " ") + " UTC"
    re_str = p.get("reasoning_effort") or "n/a"
    prov_line = (f"**Provider:** {p.get('provider')}  ·  **Model:** `{p.get('model')}`  ·  "
                 f"**Temp:** {p.get('temperature')}  ·  **max_tokens:** {p.get('max_tokens')}  ·  "
                 f"**reasoning_effort:** {re_str}  ·  **Run:** {run_utc}")

    cov_note = ""
    if n_valid < n_total:
        cov_note = (
            f"\n> ⚠ **Coverage: {n_valid}/{n_total} scenarios produced a valid graph.** "
            f"Rows marked ⚠ failed JSON parsing or truncated — their `0.0`/`—` (and any "
            f"`NRS=1.0` from an empty graph) reflect **no usable output, not belief "
            f"tracking**. They are excluded from the mean.\n")

    return f"""### `{p.get('model')}`

{prov_line}
{cov_note}
| Scenario | CER | GCS | BDA | ISS | NRS |
|----------|-----|-----|-----|-----|-----|
{chr(10).join(rows)}
{avg_row}
"""


def write_baselines_md():
    """Aggregate every model under baselines/llm/<model>/ from disk."""
    model_dirs = sorted(d for d in OUT_DIR.glob("*") if d.is_dir())
    summaries = [_load_model_from_disk(d) for d in model_dirs]
    summaries = [s for s in summaries if s["scenarios"]]

    blocks = "\n".join(_model_block(s) for s in summaries)
    md = f"""# DriftBench LLM Baselines

**Spec:** `1.0.0`  ·  Pure LLM baselines over the 7 official v1 scenarios — the
LLM builds the belief graph, scoring uses the canonical `driftbench_core` metrics.
Dash (—) = metric not applicable to that scenario (null).

{blocks}
## Provenance & honesty note

These results were produced through a **convenience runner**
(`adapters/simple/driftbench_run.py` — its `build_prompt` / `parse_belief_state`),
and the metric math is imported unchanged from the canonical `driftbench_core`.
However, this is **NOT** the tamper-checked zero-trust validator: no nonce, no
raw/conv hash chain, no integrity bans. Treat these as **baselines for orientation,
not official certificates**.

Low scores here are **expected headroom** for an early benchmark — they mark the
gap a stronger system is meant to close, not a bug in the harness.

Reasoning models (e.g. `zai-glm-4.7`) spend their token budget on hidden reasoning
and truncate / malform the JSON — hence the coverage caveats. Non-reasoning
instruct models emit valid JSON reliably and are the fair comparison points.
"""
    (ROOT / "baselines" / "BASELINES.md").write_text(md, encoding="utf-8")
    print(f"  Wrote baselines/BASELINES.md ({len(summaries)} model block(s))")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="cerebras",
                    choices=["cerebras", "github", "anthropic"])
    ap.add_argument("--model", default="gpt-oss-120b")
    ap.add_argument("--delay", type=int, default=RPS_DELAY_SECONDS)
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="override; else provider default")
    ap.add_argument("--reasoning-effort", default="__default__",
                    help="override; else provider default (cerebras=low)")
    args = ap.parse_args()

    defaults = PROVIDER_DEFAULTS[args.provider]
    max_tokens = args.max_tokens if args.max_tokens is not None else defaults["max_tokens"]
    reasoning_effort = (defaults["reasoning_effort"]
                        if args.reasoning_effort == "__default__"
                        else (args.reasoning_effort or None))

    concepts, onto_ids = load_ontology()
    model_dir = OUT_DIR / model_slug(args.model)

    print(f"\n  DriftBench LLM baseline — provider={args.provider}, model={args.model}, temp=0")
    print(f"  max_tokens={max_tokens}, reasoning_effort={reasoning_effort or 'n/a'}")
    print(f"  output → {model_dir.relative_to(ROOT)}\n")

    results = []
    for i, fname in enumerate(SCENARIO_FILES):
        path = SCEN_DIR / fname
        print(f"  [{i+1}/{len(SCENARIO_FILES)}] {fname} ...", flush=True)
        try:
            r = run_one(path, concepts, onto_ids, args.provider, args.model,
                        model_dir, max_tokens, reasoning_effort)
        except Exception as exc:
            import traceback
            print(f"      ERROR: {exc}")
            traceback.print_exc()
            r = {"scenario_id": path.stem, "scores": {m: None for m in METRICS},
                 "foreign": set(), "n_edges": 0, "state": {}, "gt": {}}
        s = r["scores"]
        print(f"      CER={_fmt(s['CER'])} GCS={_fmt(s['GCS'])} BDA={_fmt(s['BDA'])} "
              f"ISS={_fmt(s['ISS'])} NRS={_fmt(s['NRS'])}  edges={r.get('n_edges')}")
        results.append(r)

        if i == 0:
            sanity_report_first(r, onto_ids)
        if i < len(SCENARIO_FILES) - 1:
            time.sleep(args.delay)

    cer_vals = [r["scores"].get("CER") for r in results]
    if all(v == 0.0 for v in cer_vals if v is not None) and any(v is not None for v in cer_vals):
        cer_diagnostic(results)

    write_baselines_md()
    print(f"\n  Done. Per-scenario JSON → {model_dir.relative_to(ROOT)}/  ·  summary → baselines/BASELINES.md\n")


if __name__ == "__main__":
    main()
