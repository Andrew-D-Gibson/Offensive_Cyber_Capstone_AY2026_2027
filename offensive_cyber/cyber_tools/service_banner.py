from pydantic import BaseModel
from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from toy_network import TOOL_REGISTRY


class ServiceBannerInput(BaseModel):
    target: str
    port: int


class ServiceBannerOutput(TextResult):
    target: str
    port: int
    service: str
    version: str


class ServiceBannerTool(AbstractTool):
    name = "service_banner"
    description = "Grab service banner on a specific target and port."
    input_schema = ServiceBannerInput
    output_schema = ServiceBannerOutput
    side_effect = SideEffect.EXTERNAL

    async def acall(self, tool_input: BaseModel) -> ToolOutput:
        result = TOOL_REGISTRY["service_banner"](
            target=tool_input.target,
            port=tool_input.port
        )
        return ServiceBannerOutput(
            result=f"Target {result['target']}:{result['port']} running {result['service']} {result['version']}",
            target=result["target"],
            port=result["port"],
            service=result["service"],
            version=result["version"]
        )
