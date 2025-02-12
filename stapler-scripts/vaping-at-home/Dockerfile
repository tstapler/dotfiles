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

COPY requirements.lock ./
RUN uv pip install --no-cache --system -r requirements.lock

VOLUME ["/etc/vaping", "/var/run"]

CMD ["vaping", "start", "--debug"]
