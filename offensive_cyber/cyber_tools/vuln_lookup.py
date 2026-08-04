from pydantic import BaseModel, Field
from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from offensive_cyber.toy_network import TOOL_REGISTRY


class VulnLookupInput(BaseModel):
    protocol: str = Field(description="The exact 'protocol' value service_banner reported - copy it verbatim.")
    full_banner_string: str = Field(description="The exact 'full_banner_string' service_banner reported - copy it verbatim.")


class VulnLookupTool(AbstractTool):
    name = "vuln_lookup"
    description = "Check the vulnerability database for an exact protocol+banner match."
    input_schema = VulnLookupInput
    output_schema = TextResult
    side_effect = SideEffect.READ_ONLY

    async def acall(self, tool_input: VulnLookupInput) -> ToolOutput:
        result = TOOL_REGISTRY["vuln_lookup"](
            service=tool_input.protocol, version=tool_input.full_banner_string
        )
        if result["match"]:
            return TextResult(
                result=f"Vulnerability found: {result['cve']} ({result['type']}) - use module {result['exploit_module']}"
            )
        return TextResult(
            result=(
                f"No vulnerabilities found for protocol='{tool_input.protocol}', "
                f"full_banner_string='{tool_input.full_banner_string}'."
            )
        )
