"""Test de la matemática real de las cajas Niño (promedio de área ponderado
por coseno de latitud). Sirve de guardia de regresión para el tipo de bug
que ya tuvimos una vez: límites de latitud/longitud equivocados por región."""
import numpy as np
import pandas as pd
import pytest
import xarray as xr

import indices


def _constant_field(value, lat=None, lon=None):
    lat = np.arange(-15, 16, 1.0) if lat is None else lat
    lon = np.arange(140, 291, 2.0) if lon is None else lon
    data = np.full((1, lat.size, lon.size), value)
    return xr.DataArray(
        data,
        dims=("time", "lat", "lon"),
        coords={"time": [pd.Timestamp("2026-07-15")], "lat": lat, "lon": lon},
    )


def test_constant_anomaly_field_averages_to_itself():
    da = _constant_field(1.5)
    df = indices.compute_series(da)
    for col in ("nino12", "nino3", "nino34", "nino4"):
        assert df.loc[0, col] == pytest.approx(1.5, abs=1e-9)


def test_regions_only_see_their_own_box():
    # Anomalía de 3.0 rellenando exactamente la caja Niño 1+2 (lat -10..0,
    # lon 270..280) y 0 en el resto. Niño 1+2 debe promediar ~3.0; las
    # cajas vecinas pueden ver un poco de "sangrado" solo en el borde
    # compartido (ej. lon=270 pertenece a la vez a Niño 3 y Niño 1+2 por
    # definición), pero deben quedar muy por debajo del valor real.
    lat = np.arange(-15, 16, 1.0)
    lon = np.arange(140, 291, 1.0)
    da = _constant_field(0.0, lat=lat, lon=lon)
    mask = (da.lat >= -10) & (da.lat <= 0) & (da.lon >= 270) & (da.lon <= 280)
    da = xr.where(mask, 3.0, da)

    df = indices.compute_series(da)
    assert df.loc[0, "nino12"] == pytest.approx(3.0, abs=1e-6)
    for col in ("nino3", "nino34", "nino4"):
        assert df.loc[0, col] < 0.5


def test_update_indices_csv_is_idempotent_for_same_date(tmp_path):
    csv_path = tmp_path / "indices_diarios.csv"
    da = _constant_field(0.4)
    merged = indices.update_indices_csv(da, str(csv_path))
    assert len(merged) == 1

    merged_again = indices.update_indices_csv(da, str(csv_path))
    assert len(merged_again) == 1  # misma fecha reemplaza, no duplica
