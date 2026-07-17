"""
Monitor ENSO — Dash app. Sirve las figuras generadas por
pipeline/fetch_and_render.py y el resumen histórico. Expuesto vía gunicorn
como `app:server` en el puerto 8082 (mismo patrón que los otros dashboards
de este VPS: mapas.resiliencia.cloud y riesgo.resiliencia.cloud).
"""

import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html, no_update
from flask import send_from_directory

import layout_historico
import theme

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
FIGURES_DIR = os.path.join(DATA_DIR, "figures")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

PIPELINE_SCRIPT = os.path.join(PROJECT_ROOT, "pipeline", "fetch_and_render.py")
PIPELINE_LOCK = os.path.join(DATA_DIR, ".pipeline.lock")

LIMA_TZ = timezone(timedelta(hours=-5))

DAILY_ANIM_PREFIXES = {"tsm", "anom", "viento", "slp"}

MAP_TABS = [
    ("tsm", "Temperatura superficial del mar (TSM)"),
    ("anom", "Anomalía de TSM"),
    ("viento", "Viento zonal y vectores a 850 hPa"),
    ("slp", "Presión a nivel del mar (SLP)"),
    ("hovmoller_nino34", "Hovmöller — Niño 3.4"),
    ("hovmoller_nino12", "Hovmöller — Niño 1+2"),
    ("subsurf", "Subsuperficie — Onda Kelvin"),
]

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Monitor ENSO — resiliencia.cloud"
app.index_string = """<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🌊</text></svg>">
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>"""
server = app.server


@server.route("/figures/<path:filename>")
def figures_route(filename):
    return send_from_directory(FIGURES_DIR, filename)


@server.route("/health")
def health():
    return {"status": "ok"}


def _dates_for(prefix):
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d{{4}}-\d{{2}}-\d{{2}})\.png$")
    dates = []
    for f in glob.glob(os.path.join(FIGURES_DIR, f"{prefix}_*.png")):
        m = pattern.match(os.path.basename(f))
        if m:
            dates.append(m.group(1))
    return sorted(dates, reverse=True)


def _map_tab(prefix, title):
    dates = _dates_for(prefix)
    header = html.Div([
        html.Div([
            html.Div(title, className="chart-title"),
            html.Div("Elige una fecha para ver el panel correspondiente", className="chart-sub"),
        ]),
        dcc.Dropdown(
            id=f"{prefix}-date",
            options=[{"label": d, "value": d} for d in dates],
            value=(dates[0] if dates else None),
            clearable=False, style={"minWidth": "180px"},
            placeholder="Aún no hay datos — corre el pipeline",
            className="enso-dropdown",
        ),
    ], className="chart-header")

    body = [
        html.Div(
            html.Img(id=f"{prefix}-img", src=(f"/figures/{prefix}_{dates[0]}.png" if dates else None)),
            className="chart-figure",
        ) if dates else dbc.Alert(
            "Todavía no se generó ninguna figura para esta variable. "
            "Corre pipeline/fetch_and_render.py (o espera al cron diario).",
            color="warning",
        ),
    ]
    if prefix in DAILY_ANIM_PREFIXES:
        gif_path = os.path.join(FIGURES_DIR, f"{prefix}_anim.gif")
        if os.path.exists(gif_path):
            body.append(html.Div("Evolución — últimos 15 días", className="chart-title mt-3 mb-2"))
            body.append(html.Div(html.Img(src=f"/figures/{prefix}_anim.gif"), className="chart-figure"))

    if prefix == "subsurf":
        body.append(html.P(
            "Fuente: NCEP GODAS (mensual, no diario). Anomalía respecto a la climatología "
            "2015-2024 calculada para este panel — no es el ONI oficial.",
            className="chart-sub mt-2",
        ))
        gif_path = os.path.join(FIGURES_DIR, "subsurf_anim.gif")
        if os.path.exists(gif_path):
            body.append(html.Div("Evolución mensual", className="chart-title mt-3 mb-2"))
            body.append(html.Div(html.Img(src="/figures/subsurf_anim.gif"), className="chart-figure"))

    return html.Div([header] + body, className="chart-card map-panel")


def _register_map_callback(prefix):
    @app.callback(Output(f"{prefix}-img", "src"), Input(f"{prefix}-date", "value"))
    def _update(date_value, prefix=prefix):
        if not date_value:
            return None
        return f"/figures/{prefix}_{date_value}.png"


for _prefix, _title in MAP_TABS:
    _register_map_callback(_prefix)


