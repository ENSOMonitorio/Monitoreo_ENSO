"""
Cálculo y graficado de la Circulación de Walker (Zonal Mass Stream Function).
=============================================================================
Integrado en el módulo de viento del Monitor ENSO.
Soporta cálculo vía armónicos esféricos (windspharm) o resolución espectral
nativa con SciPy como respaldo multiplataforma.
"""

import os
import sys
import warnings
import numpy as np

_app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy.integrate import cumulative_trapezoid
from scipy.fft import rfft, irfft

warnings.filterwarnings("ignore")


# ============================================================
# 1. CARGA Y PREPROCESAMIENTO DE DATOS
# ============================================================

def cargar_datos(ruta_u="uwnd.nc", ruta_v="vwnd.nc"):
    """
    Carga uwnd.nc y vwnd.nc, detecta automáticamente los nombres
    de las variables y normaliza coordenadas.
    """
    ds_u = xr.open_dataset(ruta_u)
    ds_v = xr.open_dataset(ruta_v)

    def _find_var(ds, candidatos):
        for c in candidatos:
            if c in ds.data_vars:
                return c
        for v in ds.data_vars:
            if ds[v].ndim >= 3:
                return v
        raise ValueError(f"No se encontró variable de viento en {list(ds.data_vars)}")

    u_name = _find_var(ds_u, ["uwnd", "u", "U", "u_wind"])
    v_name = _find_var(ds_v, ["vwnd", "v", "V", "v_wind"])

    u = ds_u[u_name]
    v = ds_v[v_name]

    # Normalizar nombres de coordenadas
    rename_map = {}
    for coord in u.coords:
        cl = coord.lower()
        if cl in ("latitude",):
            rename_map[coord] = "lat"
        if cl in ("longitude",):
            rename_map[coord] = "lon"
        if cl in ("isobaric", "plev", "pressure", "lev"):
            rename_map[coord] = "level"
    u = u.rename(rename_map)
    v = v.rename(rename_map)

    # Normalizar unidades de nivel (si vienen en Pa a hPa)
    if float(u["level"].max()) > 2000:
        u = u.assign_coords(level=u["level"] / 100.0)
        v = v.assign_coords(level=v["level"] / 100.0)
    u["level"].attrs["units"] = "hPa"
    v["level"].attrs["units"] = "hPa"

    # Asegurar lat ascendente (-90 a 90) y level ascendente (10 a 1000 hPa)
    u = u.sortby(["lat", "level"])
    v = v.sortby(["lat", "level"])

    return u, v


# ============================================================
# 2. VIENTO DIVERGENTE (HELMHOLTZ DECOMPOSITION)
# ============================================================

