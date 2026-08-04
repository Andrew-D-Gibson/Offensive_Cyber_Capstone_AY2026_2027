from pydantic import BaseModel, Field
from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from offensive_cyber.toy_network import TOOL_REGISTRY


class NmapScanInput(BaseModel):
    target: str = Field(description="IP address of a host, as returned by list_subnet.")


class NmapScanTool(AbstractTool):
    name = "nmap_scan"
    description = "Perform a full port scan on a target host, reporting every open port."
    input_schema = NmapScanInput
    output_schema = TextResult
    side_effect = SideEffect.READ_ONLY

    async def acall(self, tool_input: NmapScanInput) -> ToolOutput:
        result = TOOL_REGISTRY["nmap_scan"](target=tool_input.target)
        if "error" in result:
            return TextResult(result=result["error"])
        return TextResult(result=f"Target {result['target']} has open ports: {result['open_ports']}")
