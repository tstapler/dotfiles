FROM mirror.gcr.io/python:3.13-slim AS builder

RUN pip install uv

WORKDIR /app

# Install build dependencies
RUN apt-get update \
    && apt-get install -y \
        build-essential \
        git \
        autoconf \
        automake \
        libcap2-bin \
    && rm -rf /var/lib/apt/lists/*

# Build and install fping from source
RUN git clone https://github.com/schweikert/fping.git \
    && cd fping \
    && git checkout v4.4 \
    && ./autogen.sh \
    && ./configure \
    && make \
    && make install \
    && setcap cap_net_raw+ep /usr/local/sbin/fping \
    && cd .. \
    && rm -rf fping

# Create and activate virtual environment
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

COPY pyproject.toml requirements.lock ./
RUN uv pip install --no-cache -r requirements.lock

FROM mirror.gcr.io/python:3.13-slim

WORKDIR /app

# traceroute is needed at runtime by the fping_mtr probe (path_to_google_dns)
# to rediscover the hop path each cycle; give it cap_net_raw like fping so it
# doesn't need to run as root.
RUN apt-get update \
    && apt-get install -y --no-install-recommends traceroute libcap2-bin \
    && setcap cap_net_raw+ep "$(readlink -f "$(command -v traceroute)")" \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and required directories
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/sbin/nologin" \
    --uid "10001" \
    appuser \
    && mkdir -p /etc/vaping/plugins /var/run \
    && chown -R appuser:appuser /etc/vaping /var/run /app

# setcap file capabilities survive a COPY --from between stages, so fping
# keeps cap_net_raw without needing build tooling in the final image.
COPY --from=builder /usr/local/sbin/fping /usr/local/sbin/fping
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

# Copy config file
COPY --chown=appuser:appuser config.yaml /etc/vaping/config.yaml

# DNS timing probe script, run by the `dns_resolution_timing` command probe
COPY --chown=appuser:appuser dns_probe.py /app/dns_probe.py

# vaping registers plugins eagerly on `import vaping.plugins`, so a plugin of
# the same name dropped on VAPING_HOME/plugins never overrides the bundled
# one (it's already in the registry by the time the search path is
# consulted). Overwrite the installed package's copy directly instead.
COPY --chown=appuser:appuser prometheus_plugin.py /tmp/prometheus_plugin.py
RUN cp /tmp/prometheus_plugin.py "$(python -c 'import vaping.plugins.prometheus as m; print(m.__file__)')" \
    && rm /tmp/prometheus_plugin.py

# command.py in this vaping fork has a bug: CommandProbe.init() extends
# self.hosts without initializing it first, and never unwraps dict-style
# host entries ({host: ..., name: ...}) the way fping.py does. Same
# override technique as prometheus_plugin.py above.
COPY --chown=appuser:appuser command_plugin.py /tmp/command_plugin.py
RUN cp /tmp/command_plugin.py "$(python -c 'import vaping.plugins.command as m; print(m.__file__)')" \
    && rm /tmp/command_plugin.py

# fping_mtr.py in this vaping fork hardcodes plain UDP traceroute, which
# doesn't work from inside a Docker container: the bridge NAT rewrites UDP
# source ports, so returned ICMP TTL-exceeded packets from hops beyond the
# gateway never match back to the probing socket (traceroute only ever
# resolves hop 1). ICMP echo probes (-I) don't have this problem. Same
# override technique as prometheus_plugin.py above.
COPY --chown=appuser:appuser fping_mtr_plugin.py /tmp/fping_mtr_plugin.py
RUN cp /tmp/fping_mtr_plugin.py "$(python -c 'import vaping.plugins.fping_mtr as m; print(m.__file__)')" \
    && rm /tmp/fping_mtr_plugin.py

USER appuser

CMD ["sh", "-c", "cat /etc/vaping/config.yaml && echo '\n--- Starting Vaping ---\n' && vaping start --debug"]
