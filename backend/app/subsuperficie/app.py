# ============================================================
# APP.PY — Aplicación Dash principal
# ============================================================
import os, sys, re, tempfile

if sys.platform.startswith("win"):
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_CUR_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_CUR_DIR)
_BACKEND_DIR = os.path.dirname(_APP_DIR)
_ROOT_DIR = os.path.dirname(_BACKEND_DIR)
if _CUR_DIR not in sys.path:
    sys.path.insert(0, _CUR_DIR)
if _APP_DIR not in sys.path:
    sys.path.insert(1, _APP_DIR)

import numpy as np
import pandas as pd
import netCDF4 as nc
import requests
from datetime import datetime
import plotly.io as pio

from dash import (Dash, dcc, html, Input, Output, State,
                  callback_context, no_update)
import plotly.graph_objects as go

try:
    from estilo import etiquetas_color, colores_default
    from graficas import (procesar_nc, procesar_nc_perfil, graficar_sst,
                          graficar_dyn, graficar_iso, graficar_w,
                          calcular_datos_contorno_t, construir_plots_contorno_t,
                          defaults_var, figura_aviso, listar_cmaps)
except ImportError:
    from subsuperficie.estilo import etiquetas_color, colores_default
    from subsuperficie.graficas import (procesar_nc, procesar_nc_perfil, graficar_sst,
                                        graficar_dyn, graficar_iso, graficar_w,
                                        calcular_datos_contorno_t, construir_plots_contorno_t,
                                        defaults_var, figura_aviso, listar_cmaps)

# ============================================================
# DATOS
# ============================================================
anio_actual = datetime.now().year

BOYAS_FILTRADAS = {
    "dyn": ["0.7n110w","0n110w","0n125w","0n140w","0n155w","0n165e","0n170e",
            "0n170w","0n180w","0n95w","10n95w","2n110w","2n125w","2n140w",
            "2n155w","2n165e","2n170w","2n180w","2n95w","2s110w","2s125w",
            "2s140w","2s155w","2s165e","2s170w","2s180w","2s95w","3.5n95w",
            "5n110w","5n125w","5n140w","5n155w","5n165e","5n170w","5n180w",
            "5n95w","5s110w","5s125w","5s140w","5s155w","5s165e","5s170w",
            "5s180w","5s95w","7n132w","7n140w","7n147w","8n110w","8n125w",
            "8n155w","8n165e","8n167e","8n168e","8n170w","8n180w","8n95w",
            "8s110w","8s125w","8s155w","8s165e","8s170w","8s180w","8s95w",
            "9n140w"],
    "iso": ["0.7n110w","0.7s110w","0n108w","0n110.5w","0n110w","0n125w",
            "0n140w","0n152w","0n155w","0n165e","0n170e","0n170w","0n180w",
            "0n85w","0n95w","10n95w","1n153w","1s153w","2n110w","2n125w",
            "2n140w","2n155w","2n165e","2n170w","2n180w","2n95w","2s110w",
            "2s125w","2s140w","2s155w","2s165e","2s170w","2s180w","2s95w",
            "3.5n95w","5n110w","5n125w","5n140w","5n155w","5n165e","5n170w",
            "5n180w","5n95w","5s110w","5s125w","5s140w","5s155w","5s165e",
            "5s170w","5s180w","5s95w","7n132w","7n140w","7n147w","7n150w",
            "8n110w","8n125w","8n150w","8n155w","8n165e","8n167e","8n168e",
            "8n170w","8n180w","8n95w","8s110w","8s125w","8s155w","8s165e",
            "8s170w","8s180w","8s95w","9n140w"],
    "sst": ["0.7n110w","0.7s110w","0n108w","0n110.5w","0n110w","0n125w",
            "0n140w","0n152w","0n155w","0n165e","0n170e","0n170w","0n180w",
            "0n85w","0n95w","10n95w","1n153w","1s153w","2n110w","2n125w",
            "2n140w","2n155w","2n165e","2n170w","2n180w","2n95w","2s110w",
            "2s125w","2s140w","2s155w","2s165e","2s170w","2s180w","2s95w",
            "3.5n95w","5n110w","5n125w","5n140w","5n155w","5n165e","5n170w",
            "5n180w","5n95w","5s110w","5s125w","5s140w","5s155w","5s165e",
            "5s170w","5s180w","5s95w","6n150w","7n132w","7n140w","7n147w",
            "7n150w","8n110w","8n125w","8n150w","8n155w","8n165e","8n167e",
            "8n168e","8n170w","8n180w","8n95w","8s110w","8s125w","8s155w",
            "8s165e","8s170w","8s180w","8s95w","9n140w"],
    "t":   ["0.7n110w","0.7s110w","0n108w","0n110.5w","0n110w","0n125w",
            "0n140w","0n152w","0n155w","0n165e","0n170e","0n170w","0n180w",
            "0n85w","0n95w","10n95w","1n153w","1s153w","2n110w","2n125w",
            "2n140w","2n155w","2n165e","2n170w","2n180w","2n95w","2s110w",
            "2s125w","2s140w","2s155w","2s165e","2s170w","2s180w","2s95w",
            "3.5n95w","5n110w","5n125w","5n140w","5n155w","5n165e","5n170w",
            "5n180w","5n95w","5s110w","5s125w","5s140w","5s155w","5s165e",
            "5s170w","5s180w","5s95w","6n150w","7n132w","7n140w","7n147w",
            "7n150w","8n110w","8n125w","8n150w","8n155w","8n165e","8n167e",
            "8n168e","8n170w","8n180w","8n95w","8s110w","8s125w","8s155w",
            "8s165e","8s170w","8s180w","8s95w","9n140w"],
    "w":   ["0.7n110w","0.7s110w","0n108w","0n110.5w","0n110w","0n125w",
            "0n140w","0n152w","0n155w","0n165e","0n170e","0n170w","0n176w",
            "0n180w","0n85w","0n95w","10n95w","1n153w","1s153w","1s167e",
            "2n110w","2n125w","2n140w","2n155w","2n157w","2n165e","2n170w",
            "2n180w","2n95w","2s110w","2s125w","2s140w","2s155w","2s165e",
            "2s170w","2s180w","2s95w","3.5n95w","5n110w","5n125w","5n140w",
            "5n155w","5n165e","5n170w","5n180w","5n95w","5s110w","5s125w",
            "5s140w","5s155w","5s165e","5s170w","5s180w","5s95w","6n150w",
            "7n132w","7n140w","7n147w","7n150w","8n110w","8n125w","8n150w",
            "8n155w","8n165e","8n167e","8n168e","8n170w","8n180w","8n95w",
            "8s110w","8s125w","8s155w","8s165e","8s170w","8s180w","8s95w",
            "9n140w"],
}

