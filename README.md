# Agent Architecture Testbed: Single Agent vs. Multi-Agent Pipeline

A fully-synthetic testbed, built on the [fair_llm](fair_llm/) (`fairlib`)
agent framework, for comparing a single ReAct agent against a decomposed
multi-agent pipeline on a small multi-step "pivot" scenario.

**No real network access, no real exploits, no cyber connectivity.** Every
tool result is a hardcoded, deterministic lookup in
`offensive_cyber/toy_network.py`. This is a fixed design constraint of the
project, not a placeholder — do not wire any tool up to a live host,
socket, or subprocess.

## Why this scenario

The toy network requires a genuine multi-step chain:

```
list_subnet -> nmap_scan -> service_banner -> vuln_lookup -> run_exploit
   (yields credentials + a NEW hidden host) -> ssh_login -> flag
```

Host C (`10.0.0.15`) is invisible until Host B is exploited. This forces
a "pivot," which is the structurally interesting part: does splitting into
Recon / Analyst / Exploit sub-agents help an LLM manage this better than
one continuous ReAct loop, or does the hand-off overhead hurt more than it
helps? That's the question this testbed is built to measure.

## Layout

```
OffensiveCyber/
├── experiment_runner.py     # entry point: runs trials, writes results.jsonl
├── .env.example             # copy to .env and edit — all config lives here
├── results.jsonl            # experiment output (generated, gitignored)
├── offensive_cyber/         # the project package
│   ├── toy_network.py       # the scenario + every mock tool's hardcoded response
│   ├── cyber_tools/         # fairlib Tool wrappers around toy_network.py
│   ├── single_agent.py      # SimpleAgent + ReActPlanner, all tools at once
│   ├── multi_agent.py       # ManagerPlanner + HierarchicalAgentRunner, 3 workers
│   ├── live_logging.py      # console logging of each step/tool call as it happens
│   └── trace_utils.py       # shared trace -> tool-log / flag-check helpers
├── tests/                   # ad hoc smoke tests (see below)
└── fair_llm/                # the agent framework itself, vendored as a separate repo
```

- `offensive_cyber/toy_network.py` — the scenario and every mock tool's
  hardcoded responses (`TOOL_REGISTRY`, `TOOL_DESCRIPTIONS`). Read this
  first; it's the entire fake sandbox.
- `offensive_cyber/cyber_tools/` — fairlib `Tool` wrappers around
  `toy_network.py`'s fake responses (`ListSubnetTool`, `NmapScanTool`,
  `ServiceBannerTool`, `VulnLookupTool`, `RunExploitTool`, `SSHLoginTool`).
  This is the only place tool schemas live; the underlying data never
  leaves `toy_network.py`.
- `offensive_cyber/single_agent.py` — one fairlib `SimpleAgent` with a
  `ReActPlanner` and all six tools available at once.
- `offensive_cyber/multi_agent.py` — a fairlib `ManagerPlanner` +
  `HierarchicalAgentRunner` coordinating three worker agents (Recon,
  Analyst, Exploit), each restricted to a subset of tools.
- `offensive_cyber/live_logging.py` — subscribes a `logging.Logger` to
  fairlib's event bus so you see each ReAct step and tool call printed to
  the console as it happens, not just after the run finishes.
- `experiment_runner.py` — runs N trials of each architecture through
  fairlib's `OllamaAdapter` or `HuggingFaceAdapter`, logs one JSON record
  per trial to `results.jsonl`, and prints a summary.
- `fair_llm/` — the agent framework itself (a separate git repo, vendored
  here). Framework changes belong there, not in this project.

## Quickstart

```bash
pip install -r requirements.txt          # optional backend clients
pip install -r fair_llm/requirements.txt # fairlib's own dependencies

cp .env.example .env                     # then edit .env to taste
python experiment_runner.py
```

All configuration lives in `.env` (see `.env.example` for every option,
documented inline) — there are no command-line flags. The main knobs:

- `BACKEND` — `ollama` (a local model already pulled via `ollama pull`) or
  `huggingface` (a local `transformers` model, downloaded on first use —
  see `HF_AUTH_TOKEN`/`HF_QUANTIZED` in `.env.example` for gated/quantized
  models).
- `MODEL` — the Ollama tag or HuggingFace alias/repo id to use.
- `TRIALS` — how many trials to run per architecture.
- `ARCHITECTURE` — `single`, `multi`, or `both`.
- `LOG_LEVEL` — `DEBUG` for maximum step-by-step detail, `INFO` (default),
  or `WARNING` for a quiet run.

For `BACKEND=ollama`, `MODEL` must name a model Ollama already has pulled
locally, or every call 404s at `/api/chat` (Ollama's real response for an
unknown model, not a fairlib error) — check with `ollama list` /
`ollama pull <model>` first.

While a trial runs, `live_logging.py` prints each agent step and tool call
to the console in real time (tagged `[single]` or `[multi]`); set
`LOG_LEVEL=DEBUG` in `.env` for more detail. Results still land in
`results.jsonl`, one record per trial with full step-by-step logs, and
each trial's complete structured trace is saved to `TRACE_DIR` — that's
the raw data for analysis (pandas, notebooks, whatever's useful).

Ad hoc smoke tests live in `tests/test_cyber_tools.py`,
`tests/test_single_agent.py`, and `tests/test_multi_agent.py`;
`python tests/run_tests.py` (run from the repo root) runs all three in
sequence.

## Suggested first experiment

1. Run both architectures for ~20 trials each against the same model.
2. Compare: success rate, steps-to-success, tool-call count, wall-clock time.
3. Read the full logs on any pipeline failures — is the Analyst agent
   losing recon context? Is the single agent confusing which host it
   already scanned? This qualitative pass is often more informative than
   the aggregate numbers at this scale.
