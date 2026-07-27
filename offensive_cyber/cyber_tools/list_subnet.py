from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from pydantic import BaseModel
from toy_network import TOOL_REGISTRY


class ListSubnetInput(BaseModel):
    pass


class ListSubnetOutput(TextResult):
    discovered_hosts: list


class ListSubnetTool(AbstractTool):
    name = "list_subnet"
    description = "Discover hosts on the local subnet via ping sweep or ARP scan."
    input_schema = ListSubnetInput
    output_schema = ListSubnetOutput
    side_effect = SideEffect.READ_ONLY

    async def acall(self, tool_input: BaseModel) -> ToolOutput:
        result = TOOL_REGISTRY["list_subnet"]()
        return ListSubnetOutput(
            result=f"Discovered hosts: {result['discovered_hosts']}",
            discovered_hosts=result["discovered_hosts"]
        )
