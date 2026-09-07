"""Temperatura superficial del mar (TSM)."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

from .common import _base_map, _add_nino_boxes, _autocrop_whitespace


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
