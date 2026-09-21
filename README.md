# Reboot dev container

A public Docker development image for [Reboot](https://reboot.dev) applications. It starts the Reboot app, developer dashboard, and a Streamable HTTP MCP server that exposes the `rbt` CLI inside the container.

## Quick start

Create a local app directory from a Reboot project (it must include `.rbtrc`):

```bash
git clone https://github.com/telegraphic-dev/reboot-pet-clinic.git app
docker compose up --build
```

The container exposes:

- `http://localhost:9991` — Reboot application and inspect UI (`/__/inspect`)
- `http://localhost:9871` — Reboot developer dashboard
- `http://localhost:3000/mcp` — Streamable HTTP MCP endpoint

The app source is bind-mounted at `/workspace`, so code changes on the host are picked up by `rbt dev run` according to the project's `.rbtrc` watch settings.
The image includes Envoy 1.38.4, which `rbt dev run` uses for Reboot's local proxy. It does not need a Docker-socket mount.

## MCP client configuration

Point an MCP client that supports Streamable HTTP at:

```json
{
  "mcpServers": {
    "reboot-rbt": {
      "type": "streamable-http",
      "url": "http://localhost:3000/mcp"
    }
  }
}
```

The server provides one `rbt(arguments)` tool. It accepts argv-style arguments and never invokes a shell:

```text
rbt(["generate"])
rbt(["inspect", "type", "list"])
rbt(["task", "list"])
```

Run `rbt(["--help"])` or a command-specific `--help` before using unfamiliar operations. `rbt` has state-changing and cloud commands; the MCP intentionally exposes the actual CLI rather than pretending those commands are read-only.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `RBT_APP_PORT` | `9991` | Reboot application port |
| `RBT_DASHBOARD_PORT` | `9871` | Dashboard port |
| `MCP_PORT` | `3000` | MCP HTTP port |
| `RBT_COMMAND_TIMEOUT_SECONDS` | `120` | Maximum duration for one MCP `rbt` request |

`RBT_APP_PORT` and `RBT_DASHBOARD_PORT` are passed to the corresponding `rbt` processes. The image includes Python 3.12, Node.js 22, and `reboot[dev]` 1.6.0.

## Security

This is a local development image. Do not expose port 3000 directly to an untrusted network: its MCP endpoint can run every `rbt` command available in the mounted project. Put it behind authenticated access if remote agents need it.

## Build only

```bash
docker build -t reboot-dev-container .
```
