import asyncio
from typing import Dict, List, Any

from fairlib import (
    SimpleAgent,
    ReActPlanner,
    OllamaAdapter,
    ToolRegistry,
    WorkingMemory,
    ToolExecutor,
)

from offensive_cyber.cyber_tools import (
    ListSubnetTool,
    NmapScanTool,
    ServiceBannerTool,
    VulnLookupTool,
    RunExploitTool,
    SSHLoginTool,
)

from toy_network import TOOL_REGISTRY


async def create_single_cyber_agent() -> SimpleAgent:
    llm = OllamaAdapter(model_name="qwen2.5:14b")

    registry = ToolRegistry()
    tools = [
        ListSubnetTool(),
        NmapScanTool(),
        ServiceBannerTool(),
        VulnLookupTool(),
        RunExploitTool(),
        SSHLoginTool(),
    ]

    for tool in tools:
        registry.register_tool(tool)

    planner = ReActPlanner(
        llm=llm,
        tool_registry=registry
    )

    executor = ToolExecutor(registry)

    memory = WorkingMemory(max_size=30)

    agent = SimpleAgent(
        llm=llm,
        planner=planner,
        tool_executor=executor,
        memory=memory,
        max_steps=15
    )

    return agent


async def run_single_cyber_agent(
    query: str,
    max_steps: int = 15,
    verbose: bool = False
) -> Dict[str, Any]:
    agent = await create_single_cyber_agent()

    log: List[Dict] = []
    tool_call_count = 0
    start_time = asyncio.get_event_loop().time()

    try:
        result = await agent.arun(
            query,
            max_steps=max_steps,
            on_tool_calls=lambda step_log: log.extend(step_log)
        )

        found_flag = None
        for entry in log:
            obs = entry.get("observation", {})
            if isinstance(obs, dict) and "flag" in obs:
                found_flag = obs["flag"]
                break

        elapsed = asyncio.get_event_loop().time() - start_time

        return {
            "architecture": "single_react_fairlib",
            "success": found_flag == TOOL_REGISTRY["ssh_login"].__self__.SCENARIO["flag"] if found_flag else False,
            "steps": len([e for e in log if e.get("type") == "action"]),
            "tool_calls": tool_call_count,
            "wall_time_sec": round(elapsed, 3),
            "claimed_flag": found_flag,
            "log": log,
        }

    except Exception as e:
        elapsed = asyncio.get_event_loop().time() - start_time
        return {
            "architecture": "single_react_fairlib",
            "success": False,
            "steps": len(log),
            "tool_calls": tool_call_count,
            "wall_time_sec": round(elapsed, 3),
            "claimed_flag": None,
            "log": log,
            "error": str(e),
        }
