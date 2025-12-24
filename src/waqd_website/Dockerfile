# docker build --tag waqd_website:latest . -f src/waqd_website/Dockerfile
FROM python:3.13-alpine3.22 AS base

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apk add --no-cache --virtual .build-deps \
    mariadb-connector-c-dev \
    mariadb-dev \
    build-base

RUN adduser -D waqd

USER waqd
WORKDIR /home/waqd

RUN python -m venv pdm-venv && \
    . pdm-venv/bin/activate && \
    pip install --upgrade pip && \
    pip install pdm

COPY --chown=waqd:waqd pyproject.toml pdm.lock LICENSE README.md ./
COPY --chown=waqd:waqd src/waqd_website/__init__.py src/waqd_website/__init__.py

RUN . pdm-venv/bin/activate && pdm install -G website && rm -rf ~/.cache/pdm

COPY --chown=waqd:waqd src/waqd src/waqd
COPY --chown=waqd:waqd src/waqd_website src/waqd_website

# Switch back to root to uninstall build dependencies and install runtime ones
USER root
RUN apk del .build-deps && \
    apk add --no-cache mariadb-connector-c

USER waqd

ENTRYPOINT ["/bin/sh", "-c", ". ./pdm-venv/bin/activate && uvicorn waqd_website.main:web_app --host 0.0.0.0 --port 8080"]
