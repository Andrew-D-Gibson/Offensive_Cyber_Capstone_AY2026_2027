"""Shared helpers for turning a fairlib run trace into this project's result shape.

single_agent.py and multi_agent.py both need the same two things from a
finished AbstractAgentRunTrace: the list of tool calls that happened, and
whether SSHLoginTool's observation reported the toy network's flag. This
module is the one place that logic lives.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

# Matches the "Flag obtained: <flag>" text SSHLoginTool puts in its
# observation on a successful login (see cyber_tools/ssh_login.py).
FLAG_RE = re.compile(r"Flag obtained:\s*(\S+)")


def extract_tool_log(trace) -> List[Dict[str, Any]]:
    """Pull every tool call (name, input, success, observation) out of a trace."""
    return [
        {
            "step": event.payload.get("step"),
            "tool_name": event.payload.get("tool_name"),
            "tool_input": event.payload.get("tool_input"),
            "succeeded": event.payload.get("succeeded"),
            "observation": event.payload.get("observation"),
        }
        for event in trace.events
        if event.event_type == "ToolCallPostEvent"
    ]


def check_flag(log: List[Dict[str, Any]], expected_flag: str) -> Tuple[bool, Optional[str]]:
    """Scan a tool-call log for a successful ssh_login and check its flag.

    Returns (success, claimed_flag). claimed_flag is None if ssh_login never
    succeeded or its observation didn't match FLAG_RE; success is True only
    when a claimed flag exactly matches expected_flag.
    """
    for entry in log:
        if entry["tool_name"] == "ssh_login" and entry["succeeded"]:
            match = FLAG_RE.search(entry["observation"] or "")
            if match:
                claimed = match.group(1)
                return claimed == expected_flag, claimed
    return False, None
