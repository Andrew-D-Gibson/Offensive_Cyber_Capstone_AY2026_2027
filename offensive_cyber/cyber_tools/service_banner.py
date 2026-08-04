from pydantic import BaseModel, Field
from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from offensive_cyber.toy_network import TOOL_REGISTRY


class ServiceBannerInput(BaseModel):
    target: str = Field(description="IP address of a host, as returned by list_subnet or nmap_scan.")
    port: int = Field(description="An open port on that host, as returned by nmap_scan.")


class ServiceBannerTool(AbstractTool):
    name = "service_banner"
    description = "Grab the service banner on a specific target and port."
    input_schema = ServiceBannerInput
    output_schema = TextResult
    side_effect = SideEffect.READ_ONLY

    async def acall(self, tool_input: ServiceBannerInput) -> ToolOutput:
        result = TOOL_REGISTRY["service_banner"](target=tool_input.target, port=tool_input.port)
        if "error" in result:
            return TextResult(result=result["error"])
        return TextResult(
            result=(
                f"Target {result['target']}:{result['port']} -> "
                f"protocol='{result['service']}', full_banner_string='{result['version']}' "
                "(pass these two values to vuln_lookup verbatim)"
            )
        )
