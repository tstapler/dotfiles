FROM python:3.13-slim

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

# Create non-root user
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/sbin/nologin" \
    --uid "10001" \
    appuser \
    && chown -R appuser:appuser /app

# Create required directories first as root
RUN mkdir -p /etc/vaping /var/run /app && \
    chown -R appuser:appuser /etc/vaping /var/run /app

# Create and activate virtual environment
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

COPY --chown=appuser:appuser pyproject.toml requirements.lock ./
RUN uv pip install --no-cache -r requirements.lock

# Copy config file
COPY --chown=appuser:appuser config.yaml /etc/vaping/config.yaml

# Declare volumes after directory creation
VOLUME ["/etc/vaping"]

CMD ["sh", "-c", "cat /etc/vaping/config.yaml && echo '\n--- Starting Vaping ---\n' && vaping start --debug"]
