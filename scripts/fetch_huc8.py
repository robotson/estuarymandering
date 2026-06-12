#!/usr/bin/env python3
"""
Download every HUC8 watershed subbasin straight from the USGS WBD ArcGIS REST
service into data/huc8_raw.geojson — no multi-gigabyte GeoDatabase, just a
couple of paginated API calls, generalized server-side to web weight.

WBD MapServer layer 4 = "8-digit HU (Subbasin)" = HUC8  (~2,456 features).
Standard library only; geopandas isn't needed until you render.
"""
import json, os, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "data", "huc8_raw.geojson")
os.makedirs(os.path.dirname(OUT), exist_ok=True)

BASE = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/4/query"
PAGE = 2000   # the service's maxRecordCount

def page(offset):
    q = {
        "where": "1=1",
        "outFields": "huc8,name,states,areasqkm",
        "returnGeometry": "true",
        "outSR": "4326",
        "maxAllowableOffset": "0.002",   # generalize server-side -> web-weight geometry
        "f": "geojson",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE),
    }
    url = BASE + "?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))

features, offset = [], 0
while True:
    got = page(offset).get("features", [])
    features.extend(got)
    print(f"  …{len(features):,} subbasins")
    if len(got) < PAGE:
        break
    offset += PAGE
    time.sleep(0.3)

# normalize property keys to lowercase: huc8 / name / states / areasqkm
for f in features:
    f["properties"] = {k.lower(): v for k, v in (f.get("properties") or {}).items()}

with open(OUT, "w") as fh:
    json.dump({"type": "FeatureCollection", "features": features}, fh)
print(f"Wrote {len(features):,} HUC8 subbasins -> {OUT}")
