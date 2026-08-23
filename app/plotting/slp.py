"""Presión a nivel del mar (SLP)."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from .common import NINO_COLORS, _autocrop_whitespace


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
    ax.add_patch(mpatches.Rectangle(xy=(-90, -10), width=10, height=10,
                                     facecolor=NINO_COLORS["Niño 1+2"], edgecolor="none",
                                     alpha=0.12, transform=ccrs.PlateCarree()))
    ax.add_patch(mpatches.Rectangle(xy=(-90, -10), width=10, height=10, facecolor="none",
                                     edgecolor=NINO_COLORS["Niño 1+2"], linewidth=2.5,
                                     transform=ccrs.PlateCarree()))
    ax.text(-90, 2, "Niño 1+2", color=NINO_COLORS["Niño 1+2"], fontsize=9, fontweight="bold",
            transform=ccrs.PlateCarree())
    cbar_ax = fig.add_axes([0.90, 0.35, 0.02, 0.3])
    cbar = fig.colorbar(plot_obj, cax=cbar_ax, orientation="vertical")
    cbar.set_label("SLP (hPa)", fontsize=12, fontweight="bold")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    _autocrop_whitespace(out_path)
    return out_path
