"""HTTP MCP server exposing the container's rbt CLI without a shell."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

WORKSPACE = Path(os.environ.get("WORKSPACE", "/workspace")).resolve()
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "3000"))

mcp = FastMCP(
    "reboot-rbt",
    instructions=(
        "Run the Reboot rbt CLI in the mounted workspace. Use `rbt --help` or "
        "`rbt <command> --help` before unfamiliar commands."
    ),
    host=HOST,
    port=PORT,
    streamable_http_path="/mcp",
)


@mcp.tool()
def rbt(arguments: list[str]) -> dict[str, object]:
    """Run `rbt` with argv-style arguments in /workspace.

    Example: arguments=["generate"] or arguments=["inspect", "type", "list"].
    The command is never passed through a shell.
    """
    if any(not isinstance(argument, str) for argument in arguments):
        raise ValueError("arguments must be an array of strings")

    result = subprocess.run(
        ["rbt", *arguments],
        cwd=WORKSPACE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=int(os.environ.get("RBT_COMMAND_TIMEOUT_SECONDS", "120")),
        check=False,
    )
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
