FROM python:3.13-slim

RUN pip install uv

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends fping \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/app" \
    --shell "/sbin/nologin" \
    --uid "10001" \
    appuser \
    && chown -R appuser:appuser /app

USER appuser

# Create and activate virtual environment
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

COPY --chown=appuser:appuser pyproject.toml requirements.lock ./
RUN uv pip install --no-cache -r requirements.lock

# Create required directories
RUN mkdir -p /etc/vaping /var/run && \
    chown -R appuser:appuser /etc/vaping /var/run

# Declare volumes after creating directories
VOLUME ["/etc/vaping", "/var/run"]

CMD ["vaping", "start", "--debug"]
