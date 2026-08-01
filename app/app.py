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
import secrets
import subprocess
import sys
from datetime import datetime, timezone, timedelta

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html, no_update
from flask import redirect, request, send_from_directory, session
from werkzeug.security import check_password_hash

import layout_historico
import theme

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
FIGURES_DIR = os.path.join(DATA_DIR, "figures")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

PIPELINE_SCRIPT = os.path.join(PROJECT_ROOT, "pipeline", "fetch_and_render.py")
PIPELINE_LOCK = os.path.join(DATA_DIR, ".pipeline.lock")


def _pipeline_running():
    """A diferencia de un simple os.path.exists(PIPELINE_LOCK): si el
    contenedor se reinicia a mitad de una corrida (p.ej. al desplegar un
    cambio de código), el proceso muere sin llegar a borrar su propio lock
    — el archivo queda huérfano y la UI se quedaría en "Actualizando…" para
    siempre. Acá se verifica que el PID adentro del lock siga vivo de
    verdad, y si no, se limpia el archivo solo."""
    if not os.path.exists(PIPELINE_LOCK):
        return False
    try:
        with open(PIPELINE_LOCK) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        try:
            os.remove(PIPELINE_LOCK)
        except FileNotFoundError:
            pass
        return False

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

# Login propio (reemplaza el basic-auth de nginx — mismo usuario/clave, pero
# con una pantalla en vez del popup nativo del navegador). El hash nunca
# vive en el código: viene por variable de entorno (docker-compose.yml).
server.secret_key = os.environ.get("ENSO_SECRET_KEY") or secrets.token_hex(32)
server.permanent_session_lifetime = timedelta(days=7)
AUTH_USER = os.environ.get("ENSO_AUTH_USER", "")
AUTH_PASS_HASH = os.environ.get("ENSO_AUTH_PASS_HASH", "")

