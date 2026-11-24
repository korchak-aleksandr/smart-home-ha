#!/usr/bin/env bash
# Download community dashboards from grafana.com at pinned revisions and wire them to the VictoriaMetrics datasource.
#
# They are not committed to this repo (third-party content). Run on the server after deploying the stack:
#   ssh homeserver 'bash -s' < scripts/fetch-grafana-dashboards.sh
# Grafana picks up new files within ~30 seconds (provisioning, folder "Community").
set -euo pipefail
DEST="${1:-/opt/smart-home/monitoring/grafana/dashboards/community}"
DATASOURCE_UID="victoriametrics"

# id:revision:file  (bump the revision deliberately, like any other pinned version)
DASHBOARDS=(
  "1860:46:node-exporter-full.json"           # host: CPU, memory, disks, network, ...
  "15798:16:docker-monitoring.json"           # containers (cAdvisor)
  "22604:4:smartctl.json"                     # SSD SMART (smartctl_exporter)
  "10229:61:victoriametrics.json"             # the metrics database itself
)

mkdir -p "$DEST"
for entry in "${DASHBOARDS[@]}"; do
  IFS=: read -r id rev file <<<"$entry"
  url="https://grafana.com/api/dashboards/${id}/revisions/${rev}/download"
  curl -fsSL "$url" | python3 -c '
import json, re, sys
uid, d = sys.argv[1], json.load(sys.stdin)
# Replace datasource template inputs like ${DS_PROMETHEUS} with our datasource uid.
names = [i["name"] for i in d.pop("__inputs", []) if i.get("type") == "datasource"]
s = json.dumps(d)
for n in names:
    s = s.replace("${%s}" % n, uid)
d = json.loads(s)
d["id"] = None
json.dump(d, sys.stdout, indent=1)
' "$DATASOURCE_UID" > "$DEST/$file.tmp"
  mv "$DEST/$file.tmp" "$DEST/$file"
  echo "fetched ${id} rev ${rev} -> ${file}"
done
