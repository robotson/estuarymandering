#!/usr/bin/env python3
"""
THE UNITED SUBBASINS OF AMERICA — complete edition

The hero map (render_map.py) draws CONUS + Alaska + main-Hawaiʻi. This second
map seats the whole republic: Puerto Rico & the U.S. Virgin Islands, Guam &
the Northern Marianas, and American Samoa get insets; the Northwestern
Hawaiian chain and the U.S. Minor Outlying Islands appear as off-scale
impressions (true arrangement, exaggerated size); and the nine wholly-Canadian
headwater basins rise dimmed past the frame, stopped only by the sheet edge.
Every basin in the dataset lands on the sheet in some register; the map lets
that speak for itself (the console print carries the full accounting).

Pass --dpi 80 for quick proofs; default 300 for print.
"""
import os, argparse, hashlib, colorsys, warnings
import geopandas as gpd
from shapely.affinity import translate

# buffering in geographic degrees is a deliberate visual exaggeration of
# sub-pixel islands, not analysis — the precision warning doesn't apply
warnings.filterwarnings("ignore", message="Geometry is in a geographic CRS")
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "huc8_raw.geojson")
OUT  = os.path.join(ROOT, "outputs"); os.makedirs(OUT, exist_ok=True)
BG   = "#0d1117"
INK  = "#8b949e"
cli = argparse.ArgumentParser(description=__doc__)
cli.add_argument("--dpi", type=int, default=300, help="80 for quick proofs")
cli.add_argument("--debug", action="store_true",
                 help="outline the inset boxes to check for collisions")
args  = cli.parse_args()
DPI   = args.dpi
DEBUG = args.debug

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

# basins lying wholly outside the US keep their hue but recede toward the
# ground — drawn by the river, not seated in the union
BG_RGB  = matplotlib.colors.to_rgb(BG)
DIM     = 0.60                                  # 0 = full color, 1 = vanishes
foreign = g.states.isin(["CN", "MX"])
g.loc[foreign, "color"] = g.loc[foreign, "color"].map(
    lambda c: tuple((1 - DIM) * ch + DIM * bg for ch, bg in zip(c, BG_RGB)))

cen = g.geometry.representative_point()
g["lon"] = cen.x; g["lat"] = cen.y

mainland = g[~g.huc2.isin(["19", "20", "21", "22"])]   # incl. 9 Canadian
                                                       # headwaters above the frame
conus    = g[(g.lon > -125) & (g.lon < -66) & (g.lat > 24) & (g.lat < 50)]
ak       = g[g.huc2 == "19"]
hi       = g[(g.huc2 == "20") & (g.lon > -160.5)]      # main 8 islands
nwhi     = g[(g.huc2 == "20") & (g.lon <= -160.5)]     # Northwestern Hawaiian chain
pr       = g[g.huc2 == "21"]                           # Puerto Rico + USVI
# region 22 partitions cleanly by the states field (GU/MP, AS, UM) — sturdier
# than lon/lat walls if the WBD revises a unit
marianas = g[g.states.isin(["GU", "MP"])]              # Guam + CNMI
samoa    = g[g.states == "AS"]                         # American Samoa
atolls   = g[g.states == "UM"]                         # U.S. Minor Outlying Islands

def proj(df, crs, buffer_deg=0.0):
    df = df.copy()
    if buffer_deg:
        df["geometry"] = df.geometry.buffer(buffer_deg)   # exaggerate sub-pixel islands
    return df.to_crs(crs)

main_p  = proj(mainland, 5070)         # Albers Equal Area (CONUS + clipped CN)
ak_p    = proj(ak, "EPSG:3338")        # Alaska Albers
hi_p    = proj(hi, "EPSG:32604")       # UTM 4N
pr_p    = proj(pr, "EPSG:32620", 0.025)        # UTM 20N (nudge so the USVI read)
mar_p   = proj(marianas, "EPSG:32655", 0.15)   # UTM 55N
sam_p   = proj(samoa, "EPSG:32702", 0.13)      # UTM 2S

# the two impressions stay in plain lat/lon — true arrangement, dot-scale
# exaggeration far beyond the buffered insets above
nwhi_i = nwhi.copy();   nwhi_i["geometry"]   = nwhi_i.geometry.buffer(0.45)
atolls_i = atolls.copy()
atolls_i["geometry"] = [t if t.centroid.x > 0 else translate(t, xoff=360)
                        for t in atolls_i.geometry]    # unwrap the dateline
atolls_i["geometry"] = atolls_i.geometry.buffer(1.0)

fig = plt.figure(figsize=(26, 17), dpi=DPI); fig.patch.set_facecolor(BG)
ax = fig.add_axes([0.0, 0.0, 1.0, 0.93]); ax.set_facecolor(BG)
in_frame = main_p.index.isin(conus.index)
main_p.loc[in_frame].plot(ax=ax, color=main_p.loc[in_frame, "color"].tolist(),
                          edgecolor=BG, linewidth=0.18)
