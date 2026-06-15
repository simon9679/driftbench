#!/usr/bin/env python3
"""
DriftBench Universal Runner
============================
Runs any LLM through DriftBench scenarios and outputs deterministic scores.

Supported providers:
  --provider openai     (GPT-4o, GPT-4-turbo, etc.)
  --provider anthropic  (Claude Sonnet/Opus/Haiku)
  --provider gemini     (Gemini 1.5 Pro/Flash)
  --provider custom     (any OpenAI-compatible endpoint)

Setup:
  pip install openai            # for openai / custom
  pip install anthropic         # for anthropic
  pip install google-generativeai  # for gemini

  export OPENAI_API_KEY=sk-...
  python driftbench_run.py --provider openai --model gpt-4o

  export ANTHROPIC_API_KEY=sk-ant-...
  python driftbench_run.py --provider anthropic --model claude-sonnet-4-20250514

  export GEMINI_API_KEY=...
  python driftbench_run.py --provider gemini --model gemini-1.5-pro

  # Custom endpoint (LM Studio, Ollama, vLLM):
  python driftbench_run.py --provider custom --base-url http://localhost:1234/v1 --model llama3

NOTE
  This is an unofficial convenience runner for quickly scoring any LLM. All
  metric math is imported from driftbench_core (single source of truth), so the
  scores match the canonical engine exactly. The two built-in scenarios use
  free-form concept ids for illustration and are NOT bound to the frozen v1
  ontology. For official, tamper-checked evaluation use the zero-trust validator:

      driftbench-validate --sub submission.json \\
          --scen standard/v1/scenarios/01_burnout_to_founder.json --nonce YOUR_NONCE
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Single source of truth: scoring and hashing come from driftbench_core,
# never reimplemented here. Insert repo root so this runs without `pip install`.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from driftbench_core.core import (  # noqa: E402
    hash_turn,
    compute_cer,
    compute_gcs,
    compute_bda,
    compute_iss,
    compute_nrs,
)


# ─── Built-in scenarios ──────────────────────────────────────────────────────

SCENARIOS = {
    "burnout_to_founder": {
        "id": "01_burnout_to_founder",
        "messages": [
            {"turn": 1, "user": "I feel completely burned out. This corporate job is killing me.",
             "assistant": "That sounds exhausting. What's been the hardest part for you?"},
            {"turn": 2, "user": "I have this side project — an app idea I believe in. I want to go all in on it.",
             "assistant": "That excitement comes through clearly. What's holding you back right now?"},
            {"turn": 3, "user": "Actually, my manager just offered me a big promotion. More money, more responsibility.",
             "assistant": "That's a significant development. How do you feel about it given what you just said?"},
            {"turn": 4, "user": "I don't care about the promotion. I've decided — I'm quitting to build my startup.",
             "assistant": "That's a major decision. What made you certain enough to cross that line?"},
            {"turn": 5, "user": "I handed in my resignation today. I'm a founder now, not an employee.",
             "assistant": "That's a huge leap. Congratulations on taking that step."},
        ],
        "ground_truth": {
            "conflicts": [["job_commitment", "founder_vision"]],
            "belief_changes": [
                {"core_id": "job_satisfaction", "direction": "down"},
                {"core_id": "founder_vision", "direction": "up"},
                {"core_id": "job_commitment", "direction": "up_then_down"},
            ],
            "identity_shift": {"from_id": "employee_identity", "to_id": "founder_identity"},
            "noise_turns": [],
        },
        "concepts": {
            "job_satisfaction": "how fulfilling the current job feels",
            "founder_vision": "belief strength in own startup idea",
            "job_commitment": "commitment to staying at the corporate job (spikes at promotion, then collapses)",
            "employee_identity": "identity as a corporate employee (dominant at start, recedes by end)",
            "founder_identity": "identity as an entrepreneur/founder (emerges and overtakes by end)",
        },
    },
    "grief_to_acceptance": {
        "id": "02_grief_to_acceptance",
        "messages": [
            {"turn": 1, "user": "My dog passed away last week. I just can't stop thinking about him.",
             "assistant": "I'm so sorry. Grief like that takes time. What was he like?"},
            {"turn": 2, "user": "He was my best friend for 12 years. My apartment feels empty now.",
             "assistant": "Twelve years is a real relationship. That emptiness makes complete sense."},
            {"turn": 3, "user": "I've been looking at rescue dogs online. I feel guilty about it.",
             "assistant": "Guilt is a common part of this. What does the guilt feel like for you?"},
            {"turn": 4, "user": "Like I'm replacing him. But also... I have so much love to give.",
             "assistant": "Both things can be true at once. That's not betrayal — that's love looking for a home."},
            {"turn": 5, "user": "I put in an adoption application today. I think he would have wanted that.",
             "assistant": "That sounds like a meaningful step forward."},
        ],
        "ground_truth": {
            "conflicts": [["loyalty_to_past", "openness_to_new"]],
            "belief_changes": [
                {"core_id": "grief_intensity", "direction": "down"},
                {"core_id": "openness_to_new", "direction": "up"},
                {"core_id": "loyalty_to_past", "direction": "up_then_down"},
            ],
            "identity_shift": {"from_id": "bereaved_identity", "to_id": "caregiver_identity"},
            "noise_turns": [],
        },
        "concepts": {
            "grief_intensity": "strength of active grief and loss (starts high, softens)",
            "openness_to_new": "willingness to move forward and embrace new connections",
            "loyalty_to_past": "felt obligation to the past (spikes when looking at dogs, then released)",
            "bereaved_identity": "identity defined by loss (dominant at start)",
            "caregiver_identity": "identity as someone with love to give (emerges by end)",
        },
    },
}


# ─── Scoring & hashing ──────────────────────────────────────────────────────
# Imported from driftbench_core.core (see top of file). This runner never
# reimplements metric logic — it is a thin convenience wrapper so the numbers it
# prints are byte-for-byte the canonical DriftBench scores.


# ─── Prompt builder ─────────────────────────────────────────────────────────

def build_prompt(scenario: Dict) -> str:
    messages = scenario["messages"]
    concepts = scenario.get("concepts", {})

    conv = "\n\n".join(
        f"Turn {m['turn']}:\nUser: {m['user']}\nAssistant: {m['assistant']}"
        for m in messages
    )

    hashes = {
        m["turn"]: hash_turn(m["turn"], m["user"], m["assistant"])
        for m in messages
    }
    hash_list = "\n".join(f'  turn_{t}: "{h}"' for t, h in sorted(hashes.items()))

    concept_list = "\n".join(f"- {k}: {v}" for k, v in concepts.items())
    concept_names = list(concepts.keys())
    n_concepts = len(concept_names)

    example_node = concept_names[0] if concept_names else "concept_a"
    example_node2 = concept_names[1] if len(concept_names) > 1 else "concept_b"

    return f"""You are a DriftBench Belief Graph extraction engine.