def _calcular_u_divergente_scipy(u_da, v_da):
    """
    Calcula el componente divergente del viento zonal resolviendo
    Del^2 chi = div(V) en la esfera usando descomposición de Fourier (lon)
    y diferencias finitas tridiagonales (lat).
    """
    a = 6.371e6  # Radio de la Tierra en metros
    lat = u_da["lat"].values
    lon = u_da["lon"].values
    u_val = u_da.values
    v_val = v_da.values

    lat_rad = np.deg2rad(lat)
    if lat_rad[0] > lat_rad[-1]:
        lat_rad = lat_rad[::-1]
        u_val = np.flip(u_val, axis=-2)
        v_val = np.flip(v_val, axis=-2)
        flipped = True
    else:
        flipped = False

    nlat = len(lat_rad)
    nlon = len(lon)
    cos_lat = np.clip(np.cos(lat_rad), 1e-6, 1.0)
    dlon = np.deg2rad(lon[1] - lon[0]) if len(lon) > 1 else (2 * np.pi / nlon)

    # Derivada zonal du/dlon por FFT
    u_hat = rfft(u_val, axis=-1)
    k = np.fft.rfftfreq(nlon, d=1.0) * (2 * np.pi / (nlon * dlon))
    du_dlon = irfft(1j * k * u_hat, n=nlon, axis=-1)

    # Derivada meridional d(v*cos(lat))/dlat
    v_cos = v_val * cos_lat[:, None]
    dv_cos_dlat = np.gradient(v_cos, lat_rad, axis=-2)
    div = (du_dlon + dv_cos_dlat) / (a * cos_lat[:, None])

    # Resolver Del^2 chi = div en espacio de Fourier
    div_hat = rfft(div, axis=-1)
    nk = div_hat.shape[-1]

    orig_shape = div_hat.shape
    nbatch = int(np.prod(orig_shape[:-2]))
    div_flat = div_hat.reshape(nbatch, nlat, nk)
    u_div_flat = np.zeros_like(div_flat)

    # Matriz del operador laplaciano en latitud para cada número de onda
    for ik in range(1, nk):
        wn = ik
        A = np.zeros((nlat, nlat), dtype=float)
        for i in range(1, nlat - 1):
            phi_p = 0.5 * (lat_rad[i] + lat_rad[i+1])
            phi_m = 0.5 * (lat_rad[i] + lat_rad[i-1])
            cos_p = np.cos(phi_p)
            cos_m = np.cos(phi_m)
            dphi_p = lat_rad[i+1] - lat_rad[i]
            dphi_m = lat_rad[i] - lat_rad[i-1]
            dphi_c = 0.5 * (lat_rad[i+1] - lat_rad[i-1])

            c_p = cos_p / (dphi_p * cos_lat[i] * dphi_c * a**2)
            c_m = cos_m / (dphi_m * cos_lat[i] * dphi_c * a**2)
            c_c = -(c_p + c_m) - (wn**2) / ((a * cos_lat[i])**2)

            A[i, i-1] = c_m
            A[i, i] = c_c
            A[i, i+1] = c_p
        A[0, 0] = 1.0
        A[-1, -1] = 1.0

        rhs = div_flat[:, :, ik].copy()
        rhs[:, 0] = 0.0
        rhs[:, -1] = 0.0
        chi = np.linalg.solve(A, rhs.T).T
        u_div_flat[:, :, ik] = (1j * wn / (a * cos_lat[None, :])) * chi

    u_div_hat = u_div_flat.reshape(orig_shape)
    u_div = irfft(u_div_hat, n=nlon, axis=-1)
    if flipped:
        u_div = np.flip(u_div, axis=-2)

    u_chi = xr.DataArray(u_div, coords=u_da.coords, dims=u_da.dims, name="u_div")
    u_chi.attrs["units"] = "m s**-1"
    u_chi.attrs["long_name"] = "Divergent zonal wind"
    return u_chi


def calcular_u_divergente(u, v):
    """
    Calcula el componente divergente (irrotacional) del viento zonal.
    Usa windspharm si está disponible, o solver nativo SciPy/FFT.
    """
    try:
        from windspharm.xarray import VectorWind
        # windspharm requiere latitud global y niveles
        u_sel = u.sel(level=slice(100, 1000))
        v_sel = v.sel(level=slice(100, 1000))
        vw = VectorWind(u_sel, v_sel)
        u_chi, _ = vw.irrotationalcomponent()
        u_chi.name = "u_div"
        u_chi.attrs["units"] = "m s**-1"
        u_chi.attrs["long_name"] = "Divergent zonal wind"
        return u_chi
    except Exception:
        # Fallback a solver nativo SciPy
        u_sel = u.sel(level=slice(100, 1000))
        v_sel = v.sel(level=slice(100, 1000))
        return _calcular_u_divergente_scipy(u_sel, v_sel)


# ============================================================
# 3. FUNCIÓN DE CORRIENTE DE MASA ZONAL Ψ(p)
# ============================================================

WALKER_BANDS = {
    "5S-5N": {"slice": (-5.0, 5.0), "label": "5°S–5°N"},
    "2S-2N": {"slice": (-2.5, 2.5), "label": "2°S–2°N"},
    "0":     {"slice": (0.0, 0.0),   "label": "0°"},
}


def calcular_stream_function(u_div, p_top=100.0, lat_band=(-5, 5)):
    """
    Ψ(p) = (2πa/g) * ∫_{p_top}^{p} u_D dp'
    con promedio meridional en la banda `lat_band` (ej. (-5, 5), (-2.5, 2.5) o (0, 0)).
    """
    a = 6.371e6     # m
    g = 9.81        # m/s²

    # Promedio meridional ecuatorial o selección en latitud específica
    lat_min, lat_max = min(lat_band), max(lat_band)
    if lat_min == lat_max:
        u_eq = u_div.sel(lat=lat_min, method="nearest")
    else:
        u_eq = u_div.sel(lat=slice(lat_min, lat_max)).mean(dim="lat")

    # Ordenar niveles de tope (100 hPa) a superficie (1000 hPa)
    u_eq = u_eq.sortby("level")
    u_eq = u_eq.sel(level=slice(p_top, 1000.0))
    p_pa = (u_eq["level"] * 100.0).astype(float)

    # Prefactor
    factor = 2 * np.pi * a / g

    lev_axis = u_eq.dims.index("level")
    psi_values = cumulative_trapezoid(u_eq.values, x=p_pa.values, axis=lev_axis, initial=0.0)

    psi = xr.DataArray(
        psi_values * factor / 1e10,
        coords=u_eq.coords,
        dims=u_eq.dims,
        name="psi",
    )
    psi.attrs["units"] = "10^10 kg s^-1"
    psi.attrs["long_name"] = "Zonal Mass Stream Function (Walker)"
    return psi


