#!/usr/bin/env python3
"""
Export dashboards and datasources from a running Grafana instance into
provisioning files, so a local Grafana can be rebuilt reproducibly.

What this DOES export:
  - All datasources: structure + UID (UID is pinned so dashboards resolve).
  - All dashboards (type=dash-db): the raw dashboard model.

What this does NOT export (Grafana API limitation, by design):
  - Datasource secrets (passwords/tokens). `secureJsonData` is write-only.
    They are templated as ${ENV_VARS} and injected at runtime via .env.
  - Alert rules, contact points, users, orgs, library panels.

Why /api/dashboards/uid (not the UI "Export for sharing" JSON):
  The sharing export rewrites datasources into `__inputs`, which breaks file
  provisioning. The raw model references datasources by UID directly.

Usage:
  GRAFANA_URL=http://<remote-grafana-host-ip>:3000 \
  GRAFANA_TOKEN=<service-account-token-with-Admin-role> \
  python3 export-from-grafana.py
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

try:
    import yaml
except ImportError:
    sys.exit("Missing PyYAML. Install with: pip install pyyaml")

GRAFANA_URL = os.environ.get("GRAFANA_URL", "").rstrip("/")
TOKEN = os.environ.get("GRAFANA_TOKEN", "")
if not GRAFANA_URL or not TOKEN:
    sys.exit("Set GRAFANA_URL and GRAFANA_TOKEN environment variables.")

BASE = pathlib.Path(__file__).resolve().parent
DS_DIR = BASE / "provisioning" / "datasources"
DASH_JSON_DIR = BASE / "provisioning" / "dashboards" / "json"
DS_DIR.mkdir(parents=True, exist_ok=True)
DASH_JSON_DIR.mkdir(parents=True, exist_ok=True)


def api(path):
    req = urllib.request.Request(
        f"{GRAFANA_URL}{path}",
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        sys.exit(f"HTTP {exc.code} on {path}: {exc.read().decode(errors='ignore')}")


def secure_block(ds_type):
    """Templated secret keys per datasource type. Grafana interpolates ${VARS}
    from the environment at provisioning load time. Unused keys are ignored."""
    if ds_type == "influxdb":
        # v2/v3 use a token; v1 uses a password. Keep both; set the one you need.
        return {"token": "${INFLUXDB_TOKEN}", "password": "${INFLUXDB_PASSWORD}"}
    # Unknown type: add the right secret keys here manually if it needs auth.
    return {}


# ---- datasources -----------------------------------------------------------
datasources = api("/api/datasources")
ds_doc = {"apiVersion": 1, "datasources": []}
for ds in datasources:
    entry = {
        "name": ds["name"],
        "uid": ds["uid"],          # CRITICAL: pin UID so dashboards resolve
        "type": ds["type"],
        "access": ds.get("access", "proxy"),
        # URL templated so local can point at Pi (Tailscale) or a local stack.
        "url": "${INFLUXDB_URL}" if ds["type"] == "influxdb" else ds.get("url", ""),
        "isDefault": ds.get("isDefault", False),
        "jsonData": ds.get("jsonData", {}),
        "editable": False,
    }
    for opt in ("user", "database", "basicAuth", "basicAuthUser"):
        if ds.get(opt):
            entry[opt] = ds[opt]
    sec = secure_block(ds["type"])
    if sec:
        entry["secureJsonData"] = sec
    ds_doc["datasources"].append(entry)
    print(f"  datasource: {ds['name']} ({ds['type']}, uid={ds['uid']})")

(DS_DIR / "datasources.yaml").write_text(
    yaml.safe_dump(ds_doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
)
print(f"==> {len(datasources)} datasource(s) -> {DS_DIR / 'datasources.yaml'}")

# ---- dashboards ------------------------------------------------------------
search = api("/api/search?type=dash-db")
for item in search:
    full = api(f"/api/dashboards/uid/{item['uid']}")
    dash = full["dashboard"]
    dash["id"] = None  # let Grafana manage the numeric id for provisioned boards
    out = DASH_JSON_DIR / f"{item['uid']}.json"
    out.write_text(json.dumps(dash, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  dashboard: {dash.get('title')} (uid={item['uid']})")
print(f"==> {len(search)} dashboard(s) -> {DASH_JSON_DIR}")
print("Done. Review the files, set secrets in .env, then `make up`.")
