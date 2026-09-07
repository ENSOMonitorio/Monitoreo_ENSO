"""
Índices ENSO propios: promedio de área de la anomalía OISST diaria sobre
las cajas Niño estándar. OJO: esto NO es el ONI oficial (que usa ERSST
mensual, promedio móvil trimestral) — es un índice diario derivado,
útil para ver la tendencia día a día entre publicaciones oficiales.
Coordenadas en convención 0-360 (igual que los archivos NOAA).
"""

import numpy as np
import pandas as pd

NINO_REGIONS_0_360 = {
    "nino12": dict(lat=(-10, 0), lon=(270, 280)),
    "nino3": dict(lat=(-5, 5), lon=(210, 270)),
    "nino34": dict(lat=(-5, 5), lon=(190, 240)),
    "nino4": dict(lat=(-5, 5), lon=(160, 210)),
}


def _area_mean(anom_da, lat_range, lon_range):
    weights = np.cos(np.deg2rad(anom_da.lat))
    sub = anom_da.sel(lat=slice(*sorted(lat_range)), lon=slice(*lon_range))
    return sub.weighted(weights).mean(dim=("lat", "lon"), skipna=True)


def compute_series(anom_da: "xr.DataArray") -> pd.DataFrame:
    """Devuelve un DataFrame fecha x {nino12,nino3,nino34,nino4} para toda la serie temporal."""
    cols = {}
    for name, box in NINO_REGIONS_0_360.items():
        cols[name] = _area_mean(anom_da, box["lat"], box["lon"]).values
    df = pd.DataFrame(cols).round(3)
    df.insert(0, "fecha", pd.to_datetime(anom_da["time"].values).normalize())
    return df


def update_indices_csv(anom_da, csv_path):
    """Recalcula la serie completa disponible en anom_da y la fusiona con el csv existente,
    reemplazando por fecha (idempotente ante re-corridas del mismo día)."""
    new_df = compute_series(anom_da)
    try:
        old_df = pd.read_csv(csv_path, parse_dates=["fecha"])
        merged = pd.concat([old_df, new_df]).drop_duplicates(subset="fecha", keep="last")
    except FileNotFoundError:
        merged = new_df
    merged = merged.sort_values("fecha").reset_index(drop=True)
    merged.to_csv(csv_path, index=False)
    return merged
