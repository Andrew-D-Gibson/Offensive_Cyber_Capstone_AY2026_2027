"""Live, human-readable logging of an agent run as it happens.

SimpleAgent emits a typed event for every ReAct step, tool call, and planner
hiccup via its AgentEventBus. This module subscribes a plain logging.Logger
to that bus so you see each step and tool call as it happens, not just the
final summary line.

Nothing here drives the agent or affects what it does — this is pure
observability. Every subscriber below just formats an event and logs it;
none of them raise, return a value the framework reads, or mutate the
event. That matters because AgentEventBus dispatches synchronously, in
registration order, on the same thread/coroutine that's running the agent
loop: a subscriber that raised would only ever produce a warning in the
bus's own log (it's caught there, not here) and the loop would carry on
regardless. See fairlib.core.event_bus.AgentEventBus for the dispatch
contract these handlers rely on.
"""

import logging
from typing import Optional

from fairlib import (
    AgentEventBus,
    AgentStepEvent,
    DegradedResponseEvent,
    PlannerParseErrorEvent,
    ToolCallPostEvent,
    ToolCallPreEvent,
)

# Tool observations (e.g. an nmap_scan result) can be long; truncate what we
# print so one noisy tool call doesn't push everything else off-screen. The
# full, untruncated text still reaches the model and still lands in
# trace.json — this limit is a console-only display choice.
_OBSERVATION_PREVIEW_LEN = 300


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure console logging once and return this project's logger."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("offensive_cyber")


def _truncate(text: Optional[str], limit: int = _OBSERVATION_PREVIEW_LEN) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "..."


def attach_live_logger(events: AgentEventBus, logger: logging.Logger) -> None:
    """Subscribe `logger` to every step/tool/error event on `events`.

    Called once per run, from single_agent.run_single_cyber_agent, right
    after the agent (and its fresh AgentEventBus) are constructed. Five
    events cover the whole ReAct loop end to end:

        AgentStepEvent          -- one loop iteration begins
          -> ToolCallPreEvent   -- the planner chose a tool; about to call it
          -> ToolCallPostEvent  -- that tool call returned (or raised)
        PlannerParseErrorEvent  -- the model's response didn't parse (can
                                   happen inside any step; the framework
                                   retries once before giving up)
        DegradedResponseEvent   -- the LLM call itself failed (timeout, rate
                                   limit, provider error, ...), independent
                                   of whether a tool was involved

    Each handler below just logs one event type; the four lines at the
    bottom are what actually wire them up.
    """

    def on_step(event: AgentStepEvent) -> None:
        # Fires at the *start* of every iteration, before the planner is
        # even called for this step -- so you'll see step N logged even if
        # step N is the one that ultimately fails to parse or errors out.
        # event.step is 0-indexed; +1 here so the console reads "1/45" like
        # a human would expect, matching MAX_STEPS in .env.
        logger.info("step %d/%d (history=%d)", event.step + 1, event.max_steps, event.history_length)

    def on_tool_pre(event: ToolCallPreEvent) -> None:
        # tool_input is whatever the planner produced -- usually a dict
        # matching the tool's Pydantic schema, but planners are free to
        # hand back a raw string here too (see the malformed-input log
        # lines you'll see if a model skips the JSON shape); %r shows
        # exactly what was sent either way.
        logger.info("  -> calling %s(%r)", event.tool_name, event.tool_input)

    def on_tool_post(event: ToolCallPostEvent) -> None:
        # Always fires exactly once per ToolCallPreEvent, success or
        # failure -- there's no case where a "pre" is logged with no
        # matching "post". observation is the exact text fed back to the
        # model as the next Observation, so this line is your best proxy
        # for "what does the agent see right now."
        status = "ok" if event.succeeded else "FAILED"
        logger.info("  <- %s %s: %s", event.tool_name, status, _truncate(event.observation))

    def on_parse_error(event: PlannerParseErrorEvent) -> None:
        # The model's raw completion didn't match SimpleReActPlanner's
        # expected "Thought: / Action: / tool_name: / tool_input:" shape.
        # attempt=1 means the framework will automatically re-prompt with a
        # corrective message and try once more (will_retry=True); attempt=2
        # means that retry also failed and PlannerParseError is about to
        # propagate up to experiment_runner.py's try/except.
        logger.warning("planner parse error (attempt %d, will_retry=%s)", event.attempt, event.will_retry)

    def on_degraded(event: DegradedResponseEvent) -> None:
        # Something went wrong at the transport/provider level rather than
        # in the model's output -- e.g. Ollama isn't running, a HuggingFace
        # generation call OOM'd, a rate limit was hit. The underlying
        # DegradedResponse exception still propagates after this fires;
        # this line is purely so you see *why* the run is about to die
        # instead of just seeing a traceback.
        logger.warning("degraded response from %s: %s (%s)", event.provider, event.kind, event.message)

    # Registration order doesn't matter for correctness (each event type has
    # its own subscriber list), but AgentEventBus dispatches synchronously
    # and in-order, so for a given event type these always fire before the
    # agent loop moves on to whatever produced the *next* event.
    events.subscribe(AgentStepEvent, on_step)
    events.subscribe(ToolCallPreEvent, on_tool_pre)
    events.subscribe(ToolCallPostEvent, on_tool_post)
    events.subscribe(PlannerParseErrorEvent, on_parse_error)
    events.subscribe(DegradedResponseEvent, on_degraded)
