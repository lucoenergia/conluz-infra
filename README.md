# conluz-infra

Infrastructure orchestration for the [Conluz](https://github.com/lucoenergia/conluz) energy management platform.

Each directory is an independently deployable role. Copy `.env.example` to `.env`, fill in the values, and run `docker compose up -d` on the target machine.

## Roles

| Role | Directory | Services |
|---|---|---|
| Reverse proxy | `proxy/` | nginx |
| MQTT broker | `mqtt/broker/` | mosquitto |
| MQTT collector | `mqtt/collector/` | telegraf |
| Application | `app/` | conluz-api, conluz-web, postgres, influxdb |
| Monitoring | `monitoring/` | prometheus, alertmanager, node-exporter |
| Log aggregation | `logging/` | loki, promtail |
| Visualization | `supervisor/` | grafana |


## Quick start

```bash
# 1. Go to the role directory
cd proxy/

# 2. Create your .env from the example
cp .env.example .env
$EDITOR .env

# 3. Start the stack
docker compose up -d

# 4. Verify
docker compose ps
```

## Role reference

### proxy

Nginx reverse proxy. Routes `/api/` to conluz-api and `/` to conluz-web. SSL is terminated upstream (for example by Cloudflare) — nginx listens on port 80 only.

The nginx config is a template (`nginx/templates/conluz.conf.template`) processed at container start via `envsubst`.

| Variable | Description |
|---|---|
| `APP_HOST` | IP or hostname of the app machine |
| `APP_API_PORT` | Port exposed by conluz-api (default: 8080) |
| `APP_WEB_PORT` | Port exposed by conluz-web (default: 80) |

### mqtt/broker

Eclipse Mosquitto MQTT broker. Receives messages from IoT devices and smart meters over TCP (1883).

For production, set `allow_anonymous false` in `mosquitto/mosquitto.conf` and configure a password file.

### mqtt/collector

Telegraf agent. Subscribes to MQTT topics on the broker and writes metrics to InfluxDB 1.8.

| Variable | Description |
|---|---|
| `MQTT_BROKER_HOST` | IP or hostname of the MQTT broker machine |
| `MQTT_BROKER_PORT` | MQTT broker port (default: 1883) |
| `MQTT_TOPICS` | Topics to subscribe, comma-separated (default: `#`) |
| `INFLUXDB_HOST` | IP or hostname of the app machine |
| `INFLUXDB_DB` | InfluxDB database name |

### app

Conluz application stack: REST API, web frontend, PostgreSQL, and InfluxDB 1.8.

Images are pulled from the GitHub Container Registry. Set `CONLUZ_API_VERSION` and `CONLUZ_WEB_VERSION` to a specific tag in production.

The `SPRING_*` and `INFLUXDB_*` environment variables in `docker-compose.yml` follow Spring Boot conventions — adjust property names if they differ in the conluz-api `application.properties`.

### monitoring

Prometheus (metrics collection), Alertmanager (email alerts), and Node Exporter (host metrics).

Prometheus uses native environment variable expansion (`$VAR`) in its config file (supported in Prometheus 2.43+). Alertmanager does not — its config is processed with `envsubst` at container start.

| Variable | Description |
|---|---|
| `APP_HOST` | IP/hostname of the app machine (for conluz-api + influxdb scrape) |
| `LOKI_HOST` | IP/hostname of the logging machine |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server for alert emails |
| `ALERT_RECEIVER_EMAIL` | Destination for alert notifications |

Alert rules are in `monitoring/prometheus/rules/`:
- `node.yml` — CPU, memory, disk thresholds
- `app.yml` — service down, high error rate, high latency

### logging

Loki (log storage) and Promtail (log shipper). Promtail discovers all Docker containers via the Docker socket and ships their logs to Loki, labelled by container name and compose service.

Default retention: 31 days (`744h`). Adjust `LOKI_RETENTION_PERIOD` in `.env`.

### supervisor

Grafana. Prometheus and Loki datasources are auto-provisioned from environment variables. Dashboards are loaded from `provisioning/dashboards/`.

| Variable | Description |
|---|---|
| `PROMETHEUS_URL` | Full URL to Prometheus (e.g. `http://192.168.1.x:9090`) |
| `LOKI_URL` | Full URL to Loki (e.g. `http://192.168.1.x:3100`) |
| `GF_SECURITY_ADMIN_PASSWORD` | Grafana admin password |

**Node Exporter Full dashboard**: The included `node-exporter.json` is a placeholder. Download the real dashboard from [grafana.com/grafana/dashboards/1860](https://grafana.com/grafana/dashboards/1860) and replace the file.

## Updating images

```bash
cd <role-directory>
docker compose pull
docker compose up -d
```
