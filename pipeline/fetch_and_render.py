#!/usr/bin/env python3
"""
Pipeline diario ENSO: descarga condicional de NOAA (OISST + NCEP/NCAR
Reanalysis), recorte al Pacífico tropical, render de figuras y actualización
del índice de tendencia. Pensado para correr vía cron (run_enso_update.sh).

Fuentes (mismas que el notebook original del usuario, solo automatizadas):
  - OISST v2 high-res (SST + anomalía diaria)  -> downloads.psl.noaa.gov
  - NCEP GDAS (viento 850hPa, SLP diaria)      -> downloads.psl.noaa.gov

Nota importante: OISST y GDAS se actualizan a diario, pero cada uno con su
propio rezago de publicación. Por eso cada variable usa su propia "última
fecha disponible" en vez de asumir que todas llegan hasta hoy — evita el
riesgo de .sel(method="nearest") etiquetando silenciosamente un dato viejo
con la fecha de hoy.
"""

import glob
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import xarray as xr

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "app"))
import indices  # noqa: E402
import plotting  # noqa: E402

RAW = os.path.join(BASE_DIR, "data", "raw")
PROCESSED = os.path.join(BASE_DIR, "data", "processed")
FIGURES = os.path.join(BASE_DIR, "data", "figures")
for _d in (RAW, PROCESSED, FIGURES):
    os.makedirs(_d, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("enso_pipeline")

YEAR = datetime.now(timezone.utc).year
NOAA_BASE = "https://downloads.psl.noaa.gov/Datasets"
SOURCES = {
    "sst_mean": f"{NOAA_BASE}/noaa.oisst.v2.highres/sst.day.mean.{YEAR}.nc",
    "sst_anom": f"{NOAA_BASE}/noaa.oisst.v2.highres/sst.day.anom.{YEAR}.nc",
    # NCEP GDAS (análisis operacional, ~1 día de rezago) — no el "ncep.reanalysis"
    # (Reanalysis 1) QC'd, que se atascó en 2026-03-19 (confirmado contra el
    # servidor: mismo Last-Modified que nuestro último archivo descargado).
    # Mismo esquema (variables/dims/grid 2.5°), así que es reemplazo directo.
    "uwnd": f"{NOAA_BASE}/ncep/uwnd.{YEAR}.nc",
    "vwnd": f"{NOAA_BASE}/ncep/vwnd.{YEAR}.nc",
    "slp": f"{NOAA_BASE}/ncep/slp.{YEAR}.nc",
    "pottmp": f"{NOAA_BASE}/godas/pottmp.{YEAR}.nc",
}

# Debe coincidir con pipeline/build_subsurface_climatology.py
SUBSURF_LAT_BAND = (-2, 2)
SUBSURF_LAT_MARGIN = (-6, 6)
SUBSURF_MAX_DEPTH_M = 600

LON_RANGE = (115, 330)   # Pacífico tropical, convención 0-360
LAT_RANGE = (-25, 25)

# plot_slp() dibuja hasta 60°S/10°N (plotting.py: extent = [220, 330, -60, 10])
# — necesita su propio recorte, más ancho que el resto de variables, si no
# el mapa queda con ejes hasta 60°S pero sin datos (en blanco) debajo de -25°.
SLP_LAT_RANGE = (-65, 25)


def download_conditional(url, dest):
    log.info("Verificando %s", os.path.basename(dest))
    cmd = ["curl", "-sS", "-fL", "--retry", "3", "--retry-delay", "5",
           "-z", dest, "-o", dest, url]
    subprocess.run(cmd, check=True)


def open_with_time_repair(path):
    """Los archivos de NCEP/NCAR Reanalysis a veces traen un fill-value
    corrupto (~9.97e36) en algún paso de tiempo, que rompe la decodificación
    normal de xarray (visto en el notebook original del usuario). Se intenta
    la apertura normal primero; solo si falla, se repara interpolando el
    índice corrupto y decodificando con las unidades reales del archivo
    (p.ej. "hours since 1800-01-01"), en vez de asumir una unidad fija."""
    try:
        return xr.open_dataset(path)
    except Exception as e:
        log.warning("Decodificación normal de tiempo falló en %s (%s); reparando...", path, e)

    raw = xr.open_dataset(path, decode_times=False)
    time_var = raw["time"]
    units = time_var.attrs.get("units", "hours since 1800-01-01 00:00:0.0")
    fill = float(time_var.attrs.get("_FillValue", 9.969209968386869e36))
    t = time_var.values.astype("float64")
    valid = np.abs(t) < abs(fill) / 1000
    if not valid.all():
        idx = np.arange(len(t))
        t = np.interp(idx, idx[valid], t[valid])
    from xarray.coding.times import decode_cf_datetime
    decoded = decode_cf_datetime(t, units)
    return raw.assign_coords(time=decoded)


def subset_var(da, lon_range=LON_RANGE, lat_range=LAT_RANGE):
    """Recorta lon/lat sin asumir el orden (ascendente o descendente) del eje lat,
    que difiere entre OISST (sur->norte) y NCEP Reanalysis (norte->sur)."""
    lat_vals = da["lat"].values
    lat_sl = slice(*lat_range) if lat_vals[0] < lat_vals[-1] else slice(*reversed(lat_range))
    return da.sel(lon=slice(*lon_range), lat=lat_sl)


def load_and_subset():
    log.info("Cargando y recortando datasets al Pacífico tropical...")
    sst_mean = subset_var(xr.open_dataset(os.path.join(RAW, "sst_mean.nc"))["sst"])
    sst_anom = subset_var(xr.open_dataset(os.path.join(RAW, "sst_anom.nc"))["anom"])

    u_raw = open_with_time_repair(os.path.join(RAW, "uwnd.nc"))
    u850 = subset_var(u_raw["uwnd"].sel(level=850, method="nearest"))

    v_raw = open_with_time_repair(os.path.join(RAW, "vwnd.nc"))
    v850 = subset_var(v_raw["vwnd"].sel(level=850, method="nearest"))

    slp = subset_var(open_with_time_repair(os.path.join(RAW, "slp.nc"))["slp"], lat_range=SLP_LAT_RANGE)
    return sst_mean, sst_anom, u850, v850, slp


def equatorial_band_mean(path):
    """Reproduce el mismo recorte/promedio usado al construir la climatología
    (build_subsurface_climatology.py) para que ambos sean comparables."""
    ds = xr.open_dataset(path)
    da = ds["pottmp"] - 273.15  # K -> °C
    da = da.sel(level=slice(0, SUBSURF_MAX_DEPTH_M))
    lat_vals = da["lat"].values
    lat_sl = (slice(*SUBSURF_LAT_MARGIN) if lat_vals[0] < lat_vals[-1]
              else slice(*reversed(SUBSURF_LAT_MARGIN)))
    da = da.sel(lat=lat_sl)
    weights = np.cos(np.deg2rad(da["lat"]))
    band_sl = (slice(*SUBSURF_LAT_BAND) if lat_vals[0] < lat_vals[-1]
               else slice(*reversed(SUBSURF_LAT_BAND)))
    return da.sel(lat=band_sl).weighted(weights.sel(lat=band_sl)).mean(dim="lat")


def render_subsurface_section(pottmp_path):
    """Corte profundidad-longitud de anomalía subsuperficial (Onda Kelvin).
    Requiere que ya exista data/processed/godas_climatology.nc — generado una
    sola vez con pipeline/build_subsurface_climatology.py. Si no existe, se
    omite este paso sin romper el resto del pipeline."""
    clim_path = os.path.join(PROCESSED, "godas_climatology.nc")
    if not os.path.exists(clim_path):
        log.warning("No existe %s — corre build_subsurface_climatology.py una vez "
                    "para habilitar el corte de Onda Kelvin. Se omite este paso.", clim_path)
        return

    pacific_lon = slice(120, 290)  # Indonesia -> Sudamérica; recorta tierra/otros océanos
    climatology = xr.open_dataset(clim_path)["pottmp_clim"].sel(lon=pacific_lon)
    band_mean = equatorial_band_mean(pottmp_path).sel(lon=pacific_lon)  # dims: (time, level, lon)

    months_available = pd.to_datetime(band_mean["time"].values)
    latest_idx = int(np.argmax(band_mean["time"].values))
    latest_month_ts = months_available[latest_idx]
    latest_label = latest_month_ts.strftime("%Y-%m")

    plotting.plot_equatorial_depth_section(
        band_mean.isel(time=latest_idx), climatology, latest_month_ts.month,
        os.path.join(FIGURES, f"subsurf_{latest_label}-01.png"),
        title_suffix=f" · {latest_month_ts.strftime('%b %Y')}")
    log.info("Corte subsuperficial (Onda Kelvin) generado para %s", latest_label)

    # GIF con todos los meses disponibles del año en curso (evolución de la onda)
    try:
        import imageio.v2 as imageio
        frame_paths = []
        tmp_dir = os.path.join(FIGURES, "_subsurf_frames")
        os.makedirs(tmp_dir, exist_ok=True)
        for i in range(len(months_available)):
            ts = months_available[i]
            fp = os.path.join(tmp_dir, f"frame_{i:02d}.png")
            plotting.plot_equatorial_depth_section(
                band_mean.isel(time=i), climatology, ts.month, fp,
                title_suffix=f" · {ts.strftime('%b %Y')}")
            frame_paths.append(fp)
        frames = [imageio.imread(fp) for fp in frame_paths]
        imageio.mimsave(os.path.join(FIGURES, "subsurf_anim.gif"), frames, duration=800, loop=0)
        for fp in frame_paths:
            os.remove(fp)
        os.rmdir(tmp_dir)
        log.info("GIF de evolución subsuperficial actualizado (%d meses)", len(frame_paths))
    except ImportError:
        log.warning("imageio no instalado — se omite el GIF de evolución subsuperficial.")


def latest_time_str(da):
    return pd.Timestamp(da["time"].max().values).strftime("%Y-%m-%d")


def build_recent_animation(prefix, max_frames=15, duration_ms=500):
    """Arma un GIF con los últimos `max_frames` días ya generados para esa
    variable — reutiliza las figuras diarias que el pipeline ya guarda en
    FIGURES (no vuelve a graficar nada), mismo patrón que la animación
    mensual de Subsuperficie. Rellena a un tamaño común por si el autocrop
    de plotting.py deja frames con 1-2 px de diferencia día a día."""
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d{{4}}-\d{{2}}-\d{{2}})\.png$")
    dated = []
    for f in glob.glob(os.path.join(FIGURES, f"{prefix}_*.png")):
        m = pattern.match(os.path.basename(f))
        if m:
            dated.append((m.group(1), f))
    dated.sort(key=lambda x: x[0])
    frame_paths = [f for _, f in dated[-max_frames:]]
    if len(frame_paths) < 2:
        return

    try:
        import imageio.v2 as imageio
    except ImportError:
        log.warning("imageio no instalado — se omite la animación de %s.", prefix)
        return

    frames = [imageio.imread(fp) for fp in frame_paths]
    max_h = max(f.shape[0] for f in frames)
    max_w = max(f.shape[1] for f in frames)
    padded = []
    for f in frames:
        h, w = f.shape[:2]
        if (h, w) == (max_h, max_w):
            padded.append(f)
            continue
        canvas = np.full((max_h, max_w, f.shape[2]), 255, dtype=f.dtype)
        canvas[:h, :w] = f
        padded.append(canvas)

    imageio.mimsave(os.path.join(FIGURES, f"{prefix}_anim.gif"), padded,
                     duration=duration_ms, loop=0)
    log.info("Animación de %s actualizada (%d días).", prefix, len(frame_paths))


