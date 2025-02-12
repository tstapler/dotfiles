# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install rye
RUN curl -sSf https://raw.githubusercontent.com/mitsuhiko/rye/main/scripts/install.sh | RYE_INSTALL_OPTION="--yes" bash
ENV PATH="/root/.rye/shims:${PATH}"

# Set up project
WORKDIR /app
COPY pyproject.toml requirements.lock .
RUN rye sync --no-lock --no-dev

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    fping \
    && rm -rf /var/lib/apt/lists/*

# Copy Python environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app
VOLUME ["/etc/vaping", "/var/run"]

CMD ["vaping", "start", "--debug"]
