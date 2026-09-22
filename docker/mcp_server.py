"""HTTP MCP server exposing the container's rbt CLI without a shell."""

from __future__ import annotations

import hmac
import os
import subprocess
from pathlib import Path

import uvicorn
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

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
    app = mcp.streamable_http_app()
    bearer_token = os.environ.get("MCP_BEARER_TOKEN", "")

    if bearer_token:
        configured_bearer_token = bearer_token

        @app.middleware("http")
        async def require_bearer_token(request: Request, call_next):
            authorization = request.headers.get("authorization", "")
            scheme, _, token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not hmac.compare_digest(
                token, configured_bearer_token
            ):
                return JSONResponse(
                    {"error": "MCP bearer token required"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return await call_next(request)

    uvicorn.run(app, host=HOST, port=PORT)
