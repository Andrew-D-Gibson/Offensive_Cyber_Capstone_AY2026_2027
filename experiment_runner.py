"""
experiment_runner.py

Runs N trials of each architecture and writes one JSON record per trial to
a JSONL log file, then prints a quick summary.
"""

import argparse
import asyncio
import json
import statistics
from pathlib import Path
from datetime import datetime

from fairlib import OllamaAdapter, AnthropicAdapter, PlannerParseError, ToolInvocationError, MaxStepsExceeded

from offensive_cyber.single_agent import run_single_cyber_agent
from offensive_cyber.multi_agent import run_multi_cyber_agent


def build_llm(backend: str, model: str):
    if backend == "mock":
        raise NotImplementedError("Mock LLM not yet supported with FAIR-LLM adapters")
    elif backend == "ollama":
        return OllamaAdapter(model_name=model)
    elif backend == "anthropic":
        return AnthropicAdapter(model_name=model)
    else:
        raise ValueError(f"unknown backend '{backend}'")


async def run_single_agent_trial(llm, verbose: bool):
    try:
        result = await run_single_cyber_agent(query="Begin. Find the flag.", max_steps=15, verbose=verbose)
        return result
    except (PlannerParseError, ToolInvocationError, MaxStepsExceeded) as e:
        return {
            "architecture": "single_react_fairlib",
            "success": False,
            "steps": 0,
            "tool_calls": 0,
            "wall_time_sec": 0,
            "claimed_flag": None,
            "log": [],
            "error_type": type(e).__name__,
            "error": str(e),
        }


async def run_multi_agent_trial(llm, verbose: bool):
    try:
        result = await run_multi_cyber_agent(query="Begin offensive security mission.", verbose=verbose)
        return result
    except (PlannerParseError, ToolInvocationError, MaxStepsExceeded) as e:
        return {
            "architecture": "multi_agent_fairlib",
            "success": False,
            "steps": 0,
            "tool_calls": 0,
            "wall_time_sec": 0,
            "claimed_flag": None,
            "log": [],
            "error_type": type(e).__name__,
            "error": str(e),
        }


def summarize(results: list, label: str):
    successes = [r for r in results if r["success"]]
    n = len(results)
    print(f"\n=== {label} ({n} trials) ===")
    print(f"Success rate: {len(successes)}/{n} ({100*len(successes)/n:.0f}%)")
    if successes:
        steps = [r["steps"] for r in successes]
        calls = [r["tool_calls"] for r in successes]
        times = [r["wall_time_sec"] for r in successes]
        print(f"  Avg steps (successful runs): {statistics.mean(steps):.1f}")
        print(f"  Avg tool calls (successful runs): {statistics.mean(calls):.1f}")
        print(f"  Avg wall time (successful runs): {statistics.mean(times):.3f}s")
    error_types = {}
    for r in results:
        if "error_type" in r:
            et = r["error_type"]
            error_types[et] = error_types.get(et, 0) + 1
    if error_types:
        print("  Errors:")
        for et, count in error_types.items():
            print(f"    {et}: {count}")


async def main():
    parser = argparse.ArgumentParser(description="Run FAIR-LLM cyber experiments")
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--backend", choices=["mock", "ollama", "anthropic"], default="ollama")
    parser.add_argument("--model", default="qwen2.5:14b")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--out", default="results.jsonl")
    parser.add_argument("--single", action="store_true", help="Run only single agent")
    parser.add_argument("--multi", action="store_true", help="Run only multi-agent")
    args = parser.parse_args()

    if args.single and args.multi:
        print("Error: Cannot specify both --single and --multi")
        return

    architectures = []
    if args.single:
        architectures = ["single_react"]
    elif args.multi:
        architectures = ["multi_agent"]
    else:
        architectures = ["single_react", "multi_agent"]

    all_results = []
    start_time = datetime.now()

    for architecture in architectures:
        print(f"\n--- Running {architecture} with {args.backend} backend ---")
        llm = build_llm(args.backend, args.model)
        results = []
        for i in range(args.trials):
            print(f"Trial {i+1}/{args.trials}...")
            if architecture == "single_react":
                result = await run_single_agent_trial(llm, verbose=args.verbose)
            else:
                result = await run_multi_agent_trial(llm, verbose=args.verbose)
            result["trial"] = i
            result["timestamp"] = datetime.now().isoformat()
            results.append(result)
        all_results.extend(results)
        summarize(results, f"{architecture} ({args.backend})")

    elapsed = (datetime.now() - start_time).total_seconds()
    out_path = Path(args.out)
    with out_path.open("w") as f:
        for r in all_results:
            f.write(json.dumps(r) + "\n")
    print(f"\n{'='*50}")
    print(f"Completed {len(all_results)} trials in {elapsed:.1f}s")
    print(f"Wrote {len(all_results)} trial records to {out_path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
