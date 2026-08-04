# Offensive Cyber Agent: a minimal fair_llm ReAct testbed

A small, fully-synthetic ReAct agent, built from fair_llm's basic building
blocks, that has to chain six tool calls through a fake "pivot" scenario to
find a flag.

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
└── offensive_cyber/          # the project package
    ├── toy_network.py        # the scenario + every mock tool's hardcoded response
    ├── cyber_tools/           # fairlib AbstractTool wrappers around toy_network.py
    ├── single_agent.py        # assembles the fairlib SimpleAgent
    └── live_logging.py        # subscribes console logging to the agent's event bus
```

- `offensive_cyber/toy_network.py` — the scenario and every mock tool's
  hardcoded response (`TOOL_REGISTRY`, `TOOL_DESCRIPTIONS`). Read this
  first; it's the entire fake sandbox.

- `offensive_cyber/cyber_tools/` — fairlib `AbstractTool` wrappers around
  `toy_network.py`'s fake responses:
    - `ListSubnetTool`
    - `NmapScanTool`
    - `ServiceBannerTool`
    - `VulnLookupTool`
    - `RunExploitTool`
    - `SSHLoginTool`
  Each is a small Pydantic input model plus one `acall()` method; output
  reuses fairlib's built-in `TextResult` rather than a custom schema per
  tool.

- `offensive_cyber/single_agent.py` — assembles one fairlib `SimpleAgent`: a
  `ToolRegistry` of the tools above, a `ToolExecutor`, `WorkingMemory`, and
  a `SimpleReActPlanner`.

- `offensive_cyber/live_logging.py` — subscribes a `logging.Logger` to
  fairlib's event bus so you see each ReAct step and tool call printed to
  the console as it happens, not just after the run finishes.

- `experiment_runner.py` — builds an LLM via fairlib's `OllamaAdapter` or
  `HuggingFaceAdapter`, runs the agent once via `arun_with_trace()`, and
  prints a summary.


## Quickstart

**Requirements:** Python 3.12, and (for `BACKEND=ollama`, the default)
[Ollama](https://ollama.com) installed and running locally.

### 1. Get the code and create an environment

Pick **one** of the two options below:

- Option A: venv (built into Python):

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

- Option B: conda (if you have it installed already):

```bash
conda create -n offensive-cyber python=3.12 -y
conda activate offensive-cyber
```

### 2. Install dependencies

```bash
pip install -r requirements.txt   # fairlib + this project's own deps
```

### 3. Configure

```bash
cp .env.example .env              # then edit .env to taste
```

All configuration lives in `.env` (see `.env.example` for every option,
documented inline) — there are no command-line flags. The main knobs:

| Variable         | Meaning                                                                                                                     |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `BACKEND`        | `ollama` (a local model already pulled via `ollama pull`) or `huggingface` (a local `transformers` model, downloaded on first use — see `HF_AUTH_TOKEN`/`HF_QUANTIZED` for gated/quantized models). |
| `MODEL`          | The Ollama tag or HuggingFace alias/repo id to use.                                                                            |
| `MAX_STEPS`      | How many ReAct steps the agent gets before giving up.                                                                          |
| `LOG_LEVEL`      | `DEBUG` for maximum step-by-step detail, `INFO` (default), or `WARNING` for a quiet run.                                       |

> **If you use `BACKEND=ollama`** `MODEL` must name a model Ollama already has
> pulled locally, or every call 404s at `/api/chat`. Check with
> `ollama list`, and pull one if you need to: `ollama pull llama3.1:8b`.

### 4. Run it

```bash
python experiment_runner.py
```

`live_logging.py` prints each agent step and tool call to the console in
real time as the run happens. Results also land in `trace.json` — the
full structured `AgentRunTrace` fairlib generates, useful for closer
inspection of a run.

## Suggested first experiment

1. Run the agent a handful of times against the same model and watch the
   console output — does it read tool output carefully, or does it fall
   back on guessed credentials/module names?
2. Try a different `MODEL` (or `BACKEND`) and compare: does it reach the
   flag? How many steps/tool calls does it take?
3. Read `offensive_cyber/single_agent.py`'s `ROLE_DEFINITION` and
   `offensive_cyber/cyber_tools/*.py` — these are the places you'd edit to
   change what the model is told.
