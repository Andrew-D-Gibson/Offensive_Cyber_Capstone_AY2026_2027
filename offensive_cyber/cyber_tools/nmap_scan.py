from typing import Optional, List
from pydantic import BaseModel, Field
from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from offensive_cyber.toy_network import TOOL_REGISTRY


class NmapScanInput(BaseModel):
    target: str = Field(description="IP address of a host, as returned by list_subnet.")
    ports: Optional[List[int]] = Field(
        default=None,
        description="Ignored by this tool - it always reports every open port on the host.",
    )


class NmapScanOutput(TextResult):
    target: str
    open_ports: List[int]


class NmapScanTool(AbstractTool):
    name = "nmap_scan"
    description = "Perform a full port scan on a target host, reporting every open port."
    input_schema = NmapScanInput
    output_schema = NmapScanOutput
    side_effect = SideEffect.EXTERNAL

    async def acall(self, tool_input: BaseModel) -> ToolOutput:
        result = TOOL_REGISTRY["nmap_scan"](target=tool_input.target)
        return NmapScanOutput(
            result=f"Target {result['target']} has open ports: {result['open_ports']}",
            target=result["target"],
            open_ports=result["open_ports"]
        )
