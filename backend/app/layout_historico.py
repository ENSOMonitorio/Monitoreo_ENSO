"""
Pestaña "Contexto histórico": port del panel estático (Artifact) con la
serie ONI 1950-2026 y los grandes eventos ENOS en Perú, para que quede
integrado en el mismo dashboard del VPS en vez de vivir solo en un link aparte.
"""

import plotly.graph_objects as go
from dash import dcc, html

import theme

# Serie ONI DJF representativa por año — misma fuente que el Artifact:
# NOAA CPC (ERSST v5) vía ggweather.com; 2025-2026 son valores provisionales.
ONI_DATA = [
    (1950, -0.82), (1951, 0.53), (1952, 0.40), (1953, 0.76), (1954, -0.81), (1955, -1.11), (1956, -0.25),
    (1957, 1.81), (1958, 0.61), (1959, -0.10), (1960, -0.04), (1961, 0.05), (1962, -0.24), (1963, -0.40),
    (1964, 1.07), (1965, -0.59), (1966, 1.37), (1967, -0.41), (1968, -0.64), (1969, 1.13), (1970, 0.51),
    (1971, -1.36), (1972, -0.71), (1973, 1.84), (1974, -1.84), (1975, -0.54), (1976, -1.56), (1977, 0.71),
    (1978, 0.69), (1979, 0.03), (1980, 0.59), (1981, -0.26), (1982, -0.05), (1983, 2.18), (1984, -0.60),
    (1985, -1.04), (1986, -0.49), (1987, 1.23), (1988, 0.81), (1989, -1.69), (1990, 0.14), (1991, 0.41),
    (1992, 1.71), (1993, 0.09), (1994, 0.06), (1995, 0.96), (1996, -0.90), (1997, -0.50), (1998, 2.24),
    (1999, -1.55), (2000, -1.66), (2001, -0.68), (2002, -0.15), (2003, 0.92), (2004, 0.37), (2005, 0.64),
    (2006, -0.85), (2007, 0.66), (2008, -1.64), (2009, -0.85), (2010, 1.50), (2011, -1.31), (2012, -0.72),
    (2013, -0.29), (2014, -0.28), (2015, 0.69), (2016, 2.63), (2017, -0.19), (2018, -0.77), (2019, 0.89),
    (2020, 0.64), (2021, -0.91), (2022, -0.82), (2023, -0.54), (2024, 1.92), (2025, -0.45), (2026, 1.00),
]

EVENTS = [
    {"yr": "1891", "title": "El Niño histórico", "stat": "Sin registro ONI instrumental",
     "desc": "Citado por el IGP y el MINAM como comparable en intensidad a los eventos de 1982-83 y 1997-98.",
     "src": "IGP · MINAM"},
    {"yr": "1925–26", "title": "El Niño de la era pre-satelital", "stat": "1524 mm de lluvia en Tumbes (1925)",
     "desc": "92 días de lluvias continuas en 1926. Uno de los eventos más intensos documentados antes de la era satelital.",
     "src": "UDEP Hoy"},
    {"yr": "1982–83", "title": "Súper Niño", "stat": "ONI pico ≈ +2.2 °C (DJF 1983)",
     "desc": "El más devastador del siglo XX hasta entonces: casi nadie en Perú lo había vivido ni anticipado.",
     "src": "UDEP Hoy"},
    {"yr": "1997–98", "title": "El Niño extraordinario", "stat": "ONI pico ≈ +2.2–2.4 °C (DJF 1998)",
     "desc": "Lluvias e inundaciones extremas en la costa norte; sigue siendo uno de los ENOS más estudiados globalmente.",
     "src": "NOAA CPC"},
    {"yr": "2015–16", "title": "Súper Niño", "stat": "ONI pico ≈ +2.6 °C (DJF 2016)",
     "desc": "El evento más cálido registrado en el Pacífico ecuatorial hasta ese momento.",
     "src": "NOAA · PMC"},
    {"yr": "dic'16–may'17", "title": "El Niño costero", "stat": "162 muertos · ≈1 millón de afectados",
     "desc": "Evento local (no un ENOS global) que devastó Tumbes, Piura y Lambayeque con huaicos e inundaciones.",
     "src": "Mongabay · Wikipedia"},
    {"yr": "mar 2023", "title": "Ciclón Yaku", "stat": "50 muertos · 13 puentes destruidos",
     "desc": "Ciclón subtropical atípico frente a la costa norte; SENAMHI no observaba algo similar desde 1983/1998.",
     "src": "Infobae · INDECI/COEN"},
    {"yr": "2023–24", "title": "El Niño fuerte", "stat": "ONI pico ≈ +1.9/2.0 °C (DJF 2024)",
     "desc": "Declarado 'fuerte' por NOAA; seguido de un giro rápido hacia una breve La Niña débil en 2025.",
     "src": "NOAA CPC"},
    {"yr": "2026 · en curso", "title": "El Niño — Alerta NOAA", "stat": "Niño 3.4 semanal +1.7 °C (17 jun)",
     "desc": "Declarado el 11 jun 2026. ~63% de probabilidad de alcanzar categoría 'Súper Niño' entre nov'26 y ene'27.",
     "src": "NOAA CPC · IRI"},
]