LOGIN_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Iniciar sesión — Monitor ENSO</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Space+Grotesk:wght@600;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background-color: #0d2a1e;
    background-image: radial-gradient(ellipse 80% 50% at 50% -10%, rgba(47,107,70,0.25), transparent),
                       radial-gradient(ellipse 60% 40% at 100% 100%, rgba(95,207,141,0.08), transparent);
    font-family: 'Inter', system-ui, sans-serif; color: #e2f0e8;
  }}
  .card {{
    width: 100%; max-width: 720px; margin: 20px;
    display: flex; flex-wrap: wrap; align-items: stretch;
    background: rgba(6,12,8,0.95); backdrop-filter: blur(16px);
    border: 1px solid rgba(255,255,255,0.08); border-radius: 16px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.65); overflow: hidden;
  }}
  .media {{ flex: 1 1 280px; min-height: 220px; background: #06140d; }}
  .media img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
  .panel {{ flex: 1 1 320px; padding: 32px 28px; }}
  .logo {{ text-align: center; margin-bottom: 24px; }}
  .logo h1 {{
    font-family: 'Space Grotesk', sans-serif; font-size: 1.35rem; font-weight: 700;
    line-height: 1.25; letter-spacing: -0.01em; text-wrap: balance;
  }}
  .logo h1 .r {{ color: #ff5252; }}
  .logo h1 .b {{ color: #5b9bdb; }}
  .logo p {{ font-size: 0.72rem; color: #5a8f70; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 8px; }}
  label {{ display: block; font-size: 0.72rem; font-weight: 700; color: #5a8f70;
           text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }}
  input {{
    width: 100%; padding: 10px 12px; margin-bottom: 16px;
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; color: #e2f0e8; font-size: 0.9rem; font-family: inherit;
  }}
  input:focus {{ outline: none; border-color: #5fcf8d; background: rgba(255,255,255,0.08); }}
  button {{
    width: 100%; padding: 11px; border: 0; border-radius: 8px; cursor: pointer;
    background: #2f6b46; color: #e2f0e8; font-weight: 700; font-size: 0.85rem;
    letter-spacing: 0.01em; font-family: inherit; transition: all 0.2s;
  }}
  button:hover {{ filter: brightness(1.12); transform: translateY(-1px); }}
  .error {{
    margin-top: 14px; padding: 10px 12px; border-radius: 8px; font-size: 0.8rem;
    background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.35); color: #f3a5a5;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="media"><img src="/assets/Logos/past-el-nino-gif-1.webp" alt="El Niño"></div>
    <div class="panel">
      <div class="logo">
        <h1><span class="r">E</span>l <span class="r">N</span>iño-<span class="b">O</span>scilación del <span class="b">S</span>ur (ENSO)</h1>
        <p>Monitoreo</p>
      </div>
      <form method="POST">
        <label>Usuario</label>
        <input type="text" name="username" autofocus required>
        <label>Contraseña</label>
        <input type="password" name="password" required>
        <button type="submit">Iniciar sesión</button>
        {error_html}
      </form>
    </div>
  </div>
</body>
</html>"""


@server.before_request
def _require_login():
    if not AUTH_PASS_HASH:
        return  # sin credenciales configuradas -> sin login (evita bloquearse afuera)
    if request.path in ("/login", "/health") or request.path.startswith("/assets/"):
        return
    if not session.get("logged_in"):
        return redirect(f"/login?next={request.path}")


@server.route("/login", methods=["GET", "POST"])
def login():
    error_html = ""
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == AUTH_USER and check_password_hash(AUTH_PASS_HASH, p):
            session.permanent = True
            session["logged_in"] = True
            return redirect(request.args.get("next") or "/")
        error_html = '<div class="error">Usuario o contraseña incorrectos.</div>'
    return LOGIN_HTML.format(error_html=error_html)


@server.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@server.route("/figures/<path:filename>")
def figures_route(filename):
    return send_from_directory(FIGURES_DIR, filename)


@server.route("/health")
def health():
    return {"status": "ok"}


def _fig_url(filename):
    """Src con cache-busting por mtime — sin esto el navegador puede quedarse
    con una copia vieja de archivos de nombre fijo (los *_anim.gif, o incluso
    un tsm_<fecha>.png si el botón "Actualizar datos" lo regenera dos veces
    el mismo día) porque la URL nunca cambia aunque el contenido sí."""
    path = os.path.join(FIGURES_DIR, filename)
    if not os.path.exists(path):
        return None
    return f"/figures/{filename}?v={int(os.path.getmtime(path))}"


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
            html.Img(id=f"{prefix}-img", src=(_fig_url(f"{prefix}_{dates[0]}.png") if dates else None)),
            className="chart-figure",
        ) if dates else dbc.Alert(
            "Todavía no se generó ninguna figura para esta variable. "
            "Corre pipeline/fetch_and_render.py (o espera al cron diario).",
            color="warning",
        ),
    ]
    if prefix in DAILY_ANIM_PREFIXES:
        anim_url = _fig_url(f"{prefix}_anim.gif")
        if anim_url:
            body.append(html.Div("Evolución — últimos 15 días", className="chart-title mt-3 mb-2"))
            body.append(html.Div(html.Img(src=anim_url), className="chart-figure"))

    if prefix == "subsurf":
        body.append(html.P(
            "Fuente: NCEP GODAS (mensual, no diario). Anomalía respecto a la climatología "
            "2015-2024 calculada para este panel — no es el ONI oficial.",
            className="chart-sub mt-2",
        ))
        composite_url = _fig_url("subsurf_composite_anim.gif")
        if composite_url:
            body.append(html.Div("Temperatura observada + anomalía — Pacífico ecuatorial", className="chart-title mt-3 mb-2"))
            body.append(html.Div(
                "Corte 2°S-2°N con el mapa de las regiones Niño arriba, animado mes a mes (año en curso).",
                className="chart-sub mb-2",
            ))
            body.append(html.Div(html.Img(src=composite_url), className="chart-figure"))

    return html.Div([header] + body, className="chart-card map-panel")


def _register_map_callback(prefix):
    @app.callback(Output(f"{prefix}-img", "src"), Input(f"{prefix}-date", "value"))
    def _update(date_value, prefix=prefix):
        if not date_value:
            return None
        return _fig_url(f"{prefix}_{date_value}.png")


for _prefix, _title in MAP_TABS:
    _register_map_callback(_prefix)


def _hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _index_region_figure(df, col, label, color):
    """Un gráfico por región (no las 4 juntas) con anotaciones de pico
    máximo y días sobre el umbral — mismo espíritu que el infográfico de
    referencia, pero con lo que ya calculamos (anomalía diaria de OISST):
    no tenemos descargados años históricos de SST cruda para armar una
    climatología mensual real, así que no hay una segunda línea "promedio
    histórico" — el 0 de la anomalía ya ES esa referencia (NOAA la calcula
    restando su propia climatología día a día)."""
    valid = df.dropna(subset=[col])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["fecha"], y=df[col], mode="lines", name=label,
        line=dict(color=color, width=2.5),
        fill="tozeroy", fillcolor=_hex_to_rgba(color, 0.10),
    ))
    fig.add_hline(y=0, line_color="rgba(160,191,170,0.35)", line_width=1)
    fig.add_hline(y=0.5, line_dash="dot", line_color="rgba(226,87,74,0.75)",
                  annotation_text="+0.5 °C · umbral El Niño", annotation_position="top left",
                  annotation_font_color="#e2574a")
    fig.add_hline(y=-0.5, line_dash="dot", line_color="rgba(91,155,219,0.65)",
                  annotation_text="-0.5 °C · umbral La Niña", annotation_position="bottom left",
                  annotation_font_color="#5b9bdb")

    if len(valid):
        peak_idx = valid[col].idxmax()
        peak_val = valid.loc[peak_idx, col]
        peak_date = valid.loc[peak_idx, "fecha"]
        days_over = int((valid[col] > 0.5).sum())

        fig.add_trace(go.Scatter(
            x=[peak_date], y=[peak_val], mode="markers",
            marker=dict(size=9, color=color, line=dict(width=2, color="#0d2a1e")),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_annotation(
            x=peak_date, y=peak_val, text=f"Pico: {peak_val:.2f} °C<br>{peak_date.strftime('%d %b')}",
            showarrow=True, arrowhead=2, ax=0, ay=-42,
            font=dict(color=color, size=11), bgcolor="rgba(6,12,8,0.9)",
            bordercolor=color, borderwidth=1, borderpad=4,
        )
        fig.add_annotation(
            xref="paper", yref="paper", x=0.99, y=1.16, xanchor="right",
            text=f"{days_over} días sobre el umbral de El Niño en lo que va de 2026",
            showarrow=False, font=dict(color="#a0bfaa", size=11),
        )

    fig.update_layout(theme.dark_layout(
        yaxis_title="Anomalía (°C)", height=380,
        margin=dict(t=55, l=50, r=20, b=40),
        showlegend=False,
    ))
    return fig


def _indices_tab():
    csv_path = os.path.join(PROCESSED_DIR, "indices_diarios.csv")
    if not os.path.exists(csv_path):
        return html.Div([
            html.Div("Índices Niño — tendencia diaria", className="chart-title"),
            dbc.Alert("Aún no hay datos — se generan tras la primera corrida del pipeline.",
                      color="warning", className="mt-3"),
        ], className="chart-card")

    df = pd.read_csv(csv_path, parse_dates=["fecha"])
    regions = [("nino12", "Niño 1+2", "#e2574a"), ("nino34", "Niño 3.4", "#5b9bdb")]
    cards = []
    for col, label, color in regions:
        if col not in df.columns:
            continue
        cards.append(html.Div([
            html.Div([
                html.Div([
                    html.Div(f"Evolución de la anomalía de TSM — Región {label}", className="chart-title"),
                    html.Div("Anomalía diaria respecto al promedio histórico de NOAA (índice propio "
                              "derivado de OISST, no el ONI oficial).", className="chart-sub"),
                ]),
            ], className="chart-header"),
            dcc.Graph(figure=_index_region_figure(df, col, label, color), config={"displayModeBar": False}),
        ], className="chart-card"))
    return html.Div(cards)


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


def _read_pipeline_status():
    path = os.path.join(PROCESSED_DIR, "pipeline_status.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _status_text():
    """A diferencia de mostrar solo la fecha de la última corrida EXITOSA
    (que puede quedar vieja en silencio si la corrida más reciente falló,
    como pasó con el sst_mean.nc corrupto), esto avisa explícitamente si
    lo último que se intentó se cayó."""
    base = _format_updated(_read_latest())
    status = _read_pipeline_status()
    if status and not status.get("ok", True):
        err = status.get("error", "error desconocido")
        return f"⚠ Falló la última actualización ({err}) — {base}"
    return base


def _header():
    is_running = _pipeline_running()
    status_text = "Actualizando…" if is_running else _status_text()
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
            html.A("Cerrar sesión", href="/logout", className="logout-link") if AUTH_PASS_HASH else None,
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
    if _pipeline_running():
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
    if _pipeline_running():
        return "Actualizando…", False, True, no_update
    return _status_text(), True, False, "/"


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
