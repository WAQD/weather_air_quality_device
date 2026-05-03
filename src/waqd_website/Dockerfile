# syntax=docker/dockerfile:1
# docker build --tag waqd_website:latest . -f src/waqd_website/Dockerfile
# Stage 1: Build the Vue.js frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY src/waqd_assets ./src/waqd_assets
COPY src/waqd_website/ui/package*.json ./src/waqd_website/ui/
RUN cd src/waqd_website/ui && npm ci
COPY src/waqd_website/ui/ ./src/waqd_website/ui/
RUN cd src/waqd_website/ui && npm run build

# Stage 2: Build the Python server
FROM python:3.14-alpine3.23 AS base

ENV DEBIAN_FRONTEND=noninteractive
RUN adduser -D waqd
USER waqd
WORKDIR /home/waqd

RUN python -m venv pdm-venv && \
    . pdm-venv/bin/activate && \
    pip install --upgrade pip && \
    pip install pdm

COPY --chown=waqd:waqd pyproject.toml pdm.lock LICENSE README.md ./
COPY --chown=waqd:waqd src/waqd_website/__init__.py src/waqd_website/__init__.py

RUN . pdm-venv/bin/activate && \
    pdm install --frozen-lockfile -G website && \
    rm -rf ~/.cache

COPY --chown=waqd:waqd src/waqd src/waqd
# Exclude the frontend source folder from the final image
COPY --exclude=ui --chown=waqd:waqd src/waqd_website src/waqd_website

# Copy the built frontend from Stage 1
COPY --from=frontend-builder --chown=waqd:waqd /app/src/waqd_website/ui/dist /home/waqd/src/waqd_website/ui/dist

ENTRYPOINT ["/bin/sh", "-c", ". ./pdm-venv/bin/activate && uvicorn waqd_website.main:web_app --host 0.0.0.0 --port 8080"]
EXPOSE 8080