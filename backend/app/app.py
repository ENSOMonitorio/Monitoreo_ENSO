"""
Monitor ENSO — backend Flask. Sirve la API JSON (/api/*), las figuras
generadas por backend/pipeline/fetch_and_render.py (/figures/<file>) y el
frontend Angular ya compilado (backend/app/static/, generado en la imagen
Docker por el stage de build de frontend/). Expuesto vía gunicorn como
`app:server` en el puerto 8082 (mismo patrón que los otros dashboards de
este VPS: mapas.resiliencia.cloud y riesgo.resiliencia.cloud).
"""

import glob
import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timezone, timedelta

import pandas as pd
import plotly.graph_objects as go
from flask import Flask, Response, abort, jsonify, redirect, render_template, request, send_from_directory, session
from werkzeug.security import check_password_hash

import layout_historico
import theme

APP_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(APP_DIR)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
FIGURES_DIR = os.path.join(DATA_DIR, "figures")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# Build de Angular (frontend/), copiado acá por el Dockerfile en producción.
# En dev local sin Docker, este directorio no existe hasta que se corra
# `ng build` a mano y se copie su salida — mientras tanto la SPA devuelve
# 404 en vez de romper el resto del backend (ver spa() más abajo).
STATIC_DIR = os.path.join(APP_DIR, "static")
LOGIN_ASSETS_DIR = os.path.join(APP_DIR, "assets", "Logos")

PIPELINE_SCRIPT = os.path.join(BACKEND_DIR, "pipeline", "fetch_and_render.py")
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
_MAP_TAB_PREFIXES = {prefix for prefix, _ in MAP_TABS}

# Mismas 4 regiones que indices.py/pipeline calculan en el CSV; hoy la
# pestaña "Índices" del frontend solo dibuja nino12/nino34, pero la API
# expone las 4 por si se quiere ampliar luego.
# Mismos colores que las cajas Niño de los mapas (theme.NINO_COLORS), para
# que el gráfico de cada región y su caja en el mapa se reconozcan.
INDEX_REGIONS = {
    key: {"label": label, "color": theme.NINO_COLORS[label]}
    for key, label in (
        ("nino12", "Niño 1+2"),
        ("nino34", "Niño 3.4"),
        ("nino3", "Niño 3"),
        ("nino4", "Niño 4"),
    )
}

server = Flask(__name__)

# Montar Dash de Subsuperficie y Boyas TAO en /subsurf-dash/
try:
    from subsuperficie.app import mount_dash
    dash_app = mount_dash(server)
except Exception as e:
    print(f"[WARN] No se pudo montar subsuperficie Dash en Flask: {e}")

# Login propio (reemplaza el basic-auth de nginx — mismo usuario/clave, pero
# con una pantalla en vez del popup nativo del navegador). El hash nunca
# vive en el código: viene por variable de entorno (docker-compose.yml).
server.secret_key = os.environ.get("ENSO_SECRET_KEY") or secrets.token_hex(32)
server.permanent_session_lifetime = timedelta(days=7)
AUTH_USER = os.environ.get("ENSO_AUTH_USER", "")
AUTH_PASS_HASH = os.environ.get("ENSO_AUTH_PASS_HASH", "")


def _safe_next(target):
    """Destino tras el login: solo rutas internas. Sin esto, un enlace como
    /login?next=https://otro.sitio llevaba a la persona fuera del monitor
    justo después de escribir su clave (redirección abierta)."""
    if not target or not target.startswith("/") or target.startswith("//") or "\\" in target:
        return "/"
    return target


@server.before_request
def _require_login():
    if not AUTH_PASS_HASH:
        return  # sin credenciales configuradas -> sin login (evita bloquearse afuera)
    if request.path in ("/login", "/health") or request.path.startswith("/login-assets/"):
        return
    if not session.get("logged_in"):
        return redirect(f"/login?next={request.path}")


@server.route("/login", methods=["GET", "POST"])
def login():
    error = False
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == AUTH_USER and check_password_hash(AUTH_PASS_HASH, p):
            session.permanent = True
            session["logged_in"] = True
            return redirect(_safe_next(request.args.get("next")))
        error = True
    return render_template("login.html", error=error)


@server.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@server.route("/login-assets/<path:filename>")
def login_assets(filename):
    return send_from_directory(LOGIN_ASSETS_DIR, filename)


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
    warm = theme.NINO_COLORS["Niño 1+2"]
    cold = theme.NINO_COLORS["Niño 3.4"]
    fig.add_hline(y=0, line_color=theme.AXIS, line_width=1)
    fig.add_hline(y=0.5, line_dash="dot", line_color=_hex_to_rgba(warm, 0.75),
                  annotation_text="+0.5 °C · umbral El Niño", annotation_position="top left",
                  annotation_font_color=theme.TEXT_2)
    fig.add_hline(y=-0.5, line_dash="dot", line_color=_hex_to_rgba(cold, 0.75),
                  annotation_text="-0.5 °C · umbral La Niña", annotation_position="bottom left",
                  annotation_font_color=theme.TEXT_2)

    if len(valid):
        peak_idx = valid[col].idxmax()
        peak_val = valid.loc[peak_idx, col]
        peak_date = valid.loc[peak_idx, "fecha"]
        days_over = int((valid[col] > 0.5).sum())

        fig.add_trace(go.Scatter(
            x=[peak_date], y=[peak_val], mode="markers",
            marker=dict(size=9, color=color, line=dict(width=2, color=theme.SURFACE)),
            showlegend=False, hoverinfo="skip",
        ))
        fig.add_annotation(
            x=peak_date, y=peak_val, text=f"Pico: {peak_val:.2f} °C<br>{peak_date.strftime('%d %b')}",
            showarrow=True, arrowhead=2, ax=0, ay=-42,
            font=dict(color=theme.TEXT, size=11), bgcolor=theme.SURFACE,
            bordercolor=color, borderwidth=1, borderpad=4,
        )
        fig.add_annotation(
            xref="paper", yref="paper", x=0.99, y=1.16, xanchor="right",
            text=f"{days_over} días sobre el umbral de El Niño en lo que va de 2026",
            showarrow=False, font=dict(color=theme.MUTED, size=11),
        )

    fig.update_layout(theme.chart_layout(
        yaxis_title="Anomalía (°C)", height=380,
        margin=dict(t=55, l=50, r=20, b=40),
        showlegend=False,
    ))
    return fig


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


