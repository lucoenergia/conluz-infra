# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Infrastructure orchestration for the [Conluz](https://github.com/lucoenergia/conluz)
energy management platform. There is **no application code, build, or test step here** —
the repo is a collection of Docker Compose stacks. Each top-level directory is an
independently deployable *role*, intended to run on its own machine (or co-located as
needed). Services communicate across roles over the host network using IP/hostname
variables set in each role's `.env`.

## Working with a role

```bash
cd <role>/                 # e.g. proxy/, app/, monitoring/
cp .env.example .env       # then fill in values
docker compose up -d
docker compose ps          # verify
docker compose pull && docker compose up -d   # update images
docker compose logs -f <service>              # inspect a service
```

Roles and their services (see README.md for the full per-role variable reference):

| Role | Dir | Services |
|---|---|---|
| Reverse proxy | `proxy/` | nginx |
| MQTT broker | `mqtt/broker/` | mosquitto |
| MQTT collector | `mqtt/collector/` | telegraf |
| Application | `app/` | conluz-api, conluz-web, postgres, influxdb |
| Monitoring | `monitoring/` | prometheus, alertmanager, node-exporter |
| Log aggregation | `logging/` | loki, promtail |
| Visualization | `supervisor/` | grafana |

## Architecture notes that span multiple files

- **Roles are network-isolated.** Each compose file defines its own bridge network
  (`app-net`, `monitoring-net`, `logging-net`, …). Services in different roles reach
  each other only via host IPs/ports passed through `.env` (e.g. `APP_HOST`,
  `MQTT_BROKER_HOST`, `INFLUXDB_HOST`, `LOKI_URL`). When adding a cross-role connection,
  you wire it through an env var + an exposed port — not a shared Docker network.

- **Config files are templated three different ways — match the existing mechanism when
  editing a role's config:**
  - `envsubst` at container start via a custom `entrypoint`/`command` that writes to a
    temp file (e.g. `monitoring/` alertmanager, nginx via the official image's
    `/etc/nginx/templates` + `*.template` convention).
  - Native env-var expansion inside the tool's own config (Prometheus 2.43+ expands
    `$VAR` in `prometheus.yml` directly — no envsubst).
  - Plain `env_file: .env` injected into the container environment.

- **Two time-series stores.** PostgreSQL (relational app data) and InfluxDB 1.8
  (metrics/IoT readings) both live in `app/`. Telegraf in `mqtt/collector/` writes the
  MQTT stream into InfluxDB; conluz-api reads/writes both.

- **`app/conluz-api` env vars follow Spring Boot conventions** (`SPRING_DATASOURCE_*`,
  `INFLUXDB_*`). If a property name changes in the conluz-api `application.properties`,
  the corresponding key in `app/docker-compose.yml` must change to match.

- **Images come from GHCR** (`ghcr.io/lucoenergia/conluz`, `…/conluz-web`). Versions
  default to `latest` but should be pinned via `CONLUZ_API_VERSION` /
  `CONLUZ_WEB_VERSION` in production.

- **Observability agents need host access.** `node-exporter` (monitoring) mounts host
  `/proc`, `/sys`, `/` and uses `pid: host`; `promtail` (logging) mounts the Docker
  socket to auto-discover containers and `/var/log`. Preserve these mounts/privileges
  when editing those services.

## Secrets

`.env` and `**/.env` are gitignored. Only `.env.example` templates are committed — keep
real values out of compose files and commits, and update the matching `.env.example`
(and README variable table) whenever you introduce a new variable.
