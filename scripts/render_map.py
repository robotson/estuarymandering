#!/usr/bin/env python3
"""
THE UNITED SUBBASINS OF AMERICA

Dark-ground, HUC2-region-hue map of every HUC8 watershed subbasin: CONUS in
Albers equal-area, with an Alaska inset and a small main-islands Hawaiʻi inset
tucked in beside it. Reads data/huc8_raw.geojson (see bootstrap.sh).
"""
import os, hashlib, colorsys
import geopandas as gpd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "huc8_raw.geojson")
OUT  = os.path.join(ROOT, "outputs"); os.makedirs(OUT, exist_ok=True)
BG   = "#0d1117"

if not os.path.exists(DATA):
    raise SystemExit(f"{DATA} not found — run  bash bootstrap.sh  first.")

g = gpd.read_file(DATA)
g = g[g.geometry.notnull()].copy()
g["huc8"] = g["huc8"].astype(str).str.zfill(8)
g["huc2"] = g["huc8"].str[:2]

# --- coloring: a base hue per HUC2 region + deterministic per-subbasin jitter ---
regions = sorted(g["huc2"].unique())
hue_for = {r: i / len(regions) for i, r in enumerate(regions)}
def color_for(huc8, huc2):
    base = hue_for[huc2]
    h = int(hashlib.md5(huc8.encode()).hexdigest(), 16)
    dh = ((h % 1000) / 1000 - 0.5) * 0.07
    s  = 0.45 + ((h >> 10) % 1000) / 1000 * 0.40
    l  = 0.45 + ((h >> 20) % 1000) / 1000 * 0.30
    return colorsys.hls_to_rgb((base + dh) % 1.0, l, s)
g["color"] = [color_for(r.huc8, r.huc2) for r in g.itertuples()]

cen = g.geometry.representative_point()
g["lon"] = cen.x; g["lat"] = cen.y

conus = g[(g.lon > -125) & (g.lon < -66) & (g.lat > 24) & (g.lat < 50)]
ak    = g[g.huc2 == "19"]
hi    = g[(g.huc2 == "20") & (g.lon > -160.5)]      # main 8 islands (drop the NW chain)

conus_p = conus.to_crs(5070)            # Albers Equal Area (CONUS)
ak_p    = ak.to_crs("EPSG:3338")        # Alaska Albers
hi_p    = hi.to_crs("EPSG:32604")       # UTM 4N — tidy for the main Hawaiian islands

fig = plt.figure(figsize=(26, 17), dpi=300); fig.patch.set_facecolor(BG)
ax = fig.add_axes([0.0, 0.0, 1.0, 0.93]); ax.set_facecolor(BG)
conus_p.plot(ax=ax, color=conus_p["color"].tolist(), edgecolor=BG, linewidth=0.18)
ax.set_axis_off()
xmin, ymin, xmax, ymax = conus_p.total_bounds
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)

# Alaska inset, lower-left
axa = fig.add_axes([0.01, 0.02, 0.20, 0.24]); axa.set_facecolor(BG)
ak_p.plot(ax=axa, color=ak_p["color"].tolist(), edgecolor=BG, linewidth=0.15)
axa.set_axis_off()

# a little Hawaiʻi, tucked just to the right of Alaska
axh = fig.add_axes([0.215, 0.035, 0.072, 0.105]); axh.set_facecolor(BG)
hi_p.plot(ax=axh, color=hi_p["color"].tolist(), edgecolor=BG, linewidth=0.35)
axh.set_axis_off()

fig.text(0.5, 0.975, "THE UNITED SUBBASINS OF AMERICA", ha="center", va="top",
         color="#f0f6fc", fontsize=42, fontweight="bold")
fig.text(0.5, 0.945,
         f"A speculative map of {len(g):,} HUC8 watershed subbasins, redrawn as "
         f"legislative districts — one representative per watershed.",
         ha="center", va="top", color="#8b949e", fontsize=18)

png = os.path.join(OUT, "united_subbasins_with_hawaii.png")
pdf = os.path.join(OUT, "united_subbasins_with_hawaii.pdf")
fig.savefig(png, dpi=300, facecolor=BG)
fig.savefig(pdf, facecolor=BG)
print(f"saved {png}\n      {pdf}   |  conus {len(conus)}  ak {len(ak)}  hi {len(hi)}")
