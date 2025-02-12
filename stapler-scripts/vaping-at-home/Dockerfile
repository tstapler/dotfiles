# Build stage
FROM python:3.13-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    python3-dev \
    python3.11-dev \
    libzmq3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install rye
RUN curl -sSf https://raw.githubusercontent.com/mitsuhiko/rye/main/scripts/install.sh | RYE_INSTALL_OPTION="--yes" bash
ENV PATH="/root/.rye/shims:${PATH}"

# Set up project
WORKDIR /app
COPY pyproject.toml requirements.lock .
RUN rye sync --no-lock --no-dev && \
    test -f /app/.venv/bin/vaping || { echo "vaping executable not found"; exit 1; }

# Runtime stage
FROM python:3.13-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    fping \
    && rm -rf /var/lib/apt/lists/*

# Copy Python environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/.venv/lib/python3.13/site-packages:$PYTHONPATH"

WORKDIR /app
VOLUME ["/etc/vaping", "/var/run"]

CMD ["vaping", "start", "--debug"]
