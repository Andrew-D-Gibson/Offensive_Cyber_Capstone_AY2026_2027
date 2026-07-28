from typing import Optional
from pydantic import BaseModel
from fairlib.core.interfaces.tools import AbstractTool, SideEffect, TextResult, ToolOutput
from offensive_cyber.toy_network import TOOL_REGISTRY


class SSHLoginInput(BaseModel):
    target: str
    username: str
    password: str


class SSHLoginOutput(TextResult):
    success: bool
    flag: Optional[str] = None
    error: Optional[str] = None


class SSHLoginTool(AbstractTool):
    name = "ssh_login"
    description = "Attempt SSH login with credentials to gain access."
    input_schema = SSHLoginInput
    output_schema = SSHLoginOutput
    side_effect = SideEffect.EXTERNAL

    async def acall(self, tool_input: BaseModel) -> ToolOutput:
        result = TOOL_REGISTRY["ssh_login"](
            target=tool_input.target,
            username=tool_input.username,
            password=tool_input.password
        )
        if result["success"]:
            return SSHLoginOutput(
                result=f"SSH login successful! Flag obtained: {result['flag']}",
                success=True,
                flag=result["flag"]
            )
        else:
            return SSHLoginOutput(
                result=f"SSH login failed: {result['error']}",
                success=False,
                error=result["error"]
            )
