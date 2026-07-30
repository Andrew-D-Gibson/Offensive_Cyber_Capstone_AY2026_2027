# Offensive Cyber Agent: a minimal ReAct testbed

A small, fully-synthetic ReAct agent that has to chain six tool calls
through a fake "pivot" scenario to find a flag. Built to be readable
top-to-bottom by anyone new to LLM agents.

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

Host C (`10.0.0.15`) is invisible until Host B is exploited, forcing a
"pivot" — the model has to read tool output carefully and copy values
verbatim across several steps rather than guessing.

## Layout

```
OffensiveCyber/
├── experiment_runner.py     # entry point: builds the LLM, runs the agent once
├── .env.example              # copy to .env and edit — all config lives here
├── offensive_cyber/          # the project package
│   ├── toy_network.py        # the scenario + every mock tool's hardcoded response
│   ├── agent.py               # the whole ReAct loop: prompt, parse, call tool, repeat
│   └── live_logging.py       # console logging setup
├── tests/                    # ad hoc smoke tests (see below)
└── fair_llm/                 # vendored agent framework — only its two LLM
                               # adapters (Ollama, HuggingFace) are used here
```

- `offensive_cyber/toy_network.py` — the scenario and every mock tool's
  hardcoded response (`TOOL_REGISTRY`: name → plain function,
  `TOOL_DESCRIPTIONS`: name → one-line description). Read this first; it's
  the entire fake sandbox.
- `offensive_cyber/agent.py` — the whole agent. One `run_agent(llm, task)`
  function: builds a system prompt from `TOOL_DESCRIPTIONS`, then loops —
  ask the model for a JSON `{tool_name, tool_input}` action, call the
  matching function in `TOOL_REGISTRY`, feed the result back as the next
  message — until the model calls `final_answer` or `max_steps` runs out.
  No planner/executor/memory classes; it's a list of messages and a
  `while` loop.
- `offensive_cyber/live_logging.py` — one `configure_logging()` call; every
  step, tool call, and observation is logged directly from `agent.py` as it
  happens.
- `experiment_runner.py` — reads `.env`, builds an `OllamaAdapter` or
  `HuggingFaceAdapter` from `fairlib`, calls `run_agent()` once, prints a
  summary.
- `fair_llm/` — the vendored agent framework this project is based on. We
  reuse exactly two things from it: `OllamaAdapter` and `HuggingFaceAdapter`
  (both know how to talk to a chat model given a list of messages). Nothing
  else from it is used — no planner, no tool registry, no event bus.
  Framework changes belong in that repo, not here.

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
- `MAX_STEPS` — how many ReAct steps the agent gets before giving up.
- `LOG_LEVEL` — `DEBUG` for maximum step-by-step detail, `INFO` (default),
  or `WARNING` for a quiet run.

For `BACKEND=ollama`, `MODEL` must name a model Ollama already has pulled
locally, or every call 404s at `/api/chat` — check with `ollama list` /
`ollama pull <model>` first.

Every step, tool call, and observation prints to the console as it
happens — tagged with the step number so you can follow the model's
reasoning live, not just see a final summary line.

Ad hoc smoke tests live in `tests/test_cyber_tools.py` (the toy network's
mock tools) and `tests/test_agent.py` (action parsing + the full ReAct loop
against a scripted fake LLM, no live model needed); `python
tests/run_tests.py` (run from the repo root) runs both.

## Suggested first experiment

1. Run the agent a handful of times against the same model and watch the
   console output — does it read tool output carefully, or does it fall
   back on guessed credentials/module names?
2. Try a different `MODEL` (or `BACKEND`) and compare: does it reach the
   flag? How many steps/tool calls does it take?
3. Read `offensive_cyber/agent.py`'s `SYSTEM_PROMPT` and `render_observation()`
   — these are the two places you'd edit to change what the model is told.
