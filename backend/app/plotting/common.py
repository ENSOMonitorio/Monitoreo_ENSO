"""
Constantes y helpers compartidos por los módulos de graficado ENSO
(cajas Niño, mapa base de cartopy, recorte de whitespace, etc.).
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")  # sin display — servidor headless
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import cartopy.crs as ccrs
import cartopy.feature as cfeature

EXTENT_PACIFICO = [115, 360 - 30, -21, 21]

# Paleta única de las cajas Niño — mismo color de contorno Y de área
# rellena en TODOS los mapas del dashboard (TSM, anomalía, viento, SLP,
# composite de subsuperficie). Antes cada mapa usaba colores distintos
# (negro/rojo/azul sin relleno en unos, otra paleta en otros).
NINO_COLORS = {
    "Niño 4":   "#7b1fa2",
    "Niño 3.4": "#1565c0",
    "Niño 3":   "#2e7d32",
    "Niño 1+2": "#c62828",
}

# Cajas Niño en convención 0-360, límites reales (lon Y lat — mismos que
# indices.py NINO_REGIONS_0_360) para el mapa/paneles del corte
# subsuperficial. lon0, lon1, lat0, lat1, color.
NINO_REGIONS_EQ = {
    "Niño 4":   (160, 210, -5, 5, NINO_COLORS["Niño 4"]),
    "Niño 3.4": (190, 240, -5, 5, NINO_COLORS["Niño 3.4"]),
    "Niño 3":   (210, 270, -5, 5, NINO_COLORS["Niño 3"]),
    "Niño 1+2": (270, 280, -10, 0, NINO_COLORS["Niño 1+2"]),
}

NINO_BOXES = {
    "Niño 3.4": dict(xy=(-170, -5), width=50, height=10, label_xy=(-150, 7)),
    "Niño 1+2": dict(xy=(-90, -10), width=10, height=10, label_xy=(-90, 2)),
    "Niño 3": dict(xy=(-150, -5), width=60, height=10, label_xy=(-120, 7)),
    "Niño 4": dict(xy=(160, -5), width=50, height=10, label_xy=(180, 7)),
}


def _autocrop_whitespace(path, pad=14, max_gap=40):
    """Recorta el margen blanco sobrante que deja cartopy cuando el aspect
    ratio del `figsize` no coincide con el del extent geográfico: GeoAxes
    encoge y recentra su propio bounding box para mantener el aspect real
    (grados lat/lon), dejando franjas en blanco arriba/abajo — incluida una
    franja interna entre el título (anclado a la figura) y el mapa (dentro
    del axes encogido). Se opera sobre el PNG ya guardado en vez de tocar el
    layout de cartopy porque bbox_inches="tight" ya se probó y rompe el
    gridliner/colorbar (ver nota en _base_map): primero recorta el margen
    externo, después comprime cualquier franja de filas en blanco interna
    más larga que `max_gap` px."""
    from PIL import Image
    im = Image.open(path).convert("RGB")
    arr = np.asarray(im)
    non_white = np.any(arr < 250, axis=2)
    rows = np.where(non_white.any(axis=1))[0]
    cols = np.where(non_white.any(axis=0))[0]
    if rows.size == 0 or cols.size == 0:
        return
    top, bottom = max(int(rows.min()) - pad, 0), min(int(rows.max()) + pad, arr.shape[0])
    left, right = max(int(cols.min()) - pad, 0), min(int(cols.max()) + pad, arr.shape[1])
    arr = arr[top:bottom, left:right]

    row_has_content = np.any(arr < 250, axis=(1, 2))
    keep = np.ones(len(row_has_content), dtype=bool)
    i = 0
    while i < len(row_has_content):
        if row_has_content[i]:
            i += 1
            continue
        j = i
        while j < len(row_has_content) and not row_has_content[j]:
            j += 1
        if j - i > max_gap:
            keep[i + max_gap:j] = False
        i = j
    Image.fromarray(arr[keep]).save(path)


def _add_nino_boxes(ax):
    for name, b in NINO_BOXES.items():
        color = NINO_COLORS[name]
        ax.add_patch(mpatches.Rectangle(
            xy=b["xy"], width=b["width"], height=b["height"],
            facecolor=color, edgecolor="none", alpha=0.12,
            transform=ccrs.PlateCarree()))
        ax.add_patch(mpatches.Rectangle(
            xy=b["xy"], width=b["width"], height=b["height"],
            facecolor="none", edgecolor=color, linewidth=2,
            transform=ccrs.PlateCarree()))
        ax.text(*b["label_xy"], name, color=color, fontsize=9, fontweight="bold",
                transform=ccrs.PlateCarree())


def _base_map(figsize=(12, 6)):
    fig, ax = plt.subplots(1, 1, figsize=figsize,
                            subplot_kw={"projection": ccrs.PlateCarree(central_longitude=180)})
    ax.set_extent(EXTENT_PACIFICO, crs=ccrs.PlateCarree())
    ax.coastlines(resolution="50m")
    ax.add_feature(cfeature.BORDERS, linestyle=":", edgecolor="black")
    ax.add_feature(cfeature.LAND, edgecolor="black", facecolor="lightgray")
    ax.add_feature(cfeature.OCEAN)
    gl = ax.gridlines(draw_labels=True, x_inline=False, y_inline=False,
                       color="gray", linestyle="--", alpha=0.6,
                       xlocs=np.arange(-180, 180, 20), ylocs=np.arange(-90, 91, 5))
    gl.top_labels = gl.right_labels = False
    # nota: plt.tight_layout() no es compatible con GeoAxes de cartopy en esta
    # combinación de versiones (rompe el cierre del polígono del gridliner, y
    # savefig(bbox_inches="tight") recorta el mapa entero dejando solo el
    # colorbar) — se ajusta el layout a mano en su lugar.
    fig.subplots_adjust(left=0.06, right=0.90, top=0.90, bottom=0.12)
    return fig, ax


def _lon_label(x):
    x = x % 360
    return f"{int(round(x))}°E" if x <= 180 else f"{int(round(360 - x))}°W"


def _perspective_coeffs(src_pts, dst_pts):
    matrix = []
    for s, t in zip(src_pts, dst_pts):
        matrix.append([t[0], t[1], 1, 0, 0, 0, -s[0] * t[0], -s[0] * t[1]])
        matrix.append([0, 0, 0, t[0], t[1], 1, -s[1] * t[0], -s[1] * t[1]])
    a = np.array(matrix, dtype=float)
    b = np.array(src_pts, dtype=float).flatten()
    return np.linalg.lstsq(a, b, rcond=None)[0].tolist()