MAPA_VARIABLES_NC = {"sst": "T_25", "dyn": "DYN_13", "iso": "ISO_6",
                     "t": None, "w": "WU_422"}

VAR_LABELS = {
    "dyn": "Altura Dinámica",
    "iso": "Isoterma 20°C",
    "sst": "Temperatura Superficial",
    "t":   "Temperatura Subsuperficial",
    "w":   "Vientos",
}


def parsear_boya(id_boya):
    m_lat = re.match(r"^([0-9.]+)([ns])", id_boya)
    if not m_lat: return None
    lat_num = float(m_lat.group(1))
    lat = lat_num if m_lat.group(2) == "n" else -lat_num
    m_lon = re.search(r"([0-9.]+)([ew])$", id_boya)
    if not m_lon: return None
    lon_num = float(m_lon.group(1))
    lon = lon_num if m_lon.group(2) == "e" else -lon_num
    lon_original = lon
    if lon > 0 and lon in (165, 167, 168, 170):
        lon -= 360
    return {"lat": lat, "lng": lon, "lng_real": lon,
            "lng_original": lon_original, "id": id_boya}


def _asignar_region(row):
    lat, lng = row["lat"], row["lng_real"]
    if -10 <= lat <= 0 and -90 <= lng <= -80: return "Niño 1+2"
    if -5 <= lat <= 5 and -150 <= lng <= -90: return "Niño 3"
    if -5 <= lat <= 5 and (lng >= 160 or lng <= -150): return "Niño 4"
    if -5 <= lat <= 5 and -170 <= lng <= -120: return "Niño 3.4"
    return "Pacífico Abierto"


def crear_df_desde_lista(lista_ids):
    rows = [parsear_boya(i) for i in lista_ids]
    rows = [r for r in rows if r]
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["tipo"] = np.where(df["lat"] == 0, "Boyas Ecuatoriales",
                          "Boyas Perfiladoras")
    df["region"] = df.apply(_asignar_region, axis=1)
    df["color"] = np.where(df["lat"] == 0, "#DC2626", "#0369A1")
    df["label"] = df.apply(lambda r: (
        f"Boya TAO: {abs(r['lat'])}°{'N' if r['lat']>=0 else 'S'} | "
        f"{abs(r['lng_original'])}°{'E' if r['lng_original']>=0 else 'W'}"),
        axis=1)
    return df


BOYAS_POR_VARIABLE = {v: crear_df_desde_lista(BOYAS_FILTRADAS[v])
                      for v in BOYAS_FILTRADAS}

# Lista de colormaps (una vez, al arrancar)
CMAPS_LIST = listar_cmaps()

# ============================================================
# CACHÉ NetCDF + CACHÉ CONTORNO T
# ============================================================
_project_cache = os.path.join(_ROOT_DIR, "data", "raw", "tao_cache")
try:
    os.makedirs(_project_cache, exist_ok=True)
    CACHE_DIR = _project_cache
except Exception:
    CACHE_DIR = os.path.join(tempfile.gettempdir(), "tao_cache")
    os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_NC = {}
_CACHE_CONTORNO_T = {}
BASE_URL = ("https://www.pmel.noaa.gov/tao/taoweb/disdel_data/"
            "cdf/sites/daily/")


def _fmt_num(x):
    if x == int(x):
        return str(int(abs(x)))
    return str(abs(x))


def _nombre_archivo_nc(var_id, boya):
    lat = boya["lat"]; lng_orig = boya["lng_original"]
    lat_s = _fmt_num(lat); lon_s = _fmt_num(lng_orig)
    lat_dir = "n" if lat >= 0 else "s"
    lon_dir = "w" if lng_orig < 0 else "e"
    return f"{var_id}{lat_s}{lat_dir}{lon_s}{lon_dir}_dy.cdf"


