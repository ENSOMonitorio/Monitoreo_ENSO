"""Tema claro de Plotly (spec de rediseño §5 y §7.3): los gráficos van sobre
tarjetas blancas, así que no puede quedar ningún color pensado para el
fondo verde oscuro anterior."""
import importlib

import pandas as pd

import theme

DARK_LEFTOVERS = ("#0d2a1e", "rgba(6,12,8", "#e2f0e8", "#a0bfaa", "rgba(160,191,170", "#0b1f16")


def _client():
    app_module = importlib.import_module("app")
    return app_module, app_module.server.test_client()


def test_chart_layout_is_light():
    lay = theme.chart_layout()
    assert lay["font"]["color"] == "#0E2233"
    assert lay["xaxis"]["gridcolor"] == "#E6EAED"
    assert lay["yaxis"]["gridcolor"] == "#E6EAED"
    assert lay["hoverlabel"]["bgcolor"] == "#0E2233"
    assert not hasattr(theme, "dark_layout")


def test_chart_layout_accepts_overrides():
    lay = theme.chart_layout(height=380)
    assert lay["height"] == 380


def test_index_regions_use_the_map_box_colors():
    from plotting.common import NINO_COLORS

    app_module, _ = _client()
    for meta in app_module.INDEX_REGIONS.values():
        assert meta["color"] == NINO_COLORS[meta["label"]]


def test_index_figure_has_no_dark_leftovers(tmp_path, monkeypatch):
    app_module, client = _client()
    fechas = pd.date_range("2026-01-01", periods=40, freq="D")
    valores = [0.1 * i for i in range(40)]  # cruza +0.5: hay pico y días sobre el umbral
    pd.DataFrame({
        "fecha": fechas, "nino12": valores, "nino3": valores,
        "nino34": valores, "nino4": valores,
    }).to_csv(tmp_path / "indices_diarios.csv", index=False)
    monkeypatch.setattr(app_module, "PROCESSED_DIR", str(tmp_path))

    resp = client.get("/api/indices/nino12")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert '"annotations"' in body  # el caso con pico sí se ejercitó
    for dark in DARK_LEFTOVERS:
        assert dark not in body, dark


def test_historico_figure_has_no_dark_leftovers():
    _, client = _client()
    body = client.get("/api/historico/oni").get_data(as_text=True)
    assert "rgba(255,255,255" not in body
    for dark in DARK_LEFTOVERS:
        assert dark not in body, dark


def _relative_luminance(hex_color):
    h = hex_color.lstrip("#")
    chans = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        chans.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = chans
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_on_white(hex_color):
    return 1.05 / (_relative_luminance(hex_color) + 0.05)


def test_oni_bar_colors_are_visible_on_white():
    """Las barras del ONI van sobre tarjetas blancas: cada nivel necesita
    al menos 3:1 (WCAG 1.4.11) y oscurecer a medida que sube la intensidad."""
    import layout_historico as lh

    for ramp in (lh._NINO_COLORS, lh._NINA_COLORS):
        levels = sorted(ramp)
        for level in levels:
            assert _contrast_on_white(ramp[level]) >= 3.0, (level, ramp[level])
        lums = [_relative_luminance(ramp[lv]) for lv in levels]
        assert lums == sorted(lums, reverse=True)
    assert _contrast_on_white(lh._NEUTRAL) >= 3.0
