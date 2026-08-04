"""Live, human-readable logging of an agent run as it happens.

SimpleAgent emits a typed event for every ReAct step, tool call, and planner
hiccup via its AgentEventBus. This module subscribes a plain logging.Logger
to that bus so you see each step and tool call as it happens, not just the
final summary line.
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
    """Subscribe `logger` to every step/tool/error event on `events`."""

    def on_step(event: AgentStepEvent) -> None:
        logger.info("\nstep %d/%d (history=%d)", event.step + 1, event.max_steps, event.history_length)

    def on_tool_pre(event: ToolCallPreEvent) -> None:
        logger.info("  -> calling %s(%r)", event.tool_name, event.tool_input)

    def on_tool_post(event: ToolCallPostEvent) -> None:
        status = "ok" if event.succeeded else "FAILED"
        logger.info("  <- %s %s: %s", event.tool_name, status, _truncate(event.observation))

    def on_parse_error(event: PlannerParseErrorEvent) -> None:
        logger.warning("planner parse error (attempt %d, will_retry=%s)", event.attempt, event.will_retry)

    def on_degraded(event: DegradedResponseEvent) -> None:
        logger.warning("degraded response from %s: %s (%s)", event.provider, event.kind, event.message)

    events.subscribe(AgentStepEvent, on_step)
    events.subscribe(ToolCallPreEvent, on_tool_pre)
    events.subscribe(ToolCallPostEvent, on_tool_post)
    events.subscribe(PlannerParseErrorEvent, on_parse_error)
    events.subscribe(DegradedResponseEvent, on_degraded)
