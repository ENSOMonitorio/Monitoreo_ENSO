#!/usr/bin/env python3
"""
Construye UNA VEZ la climatología mensual de temperatura subsuperficial
ecuatorial (GODAS `pottmp`) usada para calcular la anomalía del corte
profundidad-longitud ("Onda Kelvin"). No corre en el cron diario — se
ejecuta manualmente cuando se quiere (re)establecer el período base.

Uso:
    python pipeline/build_subsurface_climatology.py [año_inicio] [año_fin]
    (por defecto 2015-2024, ambos incluidos)

Fuente: NCEP GODAS (Global Ocean Data Assimilation System) vía
downloads.psl.noaa.gov — mismo servidor que las demás fuentes de este
pipeline. GODAS es mensual, no diario (a diferencia de OISST).
"""

import os
import subprocess
import sys

import numpy as np
import pandas as pd
import xarray as xr

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIM_CACHE = os.path.join(BASE_DIR, "data", "raw", "godas_clim_cache")
PROCESSED = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(CLIM_CACHE, exist_ok=True)
os.makedirs(PROCESSED, exist_ok=True)

NOAA_BASE = "https://downloads.psl.noaa.gov/Datasets/godas"
LAT_BAND = (-2, 2)      # franja ecuatorial para el promedio (2°S-2°N)
LAT_MARGIN = (-6, 6)    # recorte inicial, con margen, antes de promediar
MAX_DEPTH_M = 600       # profundidad máxima a conservar


def download(year):
    dest = os.path.join(CLIM_CACHE, f"pottmp.{year}.nc")
    if os.path.exists(dest):
        print(f"{year}: ya en caché, no se descarga de nuevo.")
        return dest
    url = f"{NOAA_BASE}/pottmp.{year}.nc"
    print(f"{year}: descargando {url} ...")
    subprocess.run(["curl", "-sS", "-fL", "--retry", "3", "--retry-delay", "5",
                    "-o", dest, url], check=True)
    return dest


def yearly_band_mean(path):
    ds = xr.open_dataset(path)
    da = ds["pottmp"] - 273.15  # K -> °C
    da = da.sel(level=slice(0, MAX_DEPTH_M))
    lat_vals = da["lat"].values
    lat_sl = slice(*LAT_MARGIN) if lat_vals[0] < lat_vals[-1] else slice(*reversed(LAT_MARGIN))
    da = da.sel(lat=lat_sl)
    weights = np.cos(np.deg2rad(da["lat"]))
    band_sl = slice(*LAT_BAND) if lat_vals[0] < lat_vals[-1] else slice(*reversed(LAT_BAND))
    da = da.sel(lat=band_sl).weighted(weights.sel(lat=band_sl)).mean(dim="lat")
    return da  # dims: (time, level, lon), time = 12 meses del año


def main():
    y0 = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    y1 = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
    years = list(range(y0, y1 + 1))
    print(f"Construyendo climatología GODAS {y0}-{y1} ({len(years)} años)...")

    per_year = []
    for y in years:
        path = download(y)
        per_year.append(yearly_band_mean(path))

    combined = xr.concat(per_year, dim="time")
    climatology = combined.groupby("time.month").mean(dim="time")
    climatology.name = "pottmp_clim"
    climatology.attrs["units"] = "degC"
    climatology.attrs["baseline"] = f"{y0}-{y1}"
    climatology.attrs["lat_band"] = str(LAT_BAND)

    out_path = os.path.join(PROCESSED, "godas_climatology.nc")
    climatology.to_netcdf(out_path)
    print(f"Climatología guardada en {out_path} — dims {dict(climatology.sizes)}")


if __name__ == "__main__":
    main()
