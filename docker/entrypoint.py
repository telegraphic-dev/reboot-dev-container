"""Run Reboot development (including its dashboard) and the HTTP MCP server."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

workspace = Path(os.environ.get("WORKSPACE", "/workspace"))
app_port = os.environ.get("RBT_APP_PORT", "9991")
dashboard_port = os.environ.get("RBT_DASHBOARD_PORT", "9871")

if not (workspace / ".rbtrc").is_file():
    sys.stderr.write("/workspace must contain a Reboot project with .rbtrc\n")
    raise SystemExit(2)

commands = [
    ["rbt", "dev", "run", f"--port={app_port}", f"--dashboard-port={dashboard_port}"],
    ["rbt", "dashboard", f"--port={dashboard_port}"],
    [sys.executable, "/opt/reboot-mcp/mcp_server.py"],
]
processes = [subprocess.Popen(command, cwd=workspace) for command in commands]


def stop_processes(_signum: int, _frame: object) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()


signal.signal(signal.SIGTERM, stop_processes)
signal.signal(signal.SIGINT, stop_processes)

exit_code = 0
try:
    while True:
        for process in processes:
            result = process.poll()
            if result is not None:
                exit_code = result
                stop_processes(signal.SIGTERM, None)
                raise SystemExit(exit_code)
        time.sleep(0.2)
finally:
    stop_processes(signal.SIGTERM, None)
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
