FROM python:3.13-slim as base

WORKDIR /work

FROM base as build

# Install build dependencies
RUN \
    --mount=type=cache,target=/var/lib/apt/lists \
    --mount=type=cache,target=/var/cache/apt/archives \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        build-essential

ENV RYE_HOME="/work/rye"
ENV PATH="$RYE_HOME/shims:$PATH"
ENV RYE_TOOLCHAIN="/usr/local"

RUN curl -sLSf https://rye-up.com/get | RYE_INSTALL_OPTION="--yes" bash

# Build project
RUN --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=requirements.lock,target=requirements.lock \
    --mount=type=cache,target=/work/.cache/pip \
    rye sync --no-dev --no-lock \
    && rye build --wheel \
    && sed '/-e/d' requirements.lock > dist/requirements.lock

FROM base as run

ENV PATH=/work/.local/bin:$PATH

# Install dependencies and project
RUN --mount=type=cache,target=/work/.cache/pip\
    --mount=type=bind,from=build,source=/work/dist,target=/work/dist \
    python -m pip install -r /work/dist/requirements.lock /work/dist/*.whl

# Install runtime dependencies
USER root
RUN apt-get update && apt-get install -y \
    fping \
    && rm -rf /var/lib/apt/lists/*

VOLUME ["/etc/vaping", "/var/run"]

CMD ["vaping", "start", "--debug"]
