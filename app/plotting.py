"""
Funciones de graficado ENSO, adaptadas del notebook original del usuario
(noaa_parameters_porras.py, curso ENSO). Misma lógica visual (cajas Niño,
paleta Spectral_r / seismic, extensión Pacífico tropical) — solo se quitó
todo lo específico de Colab (drive.mount, %cd, !pip, !mkdir) y se
parametrizó la ruta de salida para correr en el VPS.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # sin display — servidor headless
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import cartopy.crs as ccrs
import cartopy.feature as cfeature

EXTENT_PACIFICO = [115, 360 - 30, -21, 21]


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

NINO_BOXES = {
    "Niño 3.4": dict(xy=(-170, -5), width=50, height=10, color="black", lw=2.5, label_xy=(-150, 7)),
    "Niño 1+2": dict(xy=(-90, -10), width=10, height=10, color="black", lw=2.5, label_xy=(-90, 2)),
    "Niño 3": dict(xy=(-150, -5), width=60, height=10, color="red", lw=1.5, ls="--", label_xy=(-120, 7)),
    "Niño 4": dict(xy=(160, -5), width=50, height=10, color="blue", lw=1.5, ls="--", label_xy=(180, 7)),
}


def _add_nino_boxes(ax):
    for name, b in NINO_BOXES.items():
        ax.add_patch(mpatches.Rectangle(
            xy=b["xy"], width=b["width"], height=b["height"],
            facecolor="none", edgecolor=b["color"], linewidth=b["lw"],
            linestyle=b.get("ls", "-"), transform=ccrs.PlateCarree()))
        ax.text(*b["label_xy"], name, color=b["color"], fontsize=9,
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


def plot_sst(sst_daily_data, date_str, out_path, min_val=14, max_val=32, levels=19):
    target_date = pd.to_datetime(date_str)
    sst_to_plot = sst_daily_data.sel(time=target_date, method="nearest").squeeze()

    fig, ax = _base_map()
    cmap = plt.get_cmap("Spectral_r")
    contour_levels = np.linspace(min_val, max_val, levels)
    plot_obj = sst_to_plot.plot.contourf(ax=ax, transform=ccrs.PlateCarree(), cmap=cmap,
                                          levels=contour_levels, add_colorbar=False, extend="both")
    fig.suptitle(f'TSM Diaria {target_date.strftime("%Y-%m-%d")}', fontsize=14, fontweight="bold")
    _add_nino_boxes(ax)
    cbar_ax = fig.add_axes([0.92, 0.35, 0.02, 0.3])
    cbar = fig.colorbar(plot_obj, cax=cbar_ax, orientation="vertical")
    cbar.set_label("TSM (°C)", fontsize=12, fontweight="bold")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    _autocrop_whitespace(out_path)
    return out_path


def plot_sst_anom(sst_anom_data, date_str, out_path, min_val=-5, max_val=5, levels=21):
    target_date = pd.to_datetime(date_str)
    sst_to_plot = sst_anom_data.sel(time=target_date, method="nearest").squeeze()

    fig, ax = _base_map()
    cmap = plt.get_cmap("seismic")
    contour_levels = np.linspace(min_val, max_val, levels)
    plot_obj = sst_to_plot.plot.contourf(ax=ax, transform=ccrs.PlateCarree(), cmap=cmap,
                                          levels=contour_levels, add_colorbar=False, extend="both")
    fig.suptitle(f'Anomalía TSM Diaria {target_date.strftime("%Y-%m-%d")}', fontsize=14, fontweight="bold")
    _add_nino_boxes(ax)
    cbar_ax = fig.add_axes([0.92, 0.35, 0.02, 0.3])
    cbar = fig.colorbar(plot_obj, cax=cbar_ax, orientation="vertical")
    cbar.set_label("Anom TSM (°C)", fontsize=12, fontweight="bold")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    _autocrop_whitespace(out_path)
    return out_path


def plot_wind_850hpa_vectors(u850_data, v850_data, date_str, out_path,
                              min_val=-15, max_val=15, levels=31, cmap_name="PRGn",
                              quiver_scale=1.8, quiver_step=1,
                              quiver_width=0.0015, quiver_head_width=4, quiver_head_length=5):
    target_date = pd.to_datetime(date_str)
    u850_to_plot = u850_data.sel(time=target_date, method="nearest").squeeze()
    v850_to_plot = v850_data.sel(time=target_date, method="nearest").squeeze()

    fig, ax = _base_map()
    cmap = plt.get_cmap(cmap_name)
    contour_levels = np.linspace(min_val, max_val, levels)
    plot_obj = u850_to_plot.plot.contourf(ax=ax, transform=ccrs.PlateCarree(), cmap=cmap,
                                           levels=contour_levels, add_colorbar=False, extend="both")
    ax.quiver(u850_to_plot.lon[::quiver_step], u850_to_plot.lat[::quiver_step],
              u850_to_plot.values[::quiver_step, ::quiver_step],
              v850_to_plot.values[::quiver_step, ::quiver_step],
              color="black", scale_units="xy", scale=quiver_scale,
              transform=ccrs.PlateCarree(), width=quiver_width,
              headwidth=quiver_head_width, headlength=quiver_head_length, headaxislength=3)
    fig.suptitle(f'Viento Zonal y Vectores de Viento a 850 hPa — {target_date.strftime("%Y-%m-%d")}',
                 fontsize=14, fontweight="bold")
    _add_nino_boxes(ax)
    cbar_ax = fig.add_axes([0.92, 0.35, 0.02, 0.3])
    cbar = fig.colorbar(plot_obj, cax=cbar_ax, orientation="vertical")
    cbar.set_label("U850 (m/s)", fontsize=12, fontweight="bold")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    _autocrop_whitespace(out_path)
    return out_path


def plot_slp(slp_daily_data, date_str, out_path, min_val=981, max_val=1038, contour=3):
    target_date = pd.to_datetime(date_str)
    slp_to_plot = slp_daily_data.sel(time=target_date, method="nearest").squeeze()
    extent = [360 - 140, 360 - 30, -60, 10]

    fig, ax = plt.subplots(1, 1, figsize=(8, 12), subplot_kw={"projection": ccrs.PlateCarree()})
    cmap = plt.get_cmap("bwr")
    contour_levels = np.arange(min_val, max_val, contour)
    ax.set_extent(extent, crs=ccrs.PlateCarree())
    ax.coastlines(resolution="50m")
    gl = ax.gridlines(draw_labels=True, x_inline=False, y_inline=False,
                       color="gray", linestyle="--", alpha=0.6,
                       xlocs=np.arange(-180, 180, 20), ylocs=np.arange(-90, 91, 5))
    gl.top_labels = gl.right_labels = False
    fig.subplots_adjust(left=0.12, right=0.88, top=0.92, bottom=0.06)

    plot_obj = slp_to_plot.plot.contourf(ax=ax, transform=ccrs.PlateCarree(), cmap=cmap,
                                          levels=contour_levels, add_colorbar=False, extend="both")
    line_contour = slp_to_plot.plot.contour(ax=ax, transform=ccrs.PlateCarree(),
                                             levels=contour_levels, colors="black", linewidths=0.7)
    ax.clabel(line_contour, inline=True, fontsize=8, fmt="%1.0f")
    ax.add_feature(cfeature.BORDERS, linestyle=":", edgecolor="black")
    ax.add_feature(cfeature.LAND, edgecolor="gray", facecolor="lightgray")
    ax.add_feature(cfeature.OCEAN)
    fig.suptitle(f'Presión a nivel de mar (hPa) — {target_date.strftime("%Y-%m-%d")}',
                 fontsize=14, fontweight="bold")
    ax.add_patch(mpatches.Rectangle(xy=(-90, -10), width=10, height=10, facecolor="none",
                                     edgecolor="black", linewidth=2.5, transform=ccrs.PlateCarree()))
    ax.text(-90, 2, "Niño 1+2", color="black", fontsize=9, transform=ccrs.PlateCarree())
    cbar_ax = fig.add_axes([0.90, 0.35, 0.02, 0.3])
    cbar = fig.colorbar(plot_obj, cax=cbar_ax, orientation="vertical")
    cbar.set_label("SLP (hPa)", fontsize=12, fontweight="bold")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    _autocrop_whitespace(out_path)
    return out_path


def _lon_label(x):
    x = x % 360
    return f"{int(round(x))}°E" if x <= 180 else f"{int(round(360 - x))}°W"


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


def plot_hovmoller_nino(sst_daily_data, nombre_variable, zona_nino, out_path,
                         lon_min_360, lon_max_360, int_lon, lat_band_south, lat_band_north,
                         min_val, max_val, levels, cmap_nombre):
    data = sst_daily_data.sel(lon=slice(lon_min_360, lon_max_360))
    hov = data.sel(lat=slice(lat_band_south, lat_band_north)).mean(dim="lat").squeeze()

    fig, ax = plt.subplots(figsize=(10, 11))
    contour_levels = np.linspace(min_val, max_val, levels)
    plot_obj = hov.plot.contourf(ax=ax, x="lon", y="time", levels=contour_levels,
                                  cmap=cmap_nombre, add_colorbar=False, extend="both")
    ax.set_title(f"Diagrama de Hovmöller\n{nombre_variable} (°C)", loc="left", fontsize=11, fontweight="bold")
    ax.set_title(f"Región {zona_nino}\n(Franja {abs(lat_band_south)}°S a {abs(lat_band_north)}°"
                 f"{'S' if lat_band_north < 0 else ''})", loc="right", fontsize=11, fontweight="bold")
    ax.set_xlabel("Longitud (°)", fontsize=9)
    ax.set_ylabel("")
    xlocs = np.arange(lon_min_360, lon_max_360 + int_lon, int_lon)
    ax.set_xticks(xlocs)
    ax.set_xticklabels([f"{int((x - 360) * -1)}°W" for x in xlocs])
    ax.yaxis.set_major_locator(mdates.AutoDateLocator())
    ax.yaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.invert_yaxis()
    ax.grid(True, which="major", linestyle="--", linewidth=0.4, alpha=0.5, color="gray")
    cbar = plt.colorbar(plot_obj, ax=ax, orientation="vertical", pad=0.05)
    cbar.set_label(f"{nombre_variable} (°C)", fontsize=9, fontweight="bold")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path


def plot_hovmoller_nino_lat(sst_daily_data, nombre_variable, zona_nino, out_path,
                             lon_min_360, lon_max_360, int_lon, lat_sel,
                             min_val, max_val, levels, cmap_nombre):
    data = sst_daily_data.sel(lon=slice(lon_min_360, lon_max_360))
    hov = data.sel(lat=lat_sel, method="nearest").squeeze()

    fig, ax = plt.subplots(figsize=(10, 11))
    contour_levels = np.linspace(min_val, max_val, levels)
    plot_obj = hov.plot.contourf(ax=ax, x="lon", y="time", levels=contour_levels,
                                  cmap=cmap_nombre, add_colorbar=False, extend="both")
    ax.set_title(f"Diagrama de Hovmöller\n{nombre_variable} (°C)", loc="left", fontsize=11, fontweight="bold")
    lat_label = f"Latitud: {lat_sel}°" if lat_sel == 0 else f"Latitud: {abs(lat_sel)}°{'N' if lat_sel > 0 else 'S'}"
    ax.set_title(f"Región {zona_nino}\n({lat_label})", loc="right", fontsize=11, fontweight="bold")
    ax.set_xlabel("Longitud (°)", fontsize=9)
    ax.set_ylabel("")
    xlocs = np.arange(lon_min_360, lon_max_360 + int_lon, int_lon)
    ax.set_xticks(xlocs)
    ax.set_xticklabels([f"{int((x - 360) * -1)}°W" for x in xlocs])
    ax.yaxis.set_major_locator(mdates.AutoDateLocator())
    ax.yaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    ax.invert_yaxis()
    ax.grid(True, which="major", linestyle="--", linewidth=0.4, alpha=0.5, color="gray")
    cbar = plt.colorbar(plot_obj, ax=ax, orientation="vertical", pad=0.05)
    cbar.set_label(f"{nombre_variable} (°C)", fontsize=9, fontweight="bold")
    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out_path