def _classify(v):
    a = abs(v)
    if v >= 0.5:
        level = 4 if a >= 2.0 else 3 if a >= 1.5 else 2 if a >= 1.0 else 1
        return "El Niño", level
    if v <= -0.5:
        level = 4 if a >= 2.0 else 3 if a >= 1.5 else 2 if a >= 1.0 else 1
        return "La Niña", level
    return "Neutral", 0


_NINO_COLORS = {1: "#f6cbb8", 2: "#ea9271", 3: "#ff6b52", 4: "#ff3b2f"}
_NINA_COLORS = {1: "#cfe0f7", 2: "#8fb8ea", 3: "#5b9bdb", 4: "#3d7dc9"}
_NEUTRAL = "#8a97a3"


def build_oni_figure():
    years = [y for y, _ in ONI_DATA]
    values = [v for _, v in ONI_DATA]
    colors = []
    labels = []
    for v in values:
        phase, level = _classify(v)
        if phase == "El Niño":
            colors.append(_NINO_COLORS[level])
        elif phase == "La Niña":
            colors.append(_NINA_COLORS[level])
        else:
            colors.append(_NEUTRAL)
        labels.append(f"{phase} {'· nivel ' + str(level) if level else ''}".strip())

    fig = go.Figure(go.Bar(
        x=years, y=values, marker_color=colors, marker_line_width=0.5,
        marker_line_color="rgba(0,0,0,0.25)",
        customdata=labels,
        hovertemplate="<b>%{x}</b> · ONI %{y:.2f}<br>%{customdata}<extra></extra>",
    ))
    fig.add_hline(y=0, line_width=1, line_color="rgba(255,255,255,0.25)")
    fig.update_layout(theme.dark_layout(
        yaxis_title="ONI (°C)", xaxis_title=None,
        height=400, margin=dict(t=20, b=30, l=50, r=20),
        bargap=0.15,
    ))
    return fig


def _event_card(ev):
    return html.Div([
        html.Div(ev["yr"], className="event-year"),
        html.Div(ev["title"], className="event-title"),
        html.Div(ev["stat"], className="event-stat"),
        html.P(ev["desc"], className="event-desc"),
        html.Div(ev["src"], className="event-src"),
    ], className="event-card")


def layout():
    return html.Div([
        html.Div([
            html.Div([
                html.Div([
                    html.Div("Contexto histórico ENOS en Perú", className="chart-title"),
                    html.Div("Serie reconstruida a partir de NOAA CPC (ERSST v5) vía ggweather.com; "
                              "2025-2026 son valores provisionales. Para cifras oficiales exactas "
                              "consulte cpc.ncep.noaa.gov.", className="chart-sub"),
                ]),
            ], className="chart-header"),
            dcc.Graph(figure=build_oni_figure(), config={"displayModeBar": False}),
        ], className="chart-card"),
        html.Div([
            html.Div("Grandes eventos ENOS en Perú", className="chart-title mb-3"),
            html.Div([_event_card(ev) for ev in EVENTS], className="event-row"),
        ], className="chart-card"),
    ])