# ============================================================
# 4. ÍNDICE DE INTENSIDAD DE WALKER
# ============================================================

def indice_intensidad_walker(psi, lon_min=120, lon_max=180,
                             p_min=300, p_max=700):
    """
    Promedia Ψ en la rama ascendente del Pacífico occidental.
    Valores más negativos => Walker más intensa (La Niña).
    Valores cercanos a 0 o positivos => Walker debilitada (El Niño).
    """
    region = psi.sel(lon=slice(lon_min, lon_max),
                     level=slice(p_min, p_max))
    return region.mean(dim=["lon", "level"])


# ============================================================
# 5. VISUALIZACIÓN
# ============================================================

def plot_walker_cross_section(psi, u_eq=None, time_sel=None, out_path=None,
                              titulo=None, figsize=(12.5, 4.4), con_vectores=False):
    """
    Corte vertical Presión vs Longitud de la Circulación de Walker.
    Dominio centrado en la cuenca Indo-Pacífica (120°E a 40°W / 320°E).
    Si con_vectores es True y se proporciona u_eq, superpone los vectores (u_D, -omega).
    """
    try:
        from plotting.common import NINO_REGIONS_EQ, _lon_label, _autocrop_whitespace
    except ImportError:
        from backend.app.plotting.common import NINO_REGIONS_EQ, _lon_label, _autocrop_whitespace

    if time_sel is not None:
        if isinstance(time_sel, str):
            psi_plot = psi.sel(time=pd.to_datetime(time_sel), method="nearest")
            date_label = str(pd.to_datetime(time_sel).date())
        else:
            psi_plot = psi.sel(time=time_sel)
            date_label = str(psi_plot["time"].values)[:10]
    else:
        psi_plot = psi.isel(time=-1)
        date_label = str(psi_plot["time"].values)[:10]

    # Convertir longitudes a convención 0-360 si vinieran en -180..180
    if float(psi_plot["lon"].min()) < 0:
        psi_plot = psi_plot.assign_coords(
            lon=(psi_plot["lon"] % 360)
        ).sortby("lon")

    if titulo is None:
        titulo = f"Circulación de Walker — {date_label}"

    fig, ax = plt.subplots(figsize=figsize)

    # Recortar longitud al dominio del Pacífico tropical (120°E a 40°W / 320°E)
    psi_domain = psi_plot.sel(lon=slice(120, 320))
    vmax = float(np.nanmax(np.abs(psi_domain.values)))
    if vmax == 0 or np.isnan(vmax):
        vmax = 1.0
    levels = np.linspace(-vmax, vmax, 21)

    cf = ax.contourf(psi_domain["lon"], psi_domain["level"], psi_domain.values,
                     levels=levels, cmap="RdBu_r", extend="both")

    cl = ax.contour(psi_domain["lon"], psi_domain["level"], psi_domain.values,
                    levels=levels[::2], colors="black", linewidths=0.5, alpha=0.45)
    ax.clabel(cl, inline=True, fontsize=7.5, fmt="%1.1f")

    # Superponer vectores si está activado
    if con_vectores and u_eq is not None:
        if time_sel is not None:
            u_time = u_eq.sel(time=pd.to_datetime(time_sel), method="nearest") if isinstance(time_sel, str) else u_eq.sel(time=time_sel)
        else:
            u_time = u_eq.isel(time=-1)

        if float(u_time["lon"].min()) < 0:
            u_time = u_time.assign_coords(lon=(u_time["lon"] % 360)).sortby("lon")
        u_domain = u_time.sel(lon=slice(120, 320)).sortby("level").sel(level=slice(100.0, 1000.0))

        # Derivar omega divergente de la función de corriente por continuidad
        a = 6.371e6
        g = 9.81
        lon_rad = np.deg2rad(psi_domain["lon"].values)
        dpsi_dlon = np.gradient(psi_domain.values * 1e10, lon_rad, axis=psi_domain.dims.index("lon"))
        omega_div = - (g / (2 * np.pi * a**2)) * dpsi_dlon

        v_quiver = omega_div * 75.0

        step_lon = 4
        sel_levels = [1000, 850, 700, 500, 300, 200, 100]
        mask_lev = np.isin(psi_domain["level"].values, sel_levels)

        q_lon = psi_domain["lon"].values[::step_lon]
        q_lev = psi_domain["level"].values[mask_lev]
        q_u = u_domain.values[mask_lev, :][:, ::step_lon]
        q_v = v_quiver[mask_lev, :][:, ::step_lon]

        q = ax.quiver(
            q_lon, q_lev, q_u, q_v,
            color="#1a252f",
            scale=65,
            width=0.0020,
            headwidth=3.6,
            headlength=4.2,
            headaxislength=3.8,
            alpha=0.9
        )
        ax.quiverkey(
            q, X=0.88, Y=1.04, U=5,
            label=r"5 m s$^{-1}$ ($u_D$)",
            labelpos="E", coordinates="axes",
            fontproperties={"size": 8.5, "weight": "bold"}
        )

    # Eje Y como presión (invertido y logarítmico)
    ax.set_yscale("log")
    ax.invert_yaxis()
    ax.set_yticks([1000, 850, 700, 500, 300, 200, 100])
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter())
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())

    # Indicadores de regiones Niño
    for nombre, (lon0, lon1, _, _, color) in NINO_REGIONS_EQ.items():
        lon_c = (lon0 + lon1) / 2.0
        ax.axvspan(lon0, lon1, color=color, alpha=0.08)
        ax.axvline(lon0, color=color, ls=":", lw=0.8, alpha=0.7)
        ax.axvline(lon1, color=color, ls=":", lw=0.8, alpha=0.7)
        ax.text(lon_c, 115, nombre, color=color,
                fontsize=8, fontweight="bold", ha="center", va="top")

    ax.set_xlabel("Longitud", fontsize=10, fontweight="bold")
    ax.set_ylabel("Presión (hPa)", fontsize=10, fontweight="bold")
    ax.set_title(titulo, fontsize=12, fontweight="bold")
    ax.set_xlim(120, 320)
    xticks = np.arange(120, 321, 20)
    ax.set_xticks(xticks)
    ax.set_xticklabels([_lon_label(x) for x in xticks])
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.4, color="gray")

    cbar = plt.colorbar(cf, ax=ax, orientation="vertical", pad=0.02)
    cbar.set_label(r"$\Psi$ ($10^{10}$ kg s$^{-1}$)", fontsize=9.5, fontweight="bold")

    plt.tight_layout()

    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        _autocrop_whitespace(out_path)
        return out_path

    return fig, ax


