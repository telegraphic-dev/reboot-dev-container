# Reboot dev container

A public Docker development image for [Reboot](https://reboot.dev) applications. It starts the Reboot app, developer dashboard, and a Streamable HTTP MCP server that exposes the `rbt` CLI inside the container.

## Container image

Every push to `main` publishes a multi-architecture image for `linux/amd64` and `linux/arm64` to GitHub Container Registry:

```bash
docker pull ghcr.io/telegraphic-dev/reboot-dev-container:latest
```

Pull requests build both architectures but do not publish an image.

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
      "url": "http://localhost:3000/mcp",
      "headers": {
        "Authorization": "Bearer <MCP_BEARER_TOKEN>"
      }
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
| `RBT_APPLICATION_URL` | `http://127.0.0.1:$RBT_APP_PORT` | Default application URL injected into `rbt inspect ...`, `rbt export`, and `rbt import` when the caller does not provide one |
| `RBT_DASHBOARD_PORT` | `9871` | Dashboard port |
| `MCP_PORT` | `3000` | MCP HTTP port |
| `MCP_BEARER_TOKEN` | unset | Optional bearer token; set this whenever the MCP is reachable outside a trusted local network |
| `WORKSPACE_GIT_URL` | unset | Public Git repository cloned into an otherwise empty `/workspace` at startup |
| `WORKSPACE_GIT_REF` | `main` | Branch or tag to clone when `WORKSPACE_GIT_URL` is set |
| `RBT_COMMAND_TIMEOUT_SECONDS` | `120` | Maximum duration for one MCP `rbt` request |

`RBT_APP_PORT` and `RBT_DASHBOARD_PORT` are passed to the corresponding `rbt` processes. The image includes Python 3.12, Node.js 22, and `reboot[dev]` 1.6.0.

## Security

This is a local development image. Do not expose port 3000 directly to an untrusted network: its MCP endpoint can run every `rbt` command available in the mounted project. Set a high-entropy `MCP_BEARER_TOKEN` for every remote deployment; requests must include `Authorization: Bearer <token>`.

## Build only

```bash
docker build -t reboot-dev-container .
```
