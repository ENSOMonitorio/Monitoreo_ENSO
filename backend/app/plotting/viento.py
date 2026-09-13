"""Viento zonal y vectores de viento a 850 hPa."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs

from .common import _base_map, _add_nino_boxes, _autocrop_whitespace


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
