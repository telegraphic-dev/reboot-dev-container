FROM envoyproxy/envoy:v1.38.4 AS envoy

FROM python:3.12-slim

ARG NODE_MAJOR=22

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    WORKSPACE=/workspace \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=3000 \
    RBT_APP_PORT=9991 \
    RBT_DASHBOARD_PORT=9871

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates curl tini \
    && curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install --no-install-recommends -y nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "reboot[dev]==1.6.0" "mcp==1.27.0"

COPY --from=envoy /usr/local/bin/envoy /usr/local/bin/envoy
COPY docker/mcp_server.py /opt/reboot-mcp/mcp_server.py
COPY docker/entrypoint.py /opt/reboot-mcp/entrypoint.py

WORKDIR /workspace

EXPOSE 9991 9871 3000

ENTRYPOINT ["/usr/bin/tini", "--", "python", "/opt/reboot-mcp/entrypoint.py"]
