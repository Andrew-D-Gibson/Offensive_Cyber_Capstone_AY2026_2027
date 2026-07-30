from typing import Optional
from pydantic import BaseModel, Field
from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from offensive_cyber.toy_network import TOOL_REGISTRY


class VulnLookupInput(BaseModel):
    service: str = Field(
        description="The exact 'service' value service_banner reported (e.g. 'http', 'ssh') - copy it verbatim."
    )
    version: str = Field(
        description=(
            "The exact 'version' value service_banner reported - copy it verbatim, character for "
            "character, including any embedded product name or slash (e.g. 'VulnCorp-WebApp/1.2'). "
            "Do not split it, reword it, or move part of it into the service field."
        )
    )


class VulnLookupOutput(TextResult):
    match: bool
    cve: Optional[str] = None
    type: Optional[str] = None
    exploit_module: Optional[str] = None


class VulnLookupTool(AbstractTool):
    name = "vuln_lookup"
    description = "Check vulnerability database for exact service+version match."
    input_schema = VulnLookupInput
    output_schema = VulnLookupOutput
    side_effect = SideEffect.READ_ONLY

    async def acall(self, tool_input: BaseModel) -> ToolOutput:
        result = TOOL_REGISTRY["vuln_lookup"](
            service=tool_input.service,
            version=tool_input.version
        )
        if result["match"]:
            return VulnLookupOutput(
                result=f"Vulnerability found: {result['cve']} ({result['type']}) - use module {result['exploit_module']}",
                match=True,
                cve=result["cve"],
                type=result["type"],
                exploit_module=result["exploit_module"]
            )
        else:
            return VulnLookupOutput(
                result=(
                    f"No vulnerabilities found for service='{tool_input.service}', "
                    f"version='{tool_input.version}'. If a service_banner call reported a "
                    "version for this host/port, double-check you copied its 'service' and "
                    "'version' fields verbatim rather than re-splitting or paraphrasing them."
                ),
                match=False,
                cve=None,
                type=None,
                exploit_module=None
            )
