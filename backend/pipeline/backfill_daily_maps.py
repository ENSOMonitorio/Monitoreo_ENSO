#!/usr/bin/env python3
"""Backfill de PNGs diarios de TSM/Anomalía para fechas anteriores al primer
día que el pipeline diario alcanzó a graficar (arrancó a correr en julio,
pero el .nc anual de OISST ya trae el año completo desde el 1 de enero) —
se corre a mano, una sola vez, para habilitar el reproductor "desde
principios de año" en el frontend. Reusa el mismo archivo ya descargado en
data/raw/, no baja nada nuevo.

Uso: python -m pipeline.backfill_daily_maps --start 2026-01-01 --end 2026-06-30
(desde backend/, con el mismo entorno que corre fetch_and_render.py)
"""

import argparse
import os
import sys
from datetime import date, timedelta

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BACKEND_DIR, "app"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import xarray as xr  # noqa: E402
import plotting  # noqa: E402
from fetch_and_render import RAW, FIGURES, subset_var  # noqa: E402


def _daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    print(f"Cargando {RAW}/sst_mean.nc y sst_anom.nc ...")
    sst_mean = subset_var(xr.open_dataset(os.path.join(RAW, "sst_mean.nc"))["sst"])
    sst_anom = subset_var(xr.open_dataset(os.path.join(RAW, "sst_anom.nc"))["anom"])

    made = 0
    skipped = 0
    for d in _daterange(start, end):
        ds = d.isoformat()
        tsm_path = os.path.join(FIGURES, f"tsm_{ds}.png")
        anom_path = os.path.join(FIGURES, f"anom_{ds}.png")

        if os.path.exists(tsm_path):
            skipped += 1
        else:
            plotting.plot_sst(sst_mean, ds, tsm_path)
            made += 1

        if os.path.exists(anom_path):
            skipped += 1
        else:
            plotting.plot_sst_anom(sst_anom, ds, anom_path)
            made += 1

        print(f"{ds} listo")

    print(f"Backfill completo: {made} imagenes generadas, {skipped} ya existian "
          f"({start.isoformat()} a {end.isoformat()})")


if __name__ == "__main__":
    main()
