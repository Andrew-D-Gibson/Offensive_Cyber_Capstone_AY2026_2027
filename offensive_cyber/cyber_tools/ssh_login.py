from pydantic import BaseModel, Field
from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from offensive_cyber.toy_network import TOOL_REGISTRY


class SSHLoginInput(BaseModel):
    target: str = Field(description="IP address to attempt login against.")
    username: str = Field(description="Username - only use credentials obtained from a tool's own output.")
    password: str = Field(description="Password - only use credentials obtained from a tool's own output.")


class SSHLoginTool(AbstractTool):
    name = "ssh_login"
    description = "Attempt SSH login with credentials to gain access."
    input_schema = SSHLoginInput
    output_schema = TextResult
    side_effect = SideEffect.MUTATING

    async def acall(self, tool_input: SSHLoginInput) -> ToolOutput:
        result = TOOL_REGISTRY["ssh_login"](
            target=tool_input.target, username=tool_input.username, password=tool_input.password
        )
        if result["success"]:
            return TextResult(result=f"SSH login successful! Flag obtained: {result['flag']}")
        return TextResult(result=f"SSH login failed: {result['error']}")
