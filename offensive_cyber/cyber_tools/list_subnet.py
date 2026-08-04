from pydantic import BaseModel
from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from offensive_cyber.toy_network import TOOL_REGISTRY


class NoInput(BaseModel):
    pass


class ListSubnetTool(AbstractTool):
    name = "list_subnet"
    description = "Discover hosts on the local subnet via ping sweep or ARP scan."
    input_schema = NoInput
    output_schema = TextResult
    side_effect = SideEffect.READ_ONLY

    async def acall(self, tool_input: NoInput) -> ToolOutput:
        result = TOOL_REGISTRY["list_subnet"]()
        return TextResult(result=f"Discovered hosts: {result['discovered_hosts']}")
