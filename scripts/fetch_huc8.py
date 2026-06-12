#!/usr/bin/env python3
"""
Fetch every HUC8 watershed subbasin from the USGS WBD ArcGIS REST service into
data/huc8_raw.geojson, plus a small data/manifest.json recording provenance.

No multi-gigabyte GeoDatabase — a count preflight, then a couple of paginated
calls, geometry generalized server-side to web weight. Standard library only;
geopandas isn't needed until you render.

WBD MapServer layer 4 = "8-digit HU (Subbasin)" = HUC8.
"""
import json, os, time, datetime, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data"); os.makedirs(DATA, exist_ok=True)
OUT      = os.path.join(DATA, "huc8_raw.geojson")
MANIFEST = os.path.join(DATA, "manifest.json")

SERVICE    = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer"
LAYER      = 4         # "8-digit HU (Subbasin)" = HUC8
PAGE       = 2000      # the service's maxRecordCount
OFFSET_DEG = 0.002     # server-side generalization → web-weight geometry

def query(params):
    url = f"{SERVICE}/{LAYER}/query?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=180) as r:
        body = json.loads(r.read().decode("utf-8"))
    if "error" in body:   # ArcGIS reports failures as HTTP 200 + an error payload
        raise SystemExit(f"WBD service error: {body['error']}")
    return body

# preflight: how many subbasins should we get? (also the progress denominator)
expected = query({"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
if not expected:
    raise SystemExit("WBD count preflight returned 0 — not overwriting local data")
print(f"WBD layer {LAYER} reports {expected:,} HUC8 subbasins — fetching…")

# page until the server runs dry (an empty page), not until the preflight
# count is met — a short page may just be the transfer limit, and the count
# may be stale in either direction
features, offset = [], 0
while True:
    got = query({
        "where": "1=1",                       # no geographic filter → AK/HI/PR/GU/AS included
        "outFields": "huc8,name,states,areasqkm",
        "returnGeometry": "true",
        "outSR": "4326",
        "maxAllowableOffset": str(OFFSET_DEG),
        "f": "geojson",                       # native GeoJSON (no Esri-JSON conversion)
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE),
    }).get("features", [])
    if not got:
        break
    features.extend(got)
    print(f"  …{len(features):,}/{expected:,}")
    offset += len(got)
    time.sleep(0.3)

# normalize property keys to lowercase: huc8 / name / states / areasqkm
for f in features:
    f["properties"] = {k.lower(): v for k, v in (f.get("properties") or {}).items()}

# integrity check — a truncated fetch should be loud, not silent
status = "complete" if len(features) >= expected else "INCOMPLETE"

json.dump({
    "source": SERVICE,
    "layer": LAYER,
    "layer_name": "8-digit HU (Subbasin) / HUC8",
    "query": "where=1=1 (no geographic filter — includes AK, HI, PR, GU, AS)",
    "generalization_maxAllowableOffset_deg": OFFSET_DEG,
    "expected_count": expected,
    "feature_count": len(features),
    "status": status,
    "fetched_utc": datetime.datetime.now(datetime.timezone.utc)
                   .isoformat(timespec="seconds").replace("+00:00", "Z"),
}, open(MANIFEST, "w"), indent=2)
print(f"Wrote provenance   -> {MANIFEST}")

if status == "INCOMPLETE":   # don't cache a truncated file; bootstrap would trust it
    raise SystemExit(f"expected {expected:,}, got {len(features):,} — "
                     f"refusing to write {OUT}")

json.dump({"type": "FeatureCollection", "features": features}, open(OUT, "w"))
print(f"Wrote {len(features):,} subbasins -> {OUT}")
