# Agent Architecture Scaffold: Single ReAct vs. Multi-Agent Pipeline

A minimal, fully-synthetic testbed for comparing a single ReAct agent
against a decomposed multi-agent pipeline on a small multi-step
"pivot" scenario. **No real network access, no real exploits** — every
tool is a deterministic dictionary lookup in `toy_network.py`.

## Why this scenario

The toy network requires a genuine multi-step chain:

```
list_subnet -> nmap_scan -> service_banner -> vuln_lookup -> run_exploit
   (yields credentials + a NEW hidden host) -> ssh_login -> flag
```

Host C (`10.0.0.15`) is invisible until Host B is exploited. This forces
a "pivot," which is the structurally interesting part: does splitting
into Recon / Analyst / Exploit sub-agents help an LLM manage this better
than one continuous ReAct loop, or does the hand-off overhead hurt more
than it helps? That's the question this scaffold is built to measure.

## Files

- `toy_network.py` — the scenario + all mock tools. Read this first.
- `llm_client.py` — pluggable model backend (mock / Ollama / Anthropic).
- `react_agent.py` — single-agent ReAct loop, all tools available at once.
- `multi_agent_pipeline.py` — Recon -> Analyst -> Exploit sub-agents with
  a shared context string, looping back to Recon on a pivot.
- `experiment_runner.py` — runs N trials of each architecture, logs to
  JSONL, prints a quick summary.

## Quickstart

```bash
pip install -r requirements.txt   # only needed for ollama/anthropic backends

# 1. Validate the harness with zero model calls (scripted fake LLM):
python experiment_runner.py --trials 2 --backend mock --verbose

# 2. Point it at a local Ollama model:
python experiment_runner.py --trials 10 --backend ollama --model qwen2.5:14b

# 3. Or the Anthropic API (requires ANTHROPIC_API_KEY):
python experiment_runner.py --trials 10 --backend anthropic --model claude-sonnet-4-6
```

Results land in `results.jsonl`, one record per trial, with full step-by-step
logs — that's your raw data for analysis (pandas, notebooks, whatever the
team prefers).

## What "MVP" means here — and what's deliberately left undone

This is a launching pad, not a finished experiment harness. Things I'd
expect the team to change almost immediately:

- **Action parsing is regex-based**, not structured tool-calling. Fine for
  getting started and for models without good function-calling support,
  but fragile — a natural first improvement, and a good discussion of
  *why* parsing failures are themselves a research-relevant failure mode.
- **No retry/backoff, no cost or token tracking.** Add these once you're
  running real trials — you'll want tokens-per-run as a metric alongside
  steps and tool calls.
- **The scenario has no decoys or red herrings.** Right now a careful
  agent can't really go wrong. Consider adding a near-miss service version
  on Host A (looks vulnerable, isn't) once you want to study failure modes,
  not just success/steps.
- **`max_cycles` / `max_steps` are arbitrary.** Tune based on what you
  observe — if the multi-agent pipeline is timing out on cycle limits
  while ReAct isn't, that's itself a finding.
- **The shared "context" between pipeline stages is a flat string.**
  A more structured blackboard (typed JSON state) would be a reasonable
  semester-1 upgrade and would make failure analysis much easier.

## Suggested first experiment

1. Run both architectures for ~20 trials each against the same local model,
   varying temperature if your backend supports it.
2. Compare: success rate, steps-to-success, tool-call count, wall-clock time.
3. Read the full logs on any pipeline failures — is the Analyst agent
   losing recon context? Is ReAct getting confused about which host it
   already scanned? This qualitative pass is often more informative than
   the aggregate numbers at this scale.
4. Once you're comfortable, add the decoy service and re-run — does the
   ranking between architectures change under noise?

That comparison (with real numbers and failure examples) is a solid
starting point for the semester-1 writeup, independent of anything the
sandboxed/real-tool track does later.