def _indices_tab():
    csv_path = os.path.join(PROCESSED_DIR, "indices_diarios.csv")
    if not os.path.exists(csv_path):
        return html.Div([
            html.Div("Índices Niño — tendencia diaria", className="chart-title"),
            dbc.Alert("Aún no hay datos — se generan tras la primera corrida del pipeline.",
                      color="warning", className="mt-3"),
        ], className="chart-card")

    df = pd.read_csv(csv_path, parse_dates=["fecha"])
    fig = go.Figure()
    series = [("nino12", "Niño 1+2", "#e2574a"), ("nino3", "Niño 3", "#ff8a65"),
              ("nino34", "Niño 3.4", "#5b9bdb"), ("nino4", "Niño 4", "#7fd4c9")]
    for col, label, color in series:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=df["fecha"], y=df[col], mode="lines",
                                      name=label, line=dict(color=color, width=2)))
    fig.add_hline(y=0.5, line_dash="dot", line_color="rgba(226,87,74,0.6)",
                  annotation_text="+0.5 (umbral El Niño)", annotation_position="top left",
                  annotation_font_color="#a0bfaa")
    fig.add_hline(y=-0.5, line_dash="dot", line_color="rgba(91,155,219,0.6)",
                  annotation_text="-0.5 (umbral La Niña)", annotation_position="bottom left",
                  annotation_font_color="#a0bfaa")
    fig.update_layout(theme.dark_layout(
        yaxis_title="Anomalía (°C)", height=440,
        legend=dict(orientation="h", y=1.12, font=dict(color="#a0bfaa")),
        margin=dict(t=30, l=50, r=20, b=40),
    ))
    return html.Div([
        html.Div([
            html.Div([
                html.Div("Índices Niño — tendencia diaria", className="chart-title"),
                html.Div("Anomalía de TSM por región Niño (índice propio derivado de OISST, no el ONI oficial)",
                          className="chart-sub"),
            ]),
        ], className="chart-header"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
    ], className="chart-card")


def _read_latest():
    path = os.path.join(PROCESSED_DIR, "latest.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _format_updated(latest):
    ts = latest.get("actualizado")
    if not ts:
        return "Todavía no se actualizó"
    dt = datetime.fromisoformat(ts).astimezone(LIMA_TZ)
    return f"Actualizado {dt.strftime('%d %b · %H:%M')}"


def _header():
    is_running = os.path.exists(PIPELINE_LOCK)
    status_text = "Actualizando…" if is_running else _format_updated(_read_latest())
    return html.Header([
        html.Div([
            html.Div("🌊", className="logo-icon", style={"visibility": "hidden"}),
            html.Div([
                html.Div("Monitor ENSO", className="logo-top"),
                html.Div("Perú · Pacífico tropical", className="logo-sub"),
            ]),
        ], className="logo"),
        html.Div([
            html.Div(status_text, id="refresh-status", className="refresh-status"),
            html.Button("↻ Actualizar datos", id="refresh-btn", className="apply-btn",
                        n_clicks=0, disabled=is_running),
            html.Div([html.Span(className="live-dot"), "EN VIVO"], className="live-badge"),
            html.Div(id="header-clock", className="header-time"),
            dcc.Interval(id="clock-tick", interval=1000),
            dcc.Interval(id="refresh-poll", interval=4000, disabled=not is_running),
            dcc.Location(id="refresh-reload", refresh=True),
        ], className="header-right"),
    ], className="enso-header")


@app.callback(Output("header-clock", "children"), Input("clock-tick", "n_intervals"))
def _update_clock(_):
    return datetime.now(LIMA_TZ).strftime("%d %b %Y · %H:%M:%S")


@app.callback(
    Output("refresh-status", "children"),
    Output("refresh-poll", "disabled"),
    Output("refresh-btn", "disabled"),
    Input("refresh-btn", "n_clicks"),
    prevent_initial_call=True,
)
def _trigger_refresh(n_clicks):
    if os.path.exists(PIPELINE_LOCK):
        return "Ya hay una actualización en curso…", False, True
    subprocess.Popen([sys.executable, PIPELINE_SCRIPT], cwd=PROJECT_ROOT)
    return "Actualizando…", False, True


@app.callback(
    Output("refresh-status", "children", allow_duplicate=True),
    Output("refresh-poll", "disabled", allow_duplicate=True),
    Output("refresh-btn", "disabled", allow_duplicate=True),
    Output("refresh-reload", "pathname"),
    Input("refresh-poll", "n_intervals"),
    prevent_initial_call=True,
)
def _poll_refresh(n_intervals):
    if os.path.exists(PIPELINE_LOCK):
        return "Actualizando…", False, True, no_update
    return _format_updated(_read_latest()), True, False, "/"


def serve_layout():
    """Función (no objeto fijo) para que cada recarga del navegador refleje
    las figuras/índices más recientes sin tener que reiniciar el contenedor."""
    return html.Div([
        _header(),
        html.Div([
            html.Div([
                html.Div("Monitor ENSO — Perú / Pacífico tropical", className="page-title"),
                html.Div("TSM, anomalías, viento, presión y subsuperficie del Pacífico ecuatorial, "
                         "actualizado diariamente.", className="page-sub"),
            ], className="page-intro"),
            dcc.Tabs([
                dcc.Tab(label=title, children=_map_tab(prefix, title),
                        className="enso-tab", selected_className="enso-tab--selected")
                for prefix, title in MAP_TABS
            ] + [
                dcc.Tab(label="Índices", children=_indices_tab(),
                        className="enso-tab", selected_className="enso-tab--selected"),
                dcc.Tab(label="Contexto histórico", children=layout_historico.layout(),
                        className="enso-tab", selected_className="enso-tab--selected"),
            ], className="enso-tabs", parent_className="enso-tabs-parent"),
            html.Footer([
                html.P("Fuentes: NOAA OISST v2 · NCEP GDAS · NOAA CPC. "
                       "Pipeline propio ejecutado diariamente en este servidor."),
            ], className="enso-footer"),
        ], className="enso-shell"),
    ])


app.layout = serve_layout

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082, debug=False)