Analyze the conversation and output ONLY a single valid JSON object. No markdown, no prose, no backticks.

=== CONVERSATION ===
{conv}

=== CONCEPTS TO TRACK ===
{concept_list}

=== TURN HASHES — copy these VERBATIM into text_hash / trigger_text_hash ===
{hash_list}

=== OUTPUT FORMAT ===
{{
  "nodes": [
    {{ "id": "n1", "label": "...", "core_id": "{example_node}", "mapping_confidence": 0.95, "confidence": 0.15, "evidence_turn": 1, "text_hash": "<exact hash for evidence_turn>" }}
  ],
  "edges": [
    {{ "source_id": "n1", "target_id": "n2", "source_core_id": "{example_node}", "target_core_id": "{example_node2}", "relation": "contradicts", "created_at_turn": 3, "evidence_turn": 3, "text_hash": "<exact hash for turn 3>" }}
  ],
  "transitions": [
    {{ "node_id": "n1", "core_id": "{example_node}", "turn": 1, "delta": -0.25, "trigger_text_hash": "<exact hash for turn 1>" }}
  ]
}}

=== CONSTRAINTS ===
1. Exactly {n_concepts} nodes — one per concept: {', '.join(concept_names)}
2. confidence = FINAL belief strength after all turns [0.0–1.0]
3. All delta values in [-0.4, 0.4], non-zero only for meaningful changes
4. mapping_confidence >= 0.7 for all nodes
5. Create edges for conceptual conflicts (use relation "contradicts" or "blocks")
6. Emit transitions for every meaningful belief change across all turns
7. text_hash and trigger_text_hash must be copied EXACTLY from the hash table above
8. Output ONLY the JSON object, nothing else"""


# ─── LLM providers ──────────────────────────────────────────────────────────

def call_openai(prompt: str, model: str, base_url: Optional[str] = None) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("pip install openai")

    kwargs = {"api_key": os.environ.get("OPENAI_API_KEY", "sk-placeholder")}
    if base_url:
        kwargs["base_url"] = base_url

    client = OpenAI(**kwargs)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=3000,
    )
    return resp.choices[0].message.content


def call_anthropic(prompt: str, model: str) -> str:
    try:
        import anthropic
    except ImportError:
        sys.exit("pip install anthropic")

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
    resp = client.messages.create(
        model=model,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def call_gemini(prompt: str, model: str) -> str:
    try:
        import google.generativeai as genai
    except ImportError:
        sys.exit("pip install google-generativeai")

    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", ""))
    m = genai.GenerativeModel(model)
    resp = m.generate_content(
        prompt,
        generation_config={"temperature": 0.1, "max_output_tokens": 3000},
    )
    return resp.text


def call_llm(prompt: str, provider: str, model: str, base_url: Optional[str]) -> str:
    if provider == "openai":
        return call_openai(prompt, model)
    elif provider == "anthropic":
        return call_anthropic(prompt, model)
    elif provider == "gemini":
        return call_gemini(prompt, model)
    elif provider == "custom":
        return call_openai(prompt, model, base_url=base_url)
    else:
        sys.exit(f"Unknown provider: {provider}")


# ─── Response parsing ───────────────────────────────────────────────────────

def parse_belief_state(raw: str) -> Dict:
    clean = raw.strip()
    # Strip markdown fences if the model added them despite instructions
    for fence in ("```json", "```"):
        if clean.startswith(fence):
            clean = clean[len(fence):]
    if clean.endswith("```"):
        clean = clean[:-3]
    return json.loads(clean.strip())


def check_hashes(state: Dict, scenario: Dict) -> Tuple[int, int]:
    messages = scenario["messages"]
    hashes = {m["turn"]: hash_turn(m["turn"], m["user"], m["assistant"]) for m in messages}
    total = 0
    fails = 0
    for n in state.get("nodes", []):
        t = n.get("evidence_turn")
        if t in hashes:
            total += 1
            if n.get("text_hash") != hashes[t]:
                fails += 1
    for tr in state.get("transitions", []):
        t = tr.get("turn")
        if t in hashes:
            total += 1
            if tr.get("trigger_text_hash") != hashes[t]:
                fails += 1
    return fails, total


# ─── Output formatting ──────────────────────────────────────────────────────

def fmt(v: Optional[float]) -> str:
    return f"{v:.4f}" if v is not None else "  N/A "


BAR_WIDTH = 30

def bar(v: Optional[float]) -> str:
    if v is None:
        return " " * BAR_WIDTH
    filled = int(round(v * BAR_WIDTH))
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def color(v: Optional[float]) -> str:
    if v is None:
        return "\033[90m"
    if v >= 0.8:
        return "\033[92m"
    if v >= 0.5:
        return "\033[93m"
    return "\033[91m"


RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"
CYAN  = "\033[96m"
BLUE  = "\033[94m"


def print_results(scores: Dict, state: Dict, scenario: Dict, hash_fails: int, hash_total: int,
                  provider: str, model: str):
    print()
    print(f"{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  DriftBench Results{RESET}  {DIM}{provider} / {model}{RESET}")
    print(f"  Scenario: {scenario['id']}")
    print(f"{'─'*60}{RESET}")
    print()

    metric_desc = {
        "CER": "Conflict Edge Recovery  — found the right conflicts?",
        "GCS": "Graph Causal Score      — conflicts caused belief drops?",
        "BDA": "Belief Drift Accuracy   — beliefs moved right directions?",
        "ISS": "Identity Shift Score    — new identity overtook old one?",
        "NRS": "Noise Resistance Score  — stable on irrelevant turns?",
    }

    for k, v in scores.items():
        c = color(v)
        print(f"  {BOLD}{k}{RESET}  {c}{fmt(v)}{RESET}  {c}{bar(v)}{RESET}")
        print(f"       {DIM}{metric_desc[k]}{RESET}")
        print()

    # Aggregate score: simple mean of non-null metrics
    valid_scores = [v for v in scores.values() if v is not None]
    if valid_scores:
        agg = sum(valid_scores) / len(valid_scores)
        c = color(agg)
        print(f"  {BOLD}AGG{RESET}  {c}{fmt(agg)}{RESET}  {DIM}(mean of {len(valid_scores)} metrics){RESET}")
        print()

    print(f"{'─'*60}")

    # Final belief state table
    nodes = state.get("nodes", [])
    if nodes:
        print(f"\n  {BOLD}Final Belief State:{RESET}")
        for n in sorted(nodes, key=lambda x: x.get("confidence", 0), reverse=True):
            cid = n.get("core_id", n.get("label", "?"))
            conf = n.get("confidence", 0.0)
            c = color(conf)
            filled = int(round(conf * 20))
            b = "█" * filled + "░" * (20 - filled)
            print(f"  {c}{b}{RESET}  {conf:.2f}  {DIM}{cid}{RESET}")

    # Transitions log
    transitions = state.get("transitions", [])
    if transitions:
        print(f"\n  {BOLD}Transitions ({len(transitions)}):{RESET}")
        for tr in sorted(transitions, key=lambda x: x.get("turn", 0)):
            d = tr.get("delta", 0)
            sign = "+" if d > 0 else ""
            c = "\033[92m" if d > 0 else "\033[91m"
            print(f"  {DIM}t{tr.get('turn')}{RESET}  {tr.get('core_id', '?'):<28}  {c}{sign}{d:.3f}{RESET}")

    # Conflict edge summary
    edges = state.get("edges", [])
    conflict_edges = [e for e in edges if e.get("relation") in ("blocks", "contradicts")]
    if conflict_edges:
        print(f"\n  {BOLD}Conflict Edges:{RESET}")
        for e in conflict_edges:
            print(f"  {e.get('source_core_id','?')}  ──[{e.get('relation')}]──▶  {e.get('target_core_id','?')}  {DIM}@t{e.get('created_at_turn')}{RESET}")

    # Hash integrity report
    print()
    if hash_fails == 0:
        print(f"  {BOLD}\033[92m✓{RESET} Hash integrity: all {hash_total} hashes verified")
    else:
        print(f"  {BOLD}\033[91m✗{RESET} Hash integrity: {hash_fails}/{hash_total} mismatches")
        print(f"    {DIM}(model did not copy hashes verbatim — scores still computed){RESET}")

    print(f"{'─'*60}\n")


# ─── Save results to JSON ───────────────────────────────────────────────────

def save_results(scores: Dict, state: Dict, scenario: Dict, provider: str, model: str,
                 out_path: str):
    result = {
        "spec": "1.0.0",
        "provider": provider,
        "model": model,
        "scenario_id": scenario["id"],
        "scores": {k: (float(f"{v:.4f}") if v is not None else None) for k, v in scores.items()},
        "nodes": state.get("nodes", []),
        "edges": state.get("edges", []),
        "transitions": state.get("transitions", []),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  Saved → {out_path}\n")


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DriftBench Universal Runner — evaluate any LLM on belief drift",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python driftbench_run.py --provider openai --model gpt-4o
  python driftbench_run.py --provider anthropic --model claude-sonnet-4-20250514
  python driftbench_run.py --provider gemini --model gemini-1.5-pro
  python driftbench_run.py --provider custom --base-url http://localhost:1234/v1 --model llama3
  python driftbench_run.py --provider openai --model gpt-4o --scenario grief_to_acceptance
  python driftbench_run.py --provider openai --model gpt-4o --scenario-file my_scenario.json
        """,
    )
    parser.add_argument("--provider", required=True,
                        choices=["openai", "anthropic", "gemini", "custom"],
                        help="LLM provider")
    parser.add_argument("--model", required=True, help="Model name")
    parser.add_argument("--scenario", default="burnout_to_founder",
                        choices=list(SCENARIOS.keys()),
                        help="Built-in scenario to run (default: burnout_to_founder)")
    parser.add_argument("--scenario-file", type=str, default=None,
                        help="Path to custom scenario JSON file")
    parser.add_argument("--base-url", type=str, default=None,
                        help="Custom base URL for OpenAI-compatible endpoints")
    parser.add_argument("--out", type=str, default=None,
                        help="Save results to JSON file")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable ANSI colors")
    args = parser.parse_args()

    # Load scenario
    if args.scenario_file:
        with open(args.scenario_file, "r", encoding="utf-8-sig") as f:
            scenario = json.load(f)
        print(f"\n  Loading scenario from {args.scenario_file}")
    else:
        scenario = SCENARIOS[args.scenario]
        print(f"\n  Using built-in scenario: {args.scenario}")

    if args.no_color:
        global RESET, BOLD, DIM, CYAN, BLUE
        RESET = BOLD = DIM = CYAN = BLUE = ""

    print(f"  Provider: {args.provider}  |  Model: {args.model}")
    print(f"  Turns: {len(scenario['messages'])}")
    print()

    # Build prompt
    prompt = build_prompt(scenario)

    # Call LLM
    print("  Sending to LLM...", end="", flush=True)
    try:
        raw = call_llm(prompt, args.provider, args.model, args.base_url)
    except Exception as e:
        print(f"\n  ERROR calling LLM: {e}")
        sys.exit(1)
    print(" done")

    # Parse response
    print("  Parsing belief state...", end="", flush=True)
    try:
        state = parse_belief_state(raw)
    except json.JSONDecodeError as e:
        print(f"\n  ERROR parsing JSON: {e}")
        print(f"\n  Raw output (first 500 chars):\n{raw[:500]}")
        sys.exit(1)
    print(f" done ({len(state.get('nodes',[]))} nodes, {len(state.get('edges',[]))} edges, {len(state.get('transitions',[]))} transitions)")

    # Hash integrity check
    hash_fails, hash_total = check_hashes(state, scenario)

    # Compute scores
    gt = scenario["ground_truth"]
    scores = {
        "CER": compute_cer(state.get("edges", []), gt.get("conflicts", [])),
        "GCS": compute_gcs(state.get("edges", []), state.get("transitions", [])),
        "BDA": compute_bda(state.get("transitions", []), gt.get("belief_changes", [])),
        "ISS": compute_iss(state.get("nodes", []), gt.get("identity_shift", {})),
        "NRS": compute_nrs(state.get("transitions", []), gt),
    }

    # Print results
    print_results(scores, state, scenario, hash_fails, hash_total, args.provider, args.model)

    # Optionally save to JSON
    if args.out:
        save_results(scores, state, scenario, args.provider, args.model, args.out)

    return scores


if __name__ == "__main__":
    main()