def obtener_nc_boya(var_id, boya):
    nombre = _nombre_archivo_nc(var_id, boya)
    if nombre in CACHE_NC:
        return CACHE_NC[nombre]
    ruta = os.path.join(CACHE_DIR, nombre)
    if not os.path.exists(ruta):
        try:
            r = requests.get(BASE_URL + nombre, timeout=60)
            if r.status_code != 200:
                print(f"[TAO] 404: {BASE_URL + nombre}")
                return None
            with open(ruta, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print(f"[TAO] Error descarga: {e}")
            return None
    try:
        ncfile = nc.Dataset(ruta, "r")
    except Exception as e:
        print(f"[TAO] Error abriendo {ruta}: {e}")
        return None
    CACHE_NC[nombre] = ncfile
    return ncfile


def _datos_t_cached(boya_id, df_perfil, anios_p1, anios_p2,
                    clim_ini, clim_fin, prof_max):
    """Cachea SOLO la interpolación (no depende del cmap)."""
    key = (boya_id, anios_p1[0], anios_p2[0], clim_ini, clim_fin, prof_max)
    if key in _CACHE_CONTORNO_T:
        print(f"[TAO] Cache HIT -> {key}")
        return _CACHE_CONTORNO_T[key]
    datos = calcular_datos_contorno_t(df_perfil, anios_p1, anios_p2,
                                      inicio=clim_ini, fin=clim_fin,
                                      prof_max=prof_max)
    _CACHE_CONTORNO_T[key] = datos
    while len(_CACHE_CONTORNO_T) > 30:
        oldest = next(iter(_CACHE_CONTORNO_T))
        del _CACHE_CONTORNO_T[oldest]
    return datos


# ============================================================
# COMPONENTES UI
# ============================================================
def _titulo_sidebar(titulo, subtitulo):
    return html.Div([
        html.Div("CONFIGURACIÓN", className="titulo-sidebar"),
        html.Div(titulo, className="subtitulo-sidebar"),
        html.Div(subtitulo, className="subtitulo-sidebar-sm"),
    ], style={"padding": "6px 4px 15px 4px"})


def _accordion_item(titulo, icono, contenido, abierto=True):
    summary = html.Summary([
        html.Span(icono, style={"marginRight": "8px"}),
        html.Span(titulo),
    ], className="accordion-button")
    body = html.Div(contenido, className="accordion-body")
    kwargs = {"className": "accordion-item"}
    if abierto:
        kwargs["open"] = True
    return html.Details([summary, body], **kwargs)


def _slider_color(var_id, idx):
    labs = etiquetas_color(var_id)
    defs = colores_default(var_id)
    return html.Div([
        html.Label(labs[idx], className="form-label",
                   style={"fontSize": "0.78rem", "marginBottom": "2px"}),
        html.Div(style={"display": "flex", "gap": "6px",
                        "alignItems": "center"}, children=[
            html.Div(id=f"prev{idx+1}_{var_id}",
                     style={"width": "32px", "height": "32px",
                            "borderRadius": "6px",
                            "border": "1px solid #B8D4E3",
                            "backgroundColor": defs[idx],
                            "flexShrink": "0"}),
            dcc.Input(id=f"col{idx+1}_{var_id}", type="text",
                      value=defs[idx], placeholder="#RRGGBB",
                      debounce=True,
                      style={"flex": "1", "height": "32px",
                             "border": "1px solid #B8D4E3",
                             "borderRadius": "6px",
                             "padding": "4px 8px",
                             "fontFamily": "monospace",
                             "fontSize": "0.82rem"}),
        ]),
    ], style={"marginBottom": "8px"})


def _panel_colores(var_id):
    """Para T: selectores de cmap. Para el resto: 5 colores hex."""
    if var_id == "t":
        cmap_options = [{"label": c, "value": c} for c in CMAPS_LIST]
        return html.Div([
            html.Div("Elige la paleta de color (cmap de matplotlib).",
                     style={"color": "#64748B", "fontSize": "0.78rem",
                            "marginBottom": "10px"}),
            html.Label("Paleta para Temperatura (años):",
                       className="form-label"),
            dcc.Dropdown(id="cmap_temp_t",
                         options=cmap_options,
                         value="gist_rainbow_r",
                         clearable=False,
                         style={"marginBottom": "14px"}),
            html.Label("Paleta para Anomalías:", className="form-label"),
            dcc.Dropdown(id="cmap_anom_t",
                         options=cmap_options,
                         value="RdBu_r",
                         clearable=False),
        ])
    return html.Div([
        html.Div("Personaliza los 5 colores principales del gráfico.",
                 style={"color": "#64748B", "fontSize": "0.78rem",
                        "marginBottom": "10px"}),
        *[_slider_color(var_id, i) for i in range(5)],
    ])


def _panel_tema(var_id):
    default = "bw" if var_id == "w" else "minimal"
    return html.Div([
        html.Label("Tema de la gráfica:", className="form-label"),
        dcc.Dropdown(id=f"tema_{var_id}",
                     options=[
                         {"label": "Minimal", "value": "minimal"},
                         {"label": "Blanco y negro", "value": "bw"},
                         {"label": "Clásico", "value": "classic"},
                         {"label": "Claro", "value": "light"},
                         {"label": "Gris (defecto ggplot)", "value": "gray"},
                     ], value=default, clearable=False),
    ])


def _boton_descarga(id_boton):
    return html.Button(
        "⬇", id=id_boton, n_clicks=0, className="btn-dl-header",
        title="Descargar PNG (900 dpi)",
    )


def _card_grafica(titulo, id_graph, id_dl_btn, altura="560px"):
    return html.Div([
        html.Div([
            html.Span(titulo),
            _boton_descarga(id_dl_btn),
        ], className="card-header"),
        html.Div(dcc.Graph(id=id_graph, style={"height": altura}),
                 className="card-body"),
    ], className="card")


def crear_tab_variable(var_id, titulo):
    df = BOYAS_POR_VARIABLE.get(var_id, pd.DataFrame())
    defs = defaults_var[var_id]
    if df is not None and len(df) > 0:
        boya_options = [{"label": r["label"], "value": r["id"]}
                        for _, r in df.iterrows()]
        boya_default = boya_options[0]["value"]
    else:
        boya_options = [{"label": "Sin boyas disponibles", "value": ""}]
        boya_default = ""

    extra_panel = None
    if var_id == "t":
        extra_panel = _accordion_item("Climatología y profundidad", "⚙️", [
            html.Label("Inicio climatología:", className="form-label"),
            dcc.DatePickerSingle(id=f"clim_ini_{var_id}", date="1991-01-01",
                                 display_format="YYYY-MM-DD",
                                 style={"width": "100%",
                                        "marginBottom": "10px"}),
            html.Label("Fin climatología:", className="form-label"),
            dcc.DatePickerSingle(id=f"clim_fin_{var_id}", date="2020-12-31",
                                 display_format="YYYY-MM-DD",
                                 style={"width": "100%",
                                        "marginBottom": "10px"}),
            html.Label("Profundidad máxima (m):", className="form-label"),
            dcc.Input(id=f"prof_max_{var_id}", type="number", value=500,
                      min=50, max=1000, step=50, style={"width": "100%"}),
            html.Div([html.Span("⚠️ "),
                      html.Span("Se requieren al menos 25 años dentro del "
                                "rango. Si 1991 no tiene datos, se usará "
                                "el año más cercano.")],
                     className="aviso-warn"),
        ], abierto=False)

    panel_tema = None
    if var_id in ("sst", "dyn", "iso", "w"):
        panel_tema = _accordion_item("Apariencia", "🎨",
                                     _panel_tema(var_id), abierto=False)

    # ===== Contenido de gráficas =====
    if var_id == "t":
        contenido_graficas = html.Div([
            html.Div(
                id="timer-t",
                children=" ",
                style={
                    "textAlign": "center",
                    "padding": "10px 14px",
                    "borderRadius": "10px",
                    "background": "transparent",
                    "color": "transparent",
                    "fontWeight": "700",
                    "fontSize": "1rem",
                    "transition": "all 0.25s ease",
                    "position": "sticky",
                    "top": "0",
                    "zIndex": "100",
                    "marginBottom": "8px",
                    "display": "none",
                    "boxShadow": "0 2px 8px rgba(7, 89, 133, 0.08)",
                },
            ),
            _card_grafica("📈 Serie Histórica P1", f"hist_p1_{var_id}",
                          f"btn_dl_hist_p1_{var_id}", "450px"),
            _card_grafica("📈 Serie Histórica P2", f"hist_p2_{var_id}",
                          f"btn_dl_hist_p2_{var_id}", "450px"),
            _card_grafica("📊 Anomalías P1", f"anom_p1_{var_id}",
                          f"btn_dl_anom_p1_{var_id}", "450px"),
            _card_grafica("📊 Anomalías P2", f"anom_p2_{var_id}",
                          f"btn_dl_anom_p2_{var_id}", "450px"),
        ])
    elif var_id == "w":
        contenido_graficas = html.Div([
            html.Div(style={"display": "grid",
                            "gridTemplateColumns": "1fr 1fr",
                            "gap": "15px"}, children=[
                _card_grafica("📈 Serie Histórica P1", f"hist_p1_{var_id}",
                              f"btn_dl_hist_p1_{var_id}", "820px"),
                _card_grafica("📈 Serie Histórica P2", f"hist_p2_{var_id}",
                              f"btn_dl_hist_p2_{var_id}", "820px"),
            ]),
            html.Div(style={"display": "grid",
                            "gridTemplateColumns": "1fr 1fr",
                            "gap": "15px"}, children=[
                _card_grafica("📊 Anomalías P1", f"anom_p1_{var_id}",
                              f"btn_dl_anom_p1_{var_id}", "820px"),
                _card_grafica("📊 Anomalías P2", f"anom_p2_{var_id}",
                              f"btn_dl_anom_p2_{var_id}", "820px"),
            ]),
        ])
    else:
        contenido_graficas = html.Div([
            _card_grafica("📈 Serie Histórica", f"hist_{var_id}",
                          f"btn_dl_hist_{var_id}", "560px"),
            _card_grafica("📊 Anomalías", f"anom_{var_id}",
                          f"btn_dl_anom_{var_id}", "560px"),
        ])

    sidebar_children = [
        _titulo_sidebar(titulo, f"{len(df)} boyas disponibles"),
        _accordion_item("Boya", "📍", [
            html.Label("Seleccionar boya:", className="form-label"),
            dcc.Dropdown(id=f"boya_{var_id}", options=boya_options,
                         value=boya_default, clearable=False),
        ]),
        _accordion_item("Períodos", "📅", [
            html.Div(style={"display": "flex", "gap": "10px"}, children=[
                html.Div([
                    html.Label("Año período 1:", className="form-label"),
                    dcc.Input(id=f"anio_p1_{var_id}", type="number",
                              value=1997, min=1979, max=2030, step=1,
                              style={"width": "100%"}),
                ], style={"flex": "1"}),
                html.Div([
                    html.Label("Año período 2:", className="form-label"),
                    dcc.Input(id=f"anio_p2_{var_id}", type="number",
                              value=anio_actual - 1, min=1979, max=2030,
                              step=1, style={"width": "100%"}),
                ], style={"flex": "1"}),
            ]),
            html.Div([html.Span("ℹ️ "),
                      html.Span(["Cada período gráfica ",
                                 html.B("24 meses"),
                                 ". Los años se sincronizan "
                                 "automáticamente."])],
                     className="aviso-info"),
        ]),
    ]
    if extra_panel is not None:
        sidebar_children.append(extra_panel)
    sidebar_children.append(_accordion_item("Colores", "🎨",
                                             _panel_colores(var_id),
                                             abierto=False))
    if panel_tema is not None:
        sidebar_children.append(panel_tema)
    sidebar_children.append(_accordion_item("Títulos y etiquetas", "🔤", [
        html.Label("Título histórico (opcional):", className="form-label"),
        dcc.Textarea(id=f"titulo_hist_{var_id}", value=defs["titulo_hist"],
                     style={"width": "100%", "minHeight": "60px"}),
        html.Label("Título anomalías (opcional):", className="form-label",
                   style={"marginTop": "8px"}),
        dcc.Textarea(id=f"titulo_anom_{var_id}", value=defs["titulo_anom"],
                     style={"width": "100%", "minHeight": "60px"}),
        html.Label("Etiqueta eje Y (histórico):", className="form-label",
                   style={"marginTop": "8px"}),
        dcc.Input(id=f"ylab_hist_{var_id}", value=defs["ylab_hist"],
                  style={"width": "100%"}),
        html.Label("Etiqueta eje Y (anomalías):", className="form-label",
                   style={"marginTop": "8px"}),
        dcc.Input(id=f"ylab_anom_{var_id}", value=defs["ylab_anom"],
                  style={"width": "100%"}),
    ], abierto=False))

    sidebar = html.Div(sidebar_children, className="sidebar")
    content = html.Div(contenido_graficas, className="content-area")
    return html.Div([sidebar, content], className="main-container",
                    id=f"tab-{var_id}", style={"display": "none"})


# ============================================================
# APP + LAYOUT
# ============================================================
_ASSETS_DIR = os.path.join(_CUR_DIR, "assets")
app = Dash(
    __name__,
    server=False,
    routes_pathname_prefix="/subsurf-dash/",
    requests_pathname_prefix="/subsurf-dash/",
    assets_folder=_ASSETS_DIR,
    suppress_callback_exceptions=True,
    title="Monitoreo ENSO — Boyas TAO",
)

app.layout = html.Div([
    dcc.Store(id="boya-activa", data=None),
    dcc.Interval(id="timer-t-iv", interval=200, n_intervals=0, disabled=True),

    *[dcc.Store(id=f"fig_{nombre}_{vid}")
      for vid in ["sst", "dyn", "iso", "w"]
      for nombre in ["hist", "anom"]],
    *[dcc.Store(id=f"fig_{nombre}_{pid}_w")
      for pid in ["p1", "p2"] for nombre in ["hist", "anom"]],
    *[dcc.Store(id=f"fig_{nombre}_{pid}_t")
      for pid in ["p1", "p2"] for nombre in ["hist", "anom"]],

    *[dcc.Download(id=f"dl_{nombre}_{vid}")
      for vid in ["sst", "dyn", "iso", "w"]
      for nombre in ["hist", "anom"]],
    *[dcc.Download(id=f"dl_{nombre}_{pid}_w")
      for pid in ["p1", "p2"] for nombre in ["hist", "anom"]],
    *[dcc.Download(id=f"dl_{nombre}_{pid}_t")
      for pid in ["p1", "p2"] for nombre in ["hist", "anom"]],

    html.Div([
        html.Div([html.Span("🌊", style={"fontSize": "1.3rem"}),
                  html.Span("Monitoreo ENSO")], className="navbar-brand"),
        html.Div([
            html.Button("Ubicación", id="nav-ubicacion", n_clicks=0,
                        className="nav-link active"),
            html.Button("Temperatura Superficial", id="nav-sst", n_clicks=0,
                        className="nav-link"),
            html.Button("Altura Dinámica", id="nav-dyn", n_clicks=0,
                        className="nav-link"),
            html.Button("Isoterma de 20°C", id="nav-iso", n_clicks=0,
                        className="nav-link"),
            html.Button("Temperatura Subsuperficial", id="nav-t", n_clicks=0,
                        className="nav-link"),
            html.Button("Vientos", id="nav-w", n_clicks=0,
                        className="nav-link"),
        ], className="nav-tabs"),
        html.Button("🌙", id="btn-dark-mode", n_clicks=0,
                    className="dark-toggle"),
    ], className="navbar-custom"),

    html.Div([
        html.Div([
            html.Div([
                _titulo_sidebar("TAO/TRITON", "Pacífico ecuatorial"),
                _accordion_item("Filtros Geográficos", "📍", [
                    html.Label("Variable:", className="form-label"),
                    dcc.Dropdown(id="var_ubicacion",
                                 options=[{"label": v, "value": k}
                                          for k, v in VAR_LABELS.items()],
                                 value="sst", clearable=False),
                    html.Label("Filtrar por Región:",
                               className="form-label",
                               style={"marginTop": "10px"}),
                    dcc.Dropdown(id="filtro_region",
                                 options=[{"label": "Todas", "value": "Todas"},
                                          {"label": "Niño 1+2",
                                           "value": "Niño 1+2"},
                                          {"label": "Niño 3", "value": "Niño 3"},
                                          {"label": "Niño 4", "value": "Niño 4"},
                                          {"label": "Niño 3.4",
                                           "value": "Niño 3.4"}],
                                 value="Todas", clearable=False),
                    html.Label("Filtrar por Longitud:",
                               className="form-label",
                               style={"marginTop": "10px"}),
                    dcc.Dropdown(id="filtro_meridiano",
                                 options=[{"label": "Todas",
                                           "value": "Todas"}],
                                 value="Todas", clearable=False),
                ]),
            ], className="sidebar"),
            html.Div([
                html.Div([
                    html.Div([html.Span("🗺️ Distribución Espacial de la Red "
                                        "TAO/TRITON")],
                             className="card-header"),
                    html.Div(dcc.Graph(id="mapa-boyas",
                                       style={"height": "calc(100vh - 170px)"},
                                       config={"scrollZoom": True,
                                               "displayModeBar": False}),
                             className="card-body"),
                ], className="card", style={"marginBottom": "0"}),
            ], className="content-area"),
        ], id="tab-ubicacion", className="main-container"),

        crear_tab_variable("sst", "Temperatura Superficial"),
        crear_tab_variable("dyn", "Altura Dinámica"),
        crear_tab_variable("iso", "Isoterma de 20°C"),
        crear_tab_variable("t",   "Temperatura Subsuperficial"),
        crear_tab_variable("w",   "Vientos"),
    ], id="contenedor-tabs"),
], style={"minHeight": "100vh", "width": "100%"})


# ============================================================
# CALLBACKS DE NAVEGACIÓN
# ============================================================
@app.callback(
    [Output("tab-ubicacion", "style"),
     Output("tab-sst", "style"), Output("tab-dyn", "style"),
     Output("tab-iso", "style"), Output("tab-t", "style"),
     Output("tab-w", "style"),
     Output("nav-ubicacion", "className"),
     Output("nav-sst", "className"), Output("nav-dyn", "className"),
     Output("nav-iso", "className"), Output("nav-t", "className"),
     Output("nav-w", "className"),
     Output("timer-t-iv", "disabled")],
    [Input("nav-ubicacion", "n_clicks"), Input("nav-sst", "n_clicks"),
     Input("nav-dyn", "n_clicks"), Input("nav-iso", "n_clicks"),
     Input("nav-t", "n_clicks"), Input("nav-w", "n_clicks")],
    prevent_initial_call=True,
)
def cambiar_tab(*_):
    ctx = callback_context
    if not ctx.triggered:
        return [no_update] * 13
    trig = ctx.triggered[0]["prop_id"].split(".")[0]
    tabs = {"nav-ubicacion": "ubicacion", "nav-sst": "sst",
            "nav-dyn": "dyn", "nav-iso": "iso", "nav-t": "t", "nav-w": "w"}
    activo = tabs.get(trig, "ubicacion")
    ids_orden = ["ubicacion", "sst", "dyn", "iso", "t", "w"]
    styles = [{"display": "flex"} if t == activo else {"display": "none"}
              for t in ids_orden]
    classnames = ["nav-link active" if t == activo else "nav-link"
                  for t in ids_orden]
    timer_disabled = (activo != "t")
    return styles + classnames + [timer_disabled]


app.clientside_callback(
    """
    function(n) {
        if (n % 2 === 1) {
            document.body.classList.add('dark-mode');
            return "☀️";
        } else {
            document.body.classList.remove('dark-mode');
            return "🌙";
        }
    }
    """,
    Output("btn-dark-mode", "children"),
    Input("btn-dark-mode", "n_clicks"),
)


# ============================================================
# CONTADOR EN VIVO PARA TSSM
# ============================================================
app.clientside_callback(
    """
    function(n) {
        try {
            var timer = document.getElementById('timer-t');
            if (!timer) return " ";

            var ids = ['hist_p1_t', 'hist_p2_t', 'anom_p1_t', 'anom_p2_t'];
            var isLoading = false;

            for (var i = 0; i < ids.length; i++) {
                var el = document.getElementById(ids[i]);
                if (!el) continue;
                var node = el;
                var lim = 10;
                while (node && lim-- > 0) {
                    if (node.getAttribute &&
                        node.getAttribute('data-dash-is-loading') === 'true') {
                        isLoading = true;
                        break;
                    }
                    node = node.parentElement;
                }
                if (isLoading) break;
            }

            if (isLoading) {
                if (!window._timerT) window._timerT = Date.now();
                var sec = ((Date.now() - window._timerT) / 1000).toFixed(1);
                timer.style.display = "block";
                timer.style.background = "linear-gradient(90deg, #E0F2FE, #BAE6FD)";
                timer.style.border = "1px solid #7DD3FC";
                timer.style.color = "#075985";
                return "⏳ Procesando… " + sec + " s";
            } else {
                window._timerT = null;
                timer.style.display = "none";
                timer.style.background = "transparent";
                timer.style.border = "none";
                return " ";
            }
        } catch(e) {
            return " ";
        }
    }
    """,
    Output("timer-t", "children"),
    Input("timer-t-iv", "n_intervals"),
)


# ============================================================
# PREVIEW DE COLORES (solo para sst/dyn/iso/w; t ya no usa colores hex)
# ============================================================
def _registrar_preview_color(var_id):
    inputs = [Input(f"col{i}_{var_id}", "value") for i in range(1, 6)]
    outputs = [Output(f"prev{i}_{var_id}", "style") for i in range(1, 6)]

    @app.callback(outputs, inputs, prevent_initial_call=False)
    def _update(*colors):
        result = []
        for c in colors:
            c = c or "#FFFFFF"
            if not c.startswith("#") and re.match(r"^[0-9A-Fa-f]{3,6}$", c):
                c = "#" + c
            result.append({"width": "32px", "height": "32px",
                           "borderRadius": "6px",
                           "border": "1px solid #B8D4E3",
                           "backgroundColor": c,
                           "flexShrink": "0"})
        return result


for _v in ["sst", "dyn", "iso", "w"]:
    _registrar_preview_color(_v)


# ============================================================
# MAPA
# ============================================================
def construir_mapa(boyas_df, boya_activa=None):
    fig = go.Figure()
    regiones = [
        ("Niño 1+2", -90, -10, -80, 0, "#DC2626"),
        ("Niño 3", -150, -5, -90, 5, "#F97316"),
        ("Niño 4", -200, -5, -150, 5, "#16A34A"),
        ("Niño 3.4", -170, -5, -120, 5, "#9333EA"),
    ]
    for nombre, lon1, lat1, lon2, lat2, color in regiones:
        fig.add_trace(go.Scattergeo(
            lon=[lon1, lon2, lon2, lon1, lon1],
            lat=[lat1, lat1, lat2, lat2, lat1],
            mode="lines", name=nombre,
            line=dict(color=color, width=2), hoverinfo="name",
        ))
    fig.add_trace(go.Scattergeo(
        lon=[-210, -60], lat=[0, 0], mode="lines",
        name="Línea Ecuatorial (0°)",
        line=dict(color="#0F172A", width=1.3, dash="dash"),
    ))
    if boyas_df is not None and len(boyas_df) > 0:
        for _, b in boyas_df.iterrows():
            fig.add_trace(go.Scattergeo(
                lon=[b["lng"]], lat=[b["lat"]], mode="markers",
                marker=dict(size=10, color=b["color"],
                            line=dict(color="white", width=2)),
                text=b["label"],
                customdata=[b["id"]],
                hovertemplate=(f"<b>{b['label']}</b><br>"
                               f"Tipo: {b['tipo']}<br>"
                               f"Región: {b['region']}<br>"
                               f"Lat: {b['lat']}°<br>"
                               f"Lon: {abs(b['lng_original'])}°"
                               f"{'E' if b['lng_original']>=0 else 'W'}"
                               "<extra></extra>"),
                showlegend=False,
            ))
    if boya_activa is not None and isinstance(boya_activa, str):
        sub = None
        for v in BOYAS_POR_VARIABLE.values():
            if v is None or len(v) == 0:
                continue
            s = v[v["id"] == boya_activa]
            if len(s) > 0:
                sub = s.iloc[0]
                break
        if sub is not None:
            fig.add_trace(go.Scattergeo(
                lon=[sub["lng"]], lat=[sub["lat"]],
                mode="markers", name="Seleccionada",
                marker=dict(size=16, color="#FFD700",
                            line=dict(color="black", width=2)),
                showlegend=False, hoverinfo="skip",
            ))
    fig.update_geos(
        projection_type="natural earth",
        showland=True, landcolor="#F5F1E3",
        showocean=True, oceancolor="#B8D4E8",
        showcountries=True, countrycolor="#94A3B8",
        lataxis_range=[-25, 25], lonaxis_range=[-210, -60],
        showcoastlines=True, coastlinecolor="#475569",
        showframe=False, bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="white",
        showlegend=True,
        legend=dict(orientation="v", x=0.01, y=0.99,
                    bgcolor="rgba(255,255,255,0.9)",
                    bordercolor="#C7DDEA", borderwidth=1,
                    font=dict(size=11)),
        height=650,
    )
    return fig


@app.callback(
    Output("mapa-boyas", "figure"),
    [Input("var_ubicacion", "value"),
     Input("filtro_region", "value"),
     Input("filtro_meridiano", "value"),
     Input("boya-activa", "data")],
)
def actualizar_mapa(var_id, region, meridiano, boya_activa):
    var_id = var_id or "sst"
    df = BOYAS_POR_VARIABLE.get(var_id, pd.DataFrame()).copy()
    if df is None or len(df) == 0:
        return construir_mapa(pd.DataFrame())
    if region and region != "Todas":
        df = df[df["region"] == region]
    if meridiano and meridiano != "Todas":
        try: df = df[df["lng"] == float(meridiano)]
        except Exception: pass
    b = None
    if boya_activa:
        if isinstance(boya_activa, list):
            b = boya_activa[0] if boya_activa else None
        else:
            b = boya_activa
    return construir_mapa(df, b)


@app.callback(
    Output("filtro_meridiano", "options"),
    Output("filtro_meridiano", "value"),
    [Input("var_ubicacion", "value"),
     Input("filtro_region", "value")],
)
def actualizar_meridianos(var_id, region):
    var_id = var_id or "sst"
    df = BOYAS_POR_VARIABLE.get(var_id, pd.DataFrame())
    if df is None or len(df) == 0:
        return [{"label": "Sin boyas", "value": "Todas"}], "Todas"
    sub = df if region == "Todas" else df[df["region"] == region]
    lons = sorted(sub["lng"].unique(), reverse=True)
    if not lons:
        return [{"label": "Sin longitudes", "value": "Todas"}], "Todas"
    opts = [{"label": "Todas", "value": "Todas"}]
    for lon in lons:
        lon_real = lon + 360 if lon < -180 else lon
        etiqueta = f"{abs(lon_real)}°{'E' if lon_real>=0 else 'W'}"
        opts.append({"label": etiqueta, "value": str(lon)})
    return opts, "Todas"


@app.callback(
    Output("boya-activa", "data"),
    Input("mapa-boyas", "clickData"),
    prevent_initial_call=True,
)
def registrar_click_boya(clickData):
    if not clickData or not clickData.get("points"):
        return no_update
    pts = clickData["points"]
    if not pts:
        return no_update
    p = pts[0]
    cd = p.get("customdata")
    if cd is None:
        return no_update
    if isinstance(cd, list):
        if not cd:
            return no_update
        return cd[0]
    return cd


# ============================================================
# HELPERS DE GRÁFICAS
# ============================================================
def _computa_fig_var(vid, args):
    (boya_id, y1, y2, c1, c2, c3, c4, c5,
     th, ta, ylh, yla, *resto) = args
    tema = resto[0] if resto else "minimal"
    if not boya_id:
        return None
    df_var = BOYAS_POR_VARIABLE.get(vid, pd.DataFrame())
    rows = df_var[df_var["id"] == boya_id]
    if len(rows) == 0:
        return None
    boya = rows.iloc[0]
    ncfile = obtener_nc_boya(vid, boya)
    if ncfile is None:
        return None
    var_nc = MAPA_VARIABLES_NC.get(vid)
    if var_nc is None:
        vars_all = list(ncfile.variables.keys())
        vars_t = [v for v in vars_all if re.match(r"^T_\d+", v)]
        if not vars_t:
            return None
        var_nc = vars_t[0]
    df_merge = procesar_nc(ncfile, var_nc)
    if df_merge is None or len(df_merge) == 0:
        return None
    anios_disp = df_merge["anio"].unique()
    anios_clim = [a for a in anios_disp if 1991 <= a <= 2020]
    if len(anios_clim) < 25:
        return None
    try:
        y1 = int(y1) if y1 else 1997
        y2 = int(y2) if y2 else anio_actual - 1
    except Exception:
        y1, y2 = 1997, anio_actual - 1
    colores = [c1, c2, c3, c4, c5]
    if vid == "sst":
        return graficar_sst(df_merge, (y1, y1+1), (y2, y2+1),
                            th, ta, ylh, yla, colores, tema)
    if vid == "dyn":
        return graficar_dyn(df_merge, (y1, y1+1), (y2, y2+1),
                            th, ta, ylh, yla, colores, tema)
    if vid == "iso":
        return graficar_iso(df_merge, (y1, y1+1), (y2, y2+1),
                            th, ta, ylh, yla, colores, tema)
    return None


def _computa_fig_w(args):
    (boya_id, y1, y2, c1, c2, c3, c4, c5,
     th, ta, ylh, yla, *resto) = args
    tema = resto[0] if resto else "bw"
    if not boya_id:
        return None
    df_var = BOYAS_POR_VARIABLE.get("w", pd.DataFrame())
    rows = df_var[df_var["id"] == boya_id]
    if len(rows) == 0:
        return None
    boya = rows.iloc[0]
    ncfile = obtener_nc_boya("w", boya)
    if ncfile is None:
        return None
    var_nc = MAPA_VARIABLES_NC.get("w")
    if var_nc is None:
        return None
    df_merge = procesar_nc(ncfile, var_nc)
    if df_merge is None or len(df_merge) == 0:
        return None
    anios_disp = df_merge["anio"].unique()
    anios_clim = [a for a in anios_disp if 1991 <= a <= 2020]
    if len(anios_clim) < 25:
        return None
    try:
        y1 = int(y1) if y1 else 1997
        y2 = int(y2) if y2 else anio_actual - 1
    except Exception:
        y1, y2 = 1997, anio_actual - 1
    colores = [c1, c2, c3, c4, c5]
    return graficar_w(df_merge, (y1, y1+1), (y2, y2+1),
                      th, ta, ylh, yla, colores, tema)


# ============================================================
# CALLBACKS DE GRÁFICAS (SST, DYN, ISO, W)
# ============================================================
def _registrar_cb(var_id):
    id_boya = f"boya_{var_id}"
    id_p1 = f"anio_p1_{var_id}"
    id_p2 = f"anio_p2_{var_id}"

    if var_id == "w":
        outputs = [Output(f"hist_p1_{var_id}", "figure"),
                   Output(f"hist_p2_{var_id}", "figure"),
                   Output(f"anom_p1_{var_id}", "figure"),
                   Output(f"anom_p2_{var_id}", "figure"),
                   Output(f"fig_hist_p1_{var_id}", "data"),
                   Output(f"fig_hist_p2_{var_id}", "data"),
                   Output(f"fig_anom_p1_{var_id}", "data"),
                   Output(f"fig_anom_p2_{var_id}", "data")]
    else:
        outputs = [Output(f"hist_{var_id}", "figure"),
                   Output(f"anom_{var_id}", "figure"),
                   Output(f"fig_hist_{var_id}", "data"),
                   Output(f"fig_anom_{var_id}", "data")]

    inputs = [Input(id_boya, "value"),
              Input(id_p1, "value"), Input(id_p2, "value")]
    for i in range(1, 6):
        inputs.append(Input(f"col{i}_{var_id}", "value"))
    inputs += [Input(f"titulo_hist_{var_id}", "value"),
               Input(f"titulo_anom_{var_id}", "value"),
               Input(f"ylab_hist_{var_id}", "value"),
               Input(f"ylab_anom_{var_id}", "value")]
    if var_id in ("sst", "dyn", "iso", "w"):
        inputs.append(Input(f"tema_{var_id}", "value"))

    def make_render(vid):
        def render(*args):
            boya_id = args[0]
            if not boya_id:
                return (figura_aviso("Datos insuficientes", "Seleccione una boya y verifique los datos"),) * (8 if vid == "w" else 4)

            df_var = BOYAS_POR_VARIABLE.get(vid, pd.DataFrame())
            rows = df_var[df_var["id"] == boya_id]
            if len(rows) == 0:
                return (figura_aviso("Datos insuficientes", "Seleccione una boya y verifique los datos"),) * (8 if vid == "w" else 4)
            boya = rows.iloc[0]

            ncfile = obtener_nc_boya(vid, boya)
            if ncfile is None:
                fig_err = figura_aviso("Sin datos", f"No se pudo descargar/abrir el NetCDF ({_nombre_archivo_nc(vid, boya)})")
                return (fig_err,) * (8 if vid == "w" else 4)

            var_nc = MAPA_VARIABLES_NC.get(vid)
            if var_nc is None:
                vars_all = list(ncfile.variables.keys())
                vars_t = [v for v in vars_all if re.match(r"^T_\d+", v)]
                if not vars_t:
                    fig_err = figura_aviso("Sin datos", "No hay variables T_*")
                    return (fig_err,) * (8 if vid == "w" else 4)
                var_nc = vars_t[0]

            df_merge = procesar_nc(ncfile, var_nc)
            if df_merge is None or len(df_merge) == 0:
                fig_err = figura_aviso("Sin datos", "No se pudieron procesar los datos")
                return (fig_err,) * (8 if vid == "w" else 4)

            anios_disp = df_merge["anio"].unique()
            anios_clim = [a for a in anios_disp if 1991 <= a <= 2020]
            if len(anios_clim) < 25:
                fig_err = figura_aviso(
                    "Datos insuficientes",
                    f"Se requieren al menos 25 años para la climatología.<br>"
                    f"Años disponibles en [1991-2020]: {len(anios_clim)}")
                return (fig_err,) * (8 if vid == "w" else 4)

            if vid == "w":
                r = _computa_fig_w(args)
                if r is None:
                    fig_err = figura_aviso("Datos insuficientes", "Seleccione una boya y verifique los datos")
                    return (fig_err, fig_err, fig_err, fig_err, None, None, None, None)
                return (r["hist_p1"], r["hist_p2"], r["anom_p1"], r["anom_p2"],
                        r["hist_p1"], r["hist_p2"], r["anom_p1"], r["anom_p2"])
            r = _computa_fig_var(vid, args)
            if r is None:
                fig_err = figura_aviso("Datos insuficientes", "Seleccione una boya y verifique los datos")
                return fig_err, fig_err, None, None
            return r["hist"], r["anom"], r["hist"], r["anom"]
        return render

    app.callback(outputs, inputs, prevent_initial_call=False)(
        make_render(var_id))


for _v in ["sst", "dyn", "iso", "w"]:
    _registrar_cb(_v)


# ============================================================
# CALLBACK T — usa cmaps en vez de 5 colores
# ============================================================
@app.callback(
    [Output("hist_p1_t", "figure"), Output("hist_p2_t", "figure"),
     Output("anom_p1_t", "figure"), Output("anom_p2_t", "figure"),
     Output("fig_hist_p1_t", "data"), Output("fig_hist_p2_t", "data"),
     Output("fig_anom_p1_t", "data"), Output("fig_anom_p2_t", "data")],
    [Input("boya_t", "value"),
     Input("anio_p1_t", "value"), Input("anio_p2_t", "value"),
     Input("cmap_temp_t", "value"), Input("cmap_anom_t", "value"),
     Input("titulo_hist_t", "value"), Input("titulo_anom_t", "value"),
     Input("ylab_hist_t", "value"), Input("ylab_anom_t", "value"),
     Input("clim_ini_t", "date"), Input("clim_fin_t", "date"),
     Input("prof_max_t", "value")],
    prevent_initial_call=False,
)
def render_t(boya_id, y1, y2, cmap_temp, cmap_anom,
             th, ta, ylh, yla, clim_ini, clim_fin, prof_max):
    fig_aviso = figura_aviso(
        "Datos insuficientes",
        "Seleccione una boya y verifique los datos")
    if not boya_id:
        return (fig_aviso, fig_aviso, fig_aviso, fig_aviso,
                None, None, None, None)
    df_var = BOYAS_POR_VARIABLE.get("t", pd.DataFrame())
    rows = df_var[df_var["id"] == boya_id]
    if len(rows) == 0:
        return (fig_aviso, fig_aviso, fig_aviso, fig_aviso,
                None, None, None, None)
    boya = rows.iloc[0]
    ncfile = obtener_nc_boya("t", boya)
    if ncfile is None:
        fig_err = figura_aviso(
            "Sin datos",
            f"No se pudo abrir el NetCDF ({_nombre_archivo_nc('t', boya)})")
        return (fig_err, fig_err, fig_err, fig_err, None, None, None, None)
    vars_all = list(ncfile.variables.keys())
    vars_t = [v for v in vars_all if re.match(r"^T_\d+", v)]
    if not vars_t:
        fig_err = figura_aviso("Sin datos", "No hay variables T_*")
        return (fig_err, fig_err, fig_err, fig_err, None, None, None, None)
    df_perfil = procesar_nc_perfil(ncfile, vars_t[0])
    if df_perfil is None or len(df_perfil) == 0:
        fig_err = figura_aviso(
            "Sin datos",
            "No se pudo procesar el perfil.<br>"
            "Revise la terminal para más detalles.")
        return (fig_err, fig_err, fig_err, fig_err, None, None, None, None)
    try:
        y1 = int(y1) if y1 else 1997
        y2 = int(y2) if y2 else anio_actual - 1
    except Exception:
        y1, y2 = 1997, anio_actual - 1
    clim_ini = clim_ini or "1991-01-01"
    clim_fin = clim_fin or "2020-12-31"
    prof_max = prof_max or 500
    datos = _datos_t_cached(boya_id, df_perfil,
                            (y1, y1+1), (y2, y2+1),
                            clim_ini, clim_fin, prof_max)
    try:
        r = construir_plots_contorno_t(datos, th, ta, ylh, yla,
                                       cmap_temp=cmap_temp or "gist_rainbow_r",
                                       cmap_anom=cmap_anom or "RdBu_r")
        return (r["hist_p1"], r["hist_p2"], r["anom_p1"], r["anom_p2"],
                r["hist_p1"], r["hist_p2"], r["anom_p1"], r["anom_p2"])
    except Exception as e:
        fig_err = figura_aviso("Error al generar gráfico", str(e))
        return (fig_err, fig_err, fig_err, fig_err, None, None, None, None)


# ============================================================
# CALLBACKS DE DESCARGA PNG
# ============================================================
def _descargar_png(fig_dict, filename):
    if fig_dict is None:
        return no_update
    try:
        fig = go.Figure(fig_dict)
        img = pio.to_image(fig, format="png", width=1400, height=700,
                           scale=2)
        return dcc.send_bytes(img, filename)
    except Exception:
        return no_update


def _registrar_dl(sufijo_id, fig_id, dl_id, nombre, var_suffix):
    @app.callback(
        Output(dl_id, "data"),
        Input(f"btn_dl_{sufijo_id}{var_suffix}", "n_clicks"),
        State(fig_id, "data"),
        prevent_initial_call=True,
    )
    def _dl(n, fig_data):
        if not n:
            return no_update
        return _descargar_png(
            fig_data,
            f"{nombre}_{sufijo_id}{var_suffix.replace('_','')}_"
            f"{datetime.now():%Y%m%d}.png")
    return _dl


for vid in ["sst", "dyn", "iso"]:
    _registrar_dl("hist", f"fig_hist_{vid}", f"dl_hist_{vid}",
                  "hist", f"_{vid}")
    _registrar_dl("anom", f"fig_anom_{vid}", f"dl_anom_{vid}",
                  "anom", f"_{vid}")

for pid in ["p1", "p2"]:
    _registrar_dl(f"hist_{pid}", f"fig_hist_{pid}_w", f"dl_hist_{pid}_w",
                  "hist", "_w")
    _registrar_dl(f"anom_{pid}", f"fig_anom_{pid}_w", f"dl_anom_{pid}_w",
                  "anom", "_w")

for pid in ["p1", "p2"]:
    _registrar_dl(f"hist_{pid}", f"fig_hist_{pid}_t", f"dl_hist_{pid}_t",
                  "hist", "_t")
    _registrar_dl(f"anom_{pid}", f"fig_anom_{pid}_t", f"dl_anom_{pid}_t",
                  "anom", "_t")


def mount_dash(server_instance):
    """Monta la aplicación Dash sobre un servidor Flask existente."""
    app.init_app(server_instance)
    return app


if __name__ == "__main__":
    from flask import redirect
    app.init_app()
    @app.server.route("/")
    def _root_redir():
        return redirect("/subsurf-dash/")
    app.run(debug=True, host="0.0.0.0", port=8050, threaded=True)