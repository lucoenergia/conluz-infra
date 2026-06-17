.PHONY: export up down logs clean

# Pull dashboards + datasources from the Pi into ./provisioning
export:
	@set -a; . ./.env; set +a; python3 export-from-grafana.py

# Start the local clone
up:
	docker compose up -d
	@echo "Grafana -> http://localhost:3000 (admin / $${GF_ADMIN_PASSWORD:-admin})"

down:
	docker compose down

logs:
	docker compose logs -f grafana

# Remove the local Grafana volume (fresh state on next `up`)
clean:
	docker compose down -v
