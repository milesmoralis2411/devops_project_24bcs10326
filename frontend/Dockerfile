# syntax=docker/dockerfile:1

# ---- Stage 1: build the React app with Node -----------------------------------
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---- Stage 2: serve static files with unprivileged Nginx ----------------------
# nginx-unprivileged runs as UID 101 and listens on 8080, so no root and no
# privileged port is needed. Node, npm and the source never reach this image.
FROM nginxinc/nginx-unprivileged:1.30-alpine AS runtime

LABEL org.opencontainers.image.title="stockpilot-frontend" \
      org.opencontainers.image.description="StockPilot inventory dashboard (React + Nginx)"

ENV BACKEND_URL=http://backend:8000

# Pull in Alpine security fixes published after the base image was built
# (e.g. zlib 1.3.2-r1 for CVE-2026-85091), then drop back to the unprivileged user.
USER root
RUN apk upgrade --no-cache
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html

USER 101
EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/healthz || exit 1