# the 9 wholly-Canadian headwater basins draw unclipped: the frame stays on
# the US extent and they simply keep going up, stopped only by the sheet edge
if (~in_frame).any():   # an empty plot adds no collection; [-1] would unclip CONUS
    main_p.loc[~in_frame].plot(ax=ax, color=main_p.loc[~in_frame, "color"].tolist(),
                               edgecolor=BG, linewidth=0.18)
    ax.collections[-1].set_clip_on(False)
ax.set_axis_off()
xmin, ymin, xmax, ymax = main_p.loc[in_frame].total_bounds
ax.set_xlim(xmin, xmax); ax.set_ylim(ymin, ymax)

BASELINE = 0.016        # one shared baseline for the bottom row of labels
                        # (va="baseline" aligns the LAST line of multiline text)

def inset(rect, df, lw, label=None, label_at=None, fontsize=13):
    """label on the shared bottom baseline; label_at=(x, y, ha, va) overrides."""
    a = fig.add_axes(rect); a.set_facecolor(BG)
    df.plot(ax=a, color=df["color"].tolist(), edgecolor=BG, linewidth=lw)
    a.set_axis_off()
    if DEBUG:
        fig.add_artist(plt.Rectangle(rect[:2], rect[2], rect[3], fill=False,
                                     edgecolor="red", linewidth=1.5,
                                     transform=fig.transFigure))
    if label:
        x, y, ha, va = label_at or (rect[0] + rect[2] / 2, BASELINE,
                                    "center", "baseline")
        fig.text(x, y, label, ha=ha, va=va, color=INK, fontsize=fontsize)
    return a

# Alaska and Hawaiʻi keep the hero map's corner; the two western-Pacific
# territories borrow the open Gulf, the Caribbean sits off Florida.
inset([0.002, 0.030, 0.185, 0.225], ak_p,  0.15, "ALASKA")
inset([0.198, 0.030, 0.072, 0.100], hi_p,  0.35, "HAWAIʻI")
inset([0.527, 0.012, 0.034, 0.108], mar_p, 0.35, "GUAM &\nN. MARIANAS",
      label_at=(0.568, BASELINE, "left", "baseline"))
inset([0.640, 0.030, 0.050, 0.070], sam_p, 0.35, "AMERICAN SAMOA")
inset([0.845, 0.045, 0.135, 0.095], pr_p,  0.35, "PUERTO RICO\n& U.S.V.I.",
      label_at=(0.9125, BASELINE, "center", "baseline"))

# off-scale impressions: true arrangement, exaggerated to dots
inset([0.196, 0.150, 0.070, 0.034], nwhi_i, 0.3, "NW HAWAIIAN CHAIN",
      label_at=(0.231, 0.142, "center", "top"), fontsize=10)
inset([0.862, 0.165, 0.105, 0.080], atolls_i, 0.3, "U.S. MINOR OUTLYING ISLANDS",
      label_at=(0.9145, 0.157, "center", "top"), fontsize=10)

parts     = (mainland, ak, hi, nwhi, pr, marianas, samoa, atolls)
drawn_idx = mainland.index
for part in parts[1:]:
    drawn_idx = drawn_idx.union(part.index)
missing = len(g) - len(drawn_idx)
if missing:                                    # every basin must land somewhere
    print(f"  ! WARNING: {missing} basins fell through the filters")
n_dim  = int(foreign[drawn_idx].sum())         # wholly Canadian/Mexican basins
n_clip = int((main_p.geometry.bounds["maxy"] > ymax).sum())   # truly cut by the frame
fig.text(0.5, 0.983, "THE UNITED SUBBASINS OF AMERICA", ha="center", va="top",
         color="#f0f6fc", fontsize=42, fontweight="bold")
fig.text(0.5, 0.946,
         f"A speculative map of all {len(g):,} HUC8 watershed subbasins, "
         f"redrawn as legislative districts.",
         ha="center", va="top", color=INK, fontsize=17)

png = os.path.join(OUT, "united_subbasins_all_territories.png")
pdf = os.path.join(OUT, "united_subbasins_all_territories.pdf")
fig.savefig(png, dpi=DPI, facecolor=BG)
saved = png
if DPI >= 300:   # the PDF is resolution-independent; skip it for quick proofs
    fig.savefig(pdf, facecolor=BG)
    saved += f"\n      {pdf}"
print(f"saved {saved}")
print(f"mainland {len(mainland)} (clipped cn {n_clip})  ak {len(ak)}  hi {len(hi)}  "
      f"nwhi {len(nwhi)}  pr+usvi {len(pr)}  marianas {len(marianas)}  "
      f"samoa {len(samoa)}  atolls {len(atolls)}  dimmed {n_dim}  missing {missing}")