def prune_old_figures(days=60):
    """Poda por antigüedad de GENERACIÓN (mtime), no por la fecha del dato en
    el nombre de archivo — viento/SLP arrastran ~meses de rezago (NCEP/NCAR
    Reanalysis 1), así que una figura recién generada para un dato de marzo
    no debe borrarse solo porque esa fecha ya pasó hace más de `days` días."""
    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()
    removed = 0
    for f in glob.glob(os.path.join(FIGURES, "*.png")):
        if os.path.getmtime(f) < cutoff_ts:
            os.remove(f)
            removed += 1
    if removed:
        log.info("Figuras podadas (> %s días desde su generación): %d", days, removed)


LOCK_PATH = os.path.join(BASE_DIR, "data", ".pipeline.lock")


def main():
    """Toma un lock en data/ (compartido con el host vía el volumen Docker)
    para que una corrida disparada a mano desde el dashboard (botón
    "Actualizar datos") nunca pise una corrida del cron, sin importar cuál
    de los dos arrancó primero."""
    if os.path.exists(LOCK_PATH):
        try:
            with open(LOCK_PATH) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            log.warning("Ya hay una actualización en curso (PID %d) — saliendo.", pid)
            return
        except (OSError, ValueError):
            log.info("Lock huérfano o inválido en %s — se ignora y continúa.", LOCK_PATH)

    with open(LOCK_PATH, "w") as f:
        f.write(str(os.getpid()))
    try:
        _run()
    finally:
        try:
            os.remove(LOCK_PATH)
        except FileNotFoundError:
            pass