def plot_walker_timeseries(wci, out_path=None, titulo=None, figsize=(11, 3.2)):
    """
    Gráfico de la serie temporal del Índice de Intensidad de Walker.
    """
    try:
        from plotting.common import _autocrop_whitespace
    except ImportError:
        from backend.app.plotting.common import _autocrop_whitespace
    fig, ax = plt.subplots(figsize=figsize)
    times = pd.to_datetime(wci["time"].values)
    values = wci.values

    if titulo is None:
        titulo = "Índice de Intensidad de la Circulación de Walker (120°E–180°, 300–700 hPa)"

    ax.plot(times, values, color="#1565c0", lw=1.5, label="Índice Walker")
    ax.axhline(0, color="black", lw=0.8, linestyle="--", alpha=0.7)
    ax.fill_between(times, values, 0, where=(values < 0), color="#1565c0", alpha=0.15, label="Rama ascendente intensa")
    ax.fill_between(times, values, 0, where=(values > 0), color="#c62828", alpha=0.15, label="Rama ascendente débil")

    ax.set_title(titulo, fontsize=11, fontweight="bold")
    ax.set_ylabel(r"$\Psi$ ($10^{10}$ kg s$^{-1}$)", fontsize=9, fontweight="bold")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.4, color="gray")
    ax.legend(loc="upper right", fontsize=8, framealpha=0.8)

    plt.tight_layout()

    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        _autocrop_whitespace(out_path)
        return out_path

    return fig, ax


