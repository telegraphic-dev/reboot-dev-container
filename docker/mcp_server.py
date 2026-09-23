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
        "Run the Reboot rbt CLI in the mounted workspace. First use rbt_describe "
        "to list commands, then rbt_help for exact syntax. Inspect commands default "
        "to RBT_APPLICATION_URL (or the local Reboot app)."
    ),
    host=HOST,
    port=PORT,
    streamable_http_path="/mcp",
)


def _run_rbt(arguments: list[str]) -> dict[str, object]:
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


@mcp.tool()
def rbt_describe() -> dict[str, object]:
    """List every top-level Reboot CLI command available in this container.

    Call this before an unfamiliar operation, then use rbt_help for the exact
    syntax of the chosen command.
    """
    return _run_rbt(["--help"])


@mcp.tool()
def rbt_help(command: list[str] | None = None) -> dict[str, object]:
    """Show exact syntax for an rbt command or subcommand.

    Call with no argument for top-level help, or e.g.
    command=["inspect", "state", "list"] or command=["export"].
    """
    return _run_rbt([*(command or []), "--help"])


@mcp.tool()
def rbt(arguments: list[str]) -> dict[str, object]:
    """Run an rbt CLI command in /workspace without a shell.

    First call rbt_describe to discover available commands, then rbt_help for
    exact syntax. Valid examples include arguments=["inspect", "type", "list"],
    arguments=["export", "--directory=/workspace/export"], and
    arguments=["generate", "api"]. `rbt` never accepts shell syntax.
    Application URL defaults are supplied for inspect, export, and import;
    a non-zero rbt exit is returned as an MCP tool error.
    """
    if any(not isinstance(argument, str) for argument in arguments):
        raise ValueError("arguments must be an array of strings")
    return _run_rbt(arguments)


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