def _run():
    log.info("=== Iniciando actualización ENSO %s ===", datetime.now(timezone.utc).isoformat())

    for name, url in SOURCES.items():
        dest = os.path.join(RAW, f"{name}.nc")
        try:
            download_conditional(url, dest)
        except subprocess.CalledProcessError as e:
            log.error("Fallo al descargar %s: %s", name, e)
            if not os.path.exists(dest):
                raise

    sst_mean, sst_anom, u850, v850, slp = load_and_subset()

    date_sst = latest_time_str(sst_mean)
    date_wind = latest_time_str(u850)
    date_slp = latest_time_str(slp)
    log.info("Última fecha disponible — SST: %s | Viento: %s | SLP: %s", date_sst, date_wind, date_slp)

    lag_wind_days = (pd.Timestamp(date_sst) - pd.Timestamp(date_wind)).days
    if lag_wind_days > 10:
        log.warning("GDAS (viento/SLP) va %d días detrás de OISST — revisar si la fuente "
                    "dejó de publicar (no debería pasar de un par de días).", lag_wind_days)

    plotting.plot_sst(sst_mean, date_sst, os.path.join(FIGURES, f"tsm_{date_sst}.png"))
    build_recent_animation("tsm")
    plotting.plot_sst_anom(sst_anom, date_sst, os.path.join(FIGURES, f"anom_{date_sst}.png"))
    build_recent_animation("anom")
    plotting.plot_wind_850hpa_vectors(u850, v850, date_wind, os.path.join(FIGURES, f"viento_{date_wind}.png"))
    build_recent_animation("viento")
    plotting.plot_slp(slp, date_slp, os.path.join(FIGURES, f"slp_{date_slp}.png"))
    build_recent_animation("slp")

    plotting.plot_hovmoller_nino(
        sst_anom, "Anomalía TSM", "Niño 3.4", os.path.join(FIGURES, f"hovmoller_nino34_{date_sst}.png"),
        lon_min_360=190, lon_max_360=240, int_lon=10, lat_band_south=-5, lat_band_north=5,
        min_val=-3, max_val=3, levels=21, cmap_nombre="seismic")

    plotting.plot_hovmoller_nino(
        sst_anom, "Anomalía TSM", "Niño 1+2", os.path.join(FIGURES, f"hovmoller_nino12_{date_sst}.png"),
        lon_min_360=270, lon_max_360=280, int_lon=2.5, lat_band_south=-10, lat_band_north=0,
        min_val=-3, max_val=3, levels=21, cmap_nombre="seismic")

    indices.update_indices_csv(sst_anom, os.path.join(PROCESSED, "indices_diarios.csv"))

    try:
        render_subsurface_section(os.path.join(RAW, "pottmp.nc"))
    except Exception:
        log.exception("Fallo generando el corte subsuperficial (Onda Kelvin) — se continúa sin él.")

    # Guarda qué fecha corresponde a cada variable para que la app Dash no adivine
    with open(os.path.join(PROCESSED, "latest.json"), "w") as f:
        import json
        json.dump({"sst": date_sst, "viento": date_wind, "slp": date_slp,
                   "actualizado": datetime.now(timezone.utc).isoformat()}, f)

    prune_old_figures(days=60)
    log.info("=== Actualización completa ===")


if __name__ == "__main__":
    main()
