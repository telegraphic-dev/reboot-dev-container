"""HTTP MCP server exposing the container's rbt CLI without a shell."""

from __future__ import annotations

import hmac
import json
import os
import subprocess
from pathlib import Path

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from starlette.requests import Request
from starlette.responses import JSONResponse

WORKSPACE = Path(os.environ.get("WORKSPACE", "/workspace")).resolve()
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "3000"))
APPLICATION_URL = os.environ.get(
    "RBT_APPLICATION_URL",
    f"http://127.0.0.1:{os.environ.get('RBT_APP_PORT', '9991')}",
)


def _has_option(arguments: list[str], option: str) -> bool:
    return option in arguments or any(argument.startswith(f"{option}=") for argument in arguments)


def _with_default_application_url(arguments: list[str]) -> list[str]:
    if (
        arguments
        and arguments[0] in {"inspect", "export", "import"}
        and not _has_option(arguments, "--application-url")
    ):
        return [*arguments, f"--application-url={APPLICATION_URL}"]
    return arguments

mcp = FastMCP(
    "reboot-rbt",
    instructions=(
        "Run the Reboot rbt CLI in the mounted workspace. Inspect commands default "
        "to RBT_APPLICATION_URL (or the local Reboot app). Use `rbt --help` or "
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
    Inspect, export, and import commands automatically receive
    --application-url from RBT_APPLICATION_URL (defaulting to the local Reboot
    app) unless you
    supply --application-url explicitly. A non-zero rbt exit code is returned
    as an MCP tool error. The command is never passed through a shell.
    """
    if any(not isinstance(argument, str) for argument in arguments):
        raise ValueError("arguments must be an array of strings")

    resolved_arguments = _with_default_application_url(arguments)
    result = subprocess.run(
        ["rbt", *resolved_arguments],
        cwd=WORKSPACE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=int(os.environ.get("RBT_COMMAND_TIMEOUT_SECONDS", "120")),
        check=False,
    )
    response = {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if result.returncode:
        raise ToolError(json.dumps(response))
    return response


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
