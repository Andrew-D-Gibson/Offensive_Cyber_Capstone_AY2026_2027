from typing import Optional, List
from pydantic import BaseModel
from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from toy_network import TOOL_REGISTRY


class NmapScanInput(BaseModel):
    target: str
    ports: Optional[List[int]] = None


class NmapScanOutput(TextResult):
    target: str
    open_ports: List[int]


class NmapScanTool(AbstractTool):
    name = "nmap_scan"
    description = "Perform port scan on target host to discover open ports. Optional ports parameter to scan specific ports."
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
