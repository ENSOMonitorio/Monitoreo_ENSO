"""Diagramas de Hovmöller — Niño 3.4 y Niño 1+2."""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


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
