"""Subsuperficie — corte ecuatorial y composite de Onda Kelvin."""

import os

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from PIL import Image as PILImage

from .common import NINO_REGIONS_EQ, _lon_label, _perspective_coeffs


def plot_equatorial_depth_section(band_mean_da, climatology_da, month, out_path,
                                   min_val=-3, max_val=3, levels=13, title_suffix=""):
    """Corte profundidad-longitud de anomalía de temperatura subsuperficial en
    la franja ecuatorial (Onda Kelvin) — `band_mean_da` ya debe venir promediado
    en latitud (dims: level, lon), en °C, para el mes a graficar. `climatology_da`
    trae dims (month, level, lon); se le resta el mes correspondiente."""
    anom = band_mean_da - climatology_da.sel(month=month)

    fig, ax = plt.subplots(figsize=(11, 5))
    contour_levels = np.linspace(min_val, max_val, levels)
    plot_obj = anom.plot.contourf(ax=ax, x="lon", y="level", levels=contour_levels,
                                   cmap="RdBu_r", add_colorbar=False, extend="both")
    ax.invert_yaxis()
    ax.set_xlabel("")
    ax.set_ylabel("Profundidad (m)", fontsize=10, fontweight="bold")
    ax.set_title(f"Anomalía de temperatura subsuperficial — corte ecuatorial (2°S-2°N){title_suffix}",
                 fontsize=13, fontweight="bold")
    xticks = anom["lon"].values[::40]
    ax.set_xticks(xticks)
    ax.set_xticklabels([_lon_label(x) for x in xticks])
    ax.text(0.01, -0.12, "Indonesia", transform=ax.transAxes, fontsize=9, ha="left")
    ax.text(0.99, -0.12, "Sudamérica", transform=ax.transAxes, fontsize=9, ha="right")
    ax.grid(True, linestyle="--", linewidth=0.4, alpha=0.4, color="gray")
    fig.subplots_adjust(left=0.09, right=0.90, top=0.88, bottom=0.16)
    cbar_ax = fig.add_axes([0.92, 0.16, 0.02, 0.72])
    cbar = fig.colorbar(plot_obj, cax=cbar_ax, orientation="vertical")
    cbar.set_label("Diferencia con el promedio (°C)", fontsize=9, fontweight="bold")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_subsurf_composite(band_mean_da, climatology_da, month, out_path, date_label,
                            nino_regions=NINO_REGIONS_EQ, min_depth=600):
    """Corte profundidad-longitud (temperatura observada + anomalía) con un
    mapa real (cartopy) inclinado en perspectiva pegado arriba, imitando los
    paneles ARGO/NOAA de referencia. La "inclinación 3D" es un efecto de
    imagen (PIL.Image.transform PERSPECTIVE sobre el mapa ya renderizado),
    no una superficie 3D real — mismo truco que usan esos paneles.
    `band_mean_da` dims (level, lon) en °C; `climatology_da` dims (month, level, lon)."""
    # Se trabaja todo en convención 0-360 (igual que el resto del pipeline):
    # nuestros datos cruzan la antimeridiana (120°E -> 290°E), así que pasar
    # a -180/180 y ordenar rompe la continuidad y deja un hueco en el medio.
    lons = band_mean_da["lon"].values
    depths = band_mean_da["level"].values
    obs = band_mean_da.values
    clim = climatology_da.sel(month=month).values
    anom = obs - clim

    fig = plt.figure(figsize=(15, 8))
    fig.patch.set_facecolor("white")
    gs = gridspec.GridSpec(2, 2, height_ratios=[5, 5], width_ratios=[20, 1],
                            hspace=0.09, wspace=0.03, left=0.07, right=0.92, top=0.95, bottom=0.08)
    ax_obs = fig.add_subplot(gs[0, 0])
    ax_anom = fig.add_subplot(gs[1, 0])
    ax_cb1 = fig.add_subplot(gs[0, 1])
    ax_cb2 = fig.add_subplot(gs[1, 1])

    im_obs = ax_obs.contourf(lons, depths, obs, levels=np.arange(5, 32, 1),
                              cmap="RdYlBu_r", extend="both")
    # Termoclina (isoterma de 20°C) resaltada — referencia estándar para ver
    # dónde está el límite superior de las aguas frías profundas.
    iso20 = ax_obs.contour(lons, depths, obs, levels=[20], colors="black", linewidths=2.0)
    ax_obs.clabel(iso20, inline=True, fontsize=9, fmt="%.0f°C")
    ax_obs.invert_yaxis()
    ax_obs.set_ylim(min_depth, 0)
    ax_obs.set_xlim(lons.min(), lons.max())
    ax_obs.set_ylabel("Profundidad (m)", fontsize=10)
    ax_obs.set_xticks([])
    ax_obs.grid(True, ls=":", alpha=0.25, color="gray")
    ax_obs.text(0.01, 0.97, f"T observada — {date_label}", transform=ax_obs.transAxes,
                fontsize=9, va="top", bbox=dict(facecolor="white", alpha=0.85, pad=2, edgecolor="none"))

    im_anom = ax_anom.contourf(lons, depths, anom, levels=np.arange(-3, 3.25, 0.25),
                                cmap="RdBu_r", extend="both")
    ax_anom.invert_yaxis()
    ax_anom.set_ylim(min_depth, 0)
    ax_anom.set_xlim(lons.min(), lons.max())
    ax_anom.set_ylabel("Profundidad (m)", fontsize=10)
    ax_anom.set_xlabel("Longitud", fontsize=10)
    xticks = lons[::max(len(lons) // 8, 1)]
    ax_anom.set_xticks(xticks)
    ax_anom.set_xticklabels([_lon_label(x) for x in xticks])
    ax_anom.grid(True, ls=":", alpha=0.25, color="gray")
    ax_anom.text(0.01, 0.97, f"Anomalía T — {date_label} vs climatología",
                 transform=ax_anom.transAxes, fontsize=9, va="top",
                 bbox=dict(facecolor="white", alpha=0.85, pad=2, edgecolor="none"))

    for ax_p in (ax_obs, ax_anom):
        for name, (lo0, lo1, _lat0, _lat1, color) in nino_regions.items():
            ax_p.axvspan(lo0, lo1, alpha=0.05, color=color)
            ax_p.axvline(lo0, color=color, lw=1, ls=":", alpha=0.7)
            ax_p.axvline(lo1, color=color, lw=1, ls=":", alpha=0.7)
    for name, (lo0, lo1, _lat0, _lat1, color) in nino_regions.items():
        if lo0 >= lons.min() and lo1 <= lons.max():
            ax_anom.text((lo0 + lo1) / 2, min_depth - 15, name, ha="center", fontsize=8,
                         color=color, fontweight="bold",
                         bbox=dict(facecolor="white", alpha=0.75, pad=1, edgecolor="none"))

    fig.colorbar(im_obs, cax=ax_cb1).set_label("T (°C)", fontsize=9)
    fig.colorbar(im_anom, cax=ax_cb2).set_label("Anomalía (°C)", fontsize=9)

    # Posición real del panel de datos (sin la barra de color) en fracción de
    # figura — punto de partida para alinear el mapa horizontalmente con los
    # paneles de abajo (si no, el width_ratios del gridspec deja el panel más
    # angosto que [0.07, 0.92] y las cajas Niño del mapa no calzan).
    data_pos = ax_obs.get_position()

    base_path = out_path.replace(".png", "_base.png")
    fig.savefig(base_path, dpi=150, facecolor="white")
    plt.close(fig)

    # El efecto de perspectiva más abajo encoge el borde SUPERIOR del mapa
    # (el que queda lejos de los paneles, "hacia el fondo") y deja el borde
    # INFERIOR (el que toca los paneles) sin tocar — por eso alcanza con que
    # el mapa use el mismo ancho horizontal que el panel, sin compensar nada.
    map_x0 = data_pos.x0
    map_width = data_pos.width

    # El título va en una imagen aparte (ver más abajo) para que NO se
    # incline con el mapa: todo lo que se dibuja dentro de fig_map pasa por
    # el warp de perspectiva más abajo, texto incluido — si el título
    # estuviera acá adentro, saldría torcido igual que el mapa.
    fig_map = plt.figure(figsize=(15, 3))
    fig_map.patch.set_facecolor("white")
    # bottom=0, height=1 (sin margen): el borde inferior de los ejes coincide
    # exacto con el borde inferior de la imagen — el que se deja sin encoger
    # en el warp de perspectiva y calza directo con el panel de abajo.
    ax_map = fig_map.add_axes([map_x0, 0, map_width, 1],
                               projection=ccrs.PlateCarree(central_longitude=180))
    ax_map.set_extent([lons.min(), lons.max(), -10, 10], crs=ccrs.PlateCarree())
    ax_map.add_feature(cfeature.OCEAN, facecolor="#d0e8f0", zorder=0)
    ax_map.add_feature(cfeature.LAND, facecolor="#e8dcc8", zorder=3)
    ax_map.add_feature(cfeature.COASTLINE, linewidth=0.6, zorder=4)
    ax_map.add_feature(cfeature.BORDERS, linewidth=0.3, linestyle=":", zorder=4)
    for name, (lo0, lo1, lat0, lat1, color) in nino_regions.items():
        if lo0 >= lons.min() and lo1 <= lons.max():
            # Límites reales de cada caja (no todas llegan a -10: Niño 1+2 sí,
            # 3.4/3/4 van de -5 a 5) — el borde inferior del extent (-10) es
            # el único que el warp de perspectiva deja sin encoger, así que
            # las cajas que no llegan hasta ahí quedan una aproximación
            # visual (unos px) en vez de calzar pixel-perfecto con el panel;
            # se prioriza que la caja sea geográficamente correcta.
            ax_map.add_patch(mpatches.Rectangle(
                (lo0, lat0), lo1 - lo0, lat1 - lat0, linewidth=1.2, edgecolor=color, facecolor=color,
                alpha=0.2, transform=ccrs.PlateCarree(), zorder=5))
            ax_map.text((lo0 + lo1) / 2, 7, name, ha="center", fontsize=8, fontweight="bold",
                        color=color, transform=ccrs.PlateCarree(), zorder=6)
    gl = ax_map.gridlines(draw_labels=True, linewidth=0.5, color="gray", alpha=0.5, linestyle="--")
    gl.top_labels = gl.right_labels = gl.bottom_labels = False
    gl.xlabel_style = {"size": 7, "color": "gray"}
    gl.ylabel_style = {"size": 7, "color": "gray"}
    ax_map.set_aspect("auto")

    map_path = out_path.replace(".png", "_map.png")
    fig_map.savefig(map_path, dpi=150, facecolor="white")
    plt.close(fig_map)

    # Título en su propia figura chica, sin projection ni warp — se pega
    # plano arriba del mapa ya inclinado, así que queda horizontal.
    fig_title = plt.figure(figsize=(15, 0.65))
    fig_title.patch.set_facecolor("white")
    fig_title.text(0.5, 0.62, f"Anomalía de temperatura subsuperficial — {date_label}",
                   ha="center", va="center", fontsize=14, fontweight="bold")
    fig_title.text(0.5, 0.16, "Pacífico ecuatorial (2°S-2°N) · NCEP GODAS · Climatología 2015-2024",
                   ha="center", va="center", fontsize=9, color="#555")
    title_path = out_path.replace(".png", "_title.png")
    fig_title.savefig(title_path, dpi=150, facecolor="white")
    plt.close(fig_title)

    # Combina título + mapa + paneles con PIL, aplicando la perspectiva solo
    # al mapa para que se vea como una "tapa" inclinada sobre los paneles
    # planos (el título y los paneles quedan sin distorsionar).
    img_base = PILImage.open(base_path).convert("RGBA")
    img_map = PILImage.open(map_path).convert("RGBA")
    img_title = PILImage.open(title_path).convert("RGBA")
    w, h = img_base.size
    map_h = int(h * 0.28)
    img_map = img_map.resize((w, map_h), PILImage.LANCZOS)
    mw, mh = img_map.size
    title_h = int(w / img_title.size[0] * img_title.size[1])
    img_title = img_title.resize((w, title_h), PILImage.LANCZOS)

    # Se encoge el borde SUPERIOR (el que queda lejos de los paneles, "hacia
    # el fondo") y se deja el INFERIOR intacto — es el que queda pegado a los
    # paneles, y así calza sin compensar nada. PIL espera coeficientes que
    # mapeen cada píxel de SALIDA a su posición de origen en la imagen fuente
    # (mapeo inverso), por eso src/dst van en ese orden y no al revés.
    shrink = 0.07
    src = [(0, 0), (mw, 0), (mw, mh), (0, mh)]
    dst = [(int(mw * shrink), 0), (int(mw * (1 - shrink)), 0), (mw, mh), (0, mh)]
    coeffs = _perspective_coeffs(src, dst)
    map_3d = img_map.transform((mw, mh), PILImage.PERSPECTIVE, coeffs, PILImage.BICUBIC)

    canvas = PILImage.new("RGBA", (w, title_h + map_h + h), (255, 255, 255, 255))
    canvas.paste(img_title, (0, 0), img_title)
    canvas.paste(map_3d, (0, title_h), map_3d)
    canvas.paste(img_base, (0, title_h + map_h), img_base)
    canvas.convert("RGB").save(out_path)

    os.remove(title_path)

    os.remove(base_path)
    os.remove(map_path)
    return out_path