# ---------------------------------------------------------------------------
# API JSON — consumida por el frontend Angular (frontend/src/app). Cada
# endpoint envuelve la misma lógica que antes usaba el layout de Dash, para
# no reimplementar nada. Quedan protegidos por el mismo _require_login que
# el resto del sitio (no están en el allowlist de arriba).
# ---------------------------------------------------------------------------

@server.route("/api/config")
def api_config():
    return jsonify({
        "map_tabs": [
            {"prefix": prefix, "title": title, "has_daily_anim": prefix in DAILY_ANIM_PREFIXES}
            for prefix, title in MAP_TABS
        ],
        "auth_enabled": bool(AUTH_PASS_HASH),
    })


@server.route("/api/figures/<prefix>")
def api_figures(prefix):
    if prefix not in _MAP_TAB_PREFIXES:
        abort(404)
    dates = _dates_for(prefix)
    selected = request.args.get("date") or (dates[0] if dates else None)
    return jsonify({
        "prefix": prefix,
        "dates": dates,
        "selected_date": selected,
        "image_url": _fig_url(f"{prefix}_{selected}.png") if selected else None,
        "anim_url": _fig_url(f"{prefix}_anim.gif") if prefix in DAILY_ANIM_PREFIXES else None,
        "composite_anim_url": _fig_url("subsurf_composite_anim.gif") if prefix == "subsurf" else None,
    })


@server.route("/api/indices")
def api_indices():
    return jsonify({"regions": [{"key": key, **meta} for key, meta in INDEX_REGIONS.items()]})


@server.route("/api/indices/<region>")
def api_indices_region(region):
    if region not in INDEX_REGIONS:
        abort(404)
    csv_path = os.path.join(PROCESSED_DIR, "indices_diarios.csv")
    if not os.path.exists(csv_path):
        return jsonify({"available": False})
    df = pd.read_csv(csv_path, parse_dates=["fecha"])
    if region not in df.columns:
        return jsonify({"available": False})
    meta = INDEX_REGIONS[region]
    fig = _index_region_figure(df, region, meta["label"], meta["color"])
    # fig.to_json() (no jsonify(fig.to_dict())): el encoder de Plotly sabe
    # serializar los pandas.Timestamp de las anotaciones, el de Flask no.
    return Response(fig.to_json(), mimetype="application/json")


@server.route("/api/historico/oni")
def api_historico_oni():
    fig = layout_historico.build_oni_figure()
    return Response(fig.to_json(), mimetype="application/json")


@server.route("/api/historico/eventos")
def api_historico_eventos():
    return jsonify(layout_historico.EVENTS)


@server.route("/api/goes19")
def api_goes19():
    """Animación GOES-19 Banda 13 (temperatura de brillo) — a diferencia de
    los MAP_TABS no tiene selector de fecha ni serie histórica: es un único
    GIF de nombre fijo, regenerado a mano con `python -m GOES19.goes` (desde
    backend/app/) o vía el pipeline cuando se agende."""
    return jsonify({"anim_url": _fig_url("goes19_anim.gif")})


@server.route("/api/status")
def api_status():
    is_running = _pipeline_running()
    return jsonify({
        "text": "Actualizando…" if is_running else _status_text(),
        "is_running": is_running,
    })


@server.route("/api/pipeline/status")
def api_pipeline_status():
    status = _read_pipeline_status()
    return jsonify({
        "running": _pipeline_running(),
        "ok": status.get("ok") if status else None,
        "error": status.get("error") if status else None,
        "last_attempt_ts": status.get("ts") if status else None,
        "last_success": _read_latest(),
    })


@server.route("/api/pipeline/run", methods=["POST"])
def api_pipeline_run():
    if _pipeline_running():
        return jsonify({"started": False, "reason": "already_running"}), 409
    subprocess.Popen([sys.executable, PIPELINE_SCRIPT], cwd=PROJECT_ROOT)
    return jsonify({"started": True}), 202


# ---------------------------------------------------------------------------
# Frontend Angular ya compilado (backend/app/static/, generado por el stage
# de build de frontend/ en el Dockerfile). Cualquier ruta que no sea una API
# ni un archivo estático conocido cae al index.html de la SPA, para que el
# router de Angular la resuelva del lado del cliente (soporta refrescar el
# navegador en una ruta profunda como /indices sin dar 404).
# ---------------------------------------------------------------------------

@server.route("/", defaults={"path": ""})
@server.route("/<path:path>")
def spa(path):
    if path.startswith("subsurf-dash"):
        abort(404)
    candidate = os.path.join(STATIC_DIR, path) if path else None
    if candidate and os.path.isfile(candidate):
        return send_from_directory(STATIC_DIR, path)
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        abort(404)
    return send_from_directory(STATIC_DIR, "index.html")

if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8082, debug=False)