def generar_figuras_walker(ruta_u, ruta_v, ruta_corte, ruta_serie, dates_to_plot=None):
    """
    Calcula la función de corriente de Walker y genera las figuras consumidas
    por el backend y el dashboard para las bandas 5°S–5°N, 2°S–2°N y 0°,
    incluyendo versiones con vectores superpuestos.
    """
    u, v = cargar_datos(ruta_u, ruta_v)
    u_div = calcular_u_divergente(u, v)

    figures_dir = os.path.dirname(os.path.abspath(ruta_corte))

    # Fecha más reciente disponible
    fecha_dt = pd.to_datetime(u_div["time"].values[-1])
    if dates_to_plot is not None:
        fechas = [pd.to_datetime(d).strftime("%Y-%m-%d") for d in dates_to_plot]
    else:
        fechas = [fecha_dt.strftime("%Y-%m-%d")]
    fecha_reciente = fechas[-1]

    psi_default = None

    for band_key, band_info in WALKER_BANDS.items():
        psi_band = calcular_stream_function(u_div, lat_band=band_info["slice"])
        if band_key == "5S-5N":
            psi_default = psi_band

        lat_min, lat_max = min(band_info["slice"]), max(band_info["slice"])
        if lat_min == lat_max:
            u_band = u_div.sel(lat=lat_min, method="nearest")
        else:
            u_band = u_div.sel(lat=slice(lat_min, lat_max)).mean(dim="lat")

        label = band_info["label"]

        # 1. Cortes diarios para cada fecha (estándar y con vectores)
        for f in fechas:
            out_band_f = os.path.join(figures_dir, f"walker_{band_key}_{f}.png")
            plot_walker_cross_section(
                psi_band,
                time_sel=f,
                out_path=out_band_f,
                titulo=f"Circulación de Walker ({label}) — {f}",
                con_vectores=False,
            )
            out_vec_f = os.path.join(figures_dir, f"walker_vec_{band_key}_{f}.png")
            plot_walker_cross_section(
                psi_band,
                u_eq=u_band,
                time_sel=f,
                out_path=out_vec_f,
                titulo=f"Circulación de Walker ({label}) con Vectores — {f}",
                con_vectores=True,
            )

            # Para la banda por defecto 5S-5N, también guardar walker_{f}.png y walker_vec_{f}.png
            if band_key == "5S-5N":
                plot_walker_cross_section(
                    psi_band,
                    time_sel=f,
                    out_path=os.path.join(figures_dir, f"walker_{f}.png"),
                    titulo=f"Circulación de Walker ({label}) — {f}",
                    con_vectores=False,
                )
                plot_walker_cross_section(
                    psi_band,
                    u_eq=u_band,
                    time_sel=f,
                    out_path=os.path.join(figures_dir, f"walker_vec_{f}.png"),
                    titulo=f"Circulación de Walker ({label}) con Vectores — {f}",
                    con_vectores=True,
                )

        # 2. Corte vertical reciente
        out_band_corte = os.path.join(figures_dir, f"walker_{band_key}_cross_section.png")
        plot_walker_cross_section(
            psi_band,
            time_sel=fecha_reciente,
            out_path=out_band_corte,
            titulo=f"Circulación de Walker ({label}) — {fecha_reciente}",
            con_vectores=False,
        )
        out_vec_corte = os.path.join(figures_dir, f"walker_vec_{band_key}_cross_section.png")
        plot_walker_cross_section(
            psi_band,
            u_eq=u_band,
            time_sel=fecha_reciente,
            out_path=out_vec_corte,
            titulo=f"Circulación de Walker ({label}) con Vectores — {fecha_reciente}",
            con_vectores=True,
        )

        if band_key == "5S-5N":
            plot_walker_cross_section(
                psi_band,
                time_sel=fecha_reciente,
                out_path=ruta_corte,
                titulo=f"Circulación de Walker ({label}) — {fecha_reciente}",
                con_vectores=False,
            )
            plot_walker_cross_section(
                psi_band,
                u_eq=u_band,
                time_sel=fecha_reciente,
                out_path=os.path.join(figures_dir, "walker_vec_cross_section.png"),
                titulo=f"Circulación de Walker ({label}) con Vectores — {fecha_reciente}",
                con_vectores=True,
            )

        # 3. Serie temporal del índice
        wci_band = indice_intensidad_walker(psi_band)
        out_band_serie = os.path.join(figures_dir, f"walker_{band_key}_timeseries.png")
        plot_walker_timeseries(
            wci_band,
            out_path=out_band_serie,
            titulo=f"Índice de Intensidad de la Circulación de Walker ({label}, 120°E–180°, 300–700 hPa)"
        )
        if band_key == "5S-5N":
            plot_walker_timeseries(
                wci_band,
                out_path=ruta_serie,
                titulo=f"Índice de Intensidad de la Circulación de Walker ({label}, 120°E–180°, 300–700 hPa)"
            )

    return fecha_reciente, psi_default
