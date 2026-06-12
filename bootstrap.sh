#!/usr/bin/env bash
#
# Fetch the HUC8 watershed subbasins from the USGS WBD REST service into
# data/huc8_raw.geojson — a few MB of paginated API calls, no 3 GB download.
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$ROOT"
mkdir -p data outputs

if [ -f data/huc8_raw.geojson ]; then
  echo "==> data/huc8_raw.geojson already present — nothing to do."
  echo "    (delete it to refetch from USGS.)"
  exit 0
fi

echo "==> Fetching HUC8 subbasins from the USGS WBD REST service…"
python3 scripts/fetch_huc8.py
echo ""
echo "Done. Render it with:  make map     (or: python3 scripts/render_map.py)"
