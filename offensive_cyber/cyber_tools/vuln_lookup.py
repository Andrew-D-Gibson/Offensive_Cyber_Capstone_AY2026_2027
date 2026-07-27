from typing import Optional
from pydantic import BaseModel
from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from toy_network import TOOL_REGISTRY


class VulnLookupInput(BaseModel):
    service: str
    version: str


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
                result="No vulnerabilities found for this service/version",
                match=False,
                cve=None,
                type=None,
                exploit_module=None
            )
