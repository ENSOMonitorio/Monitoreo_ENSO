# ============================================================
# ESTILO.PY — Paleta, tema y CSS
# ============================================================

colores_pasteles = [
    "#FDE68A", "#BBF7D0", "#BFDBFE", "#E9D5FF", "#FECACA",
    "#D9F99D", "#A7F3D0", "#BAE6FD", "#DDD6FE", "#FBCFE8",
    "#FEF08A", "#86EFAC", "#93C5FD", "#C4B5FD", "#FCA5A5",
    "#D4D4D8", "#FDE047", "#6EE7B7", "#7DD3FC", "#A78BFA",
]


def etiquetas_color(var_id):
    return {
        "sst": ["Prom. histórico", "Línea serie P1", "Línea serie P2",
                "Línea cero", "Separador año"],
        "dyn": ["Línea serie P1", "Línea serie P2", "Prom. histórico",
                "Línea cero", "Separador año"],
        "iso": ["Línea serie P1", "Línea serie P2", "Prom. histórico",
                "Línea cero", "Separador año"],
        "w":   ["Barras del año", "Línea prom. histórico",
                "Anomalía positiva", "Anomalía negativa", "Separador año"],
        "t":   ["Contorno sólido Temp.", "Contorno discontinuo Temp.",
                "Contorno sólido Anom.", "Contorno discontinuo Anom.",
                "Etiqueta de contorno"],
    }.get(var_id, ["Color 1", "Color 2", "Color 3", "Color 4", "Color 5"])


def colores_default(var_id):
    """Devuelve SIEMPRE hex #RRGGBB."""
    return {
        "sst": ["#0000CD", "#D32F2F", "#000000", "#FF0000", "#FF0000"],
        "dyn": ["#D32F2F", "#000000", "#6495ED", "#FF0000", "#FF0000"],
        "iso": ["#D32F2F", "#000000", "#B0B0B0", "#FF0000", "#FF0000"],
        "w":   ["#D32F2F", "#0000FF", "#D32F2F", "#4B92DB", "#FF0000"],
        "t":   ["#000000", "#666666", "#000000", "#666666", "#4D4D4D"],
    }.get(var_id, ["#D32F2F", "#000000", "#0000FF", "#00FF00", "#FF0000"])


def obtener_tema(nombre):
    return {
        "minimal": "plotly_white",
        "bw":      "simple_white",
        "classic": "simple_white",
        "light":   "plotly_white",
        "gray":    "plotly",
    }.get(nombre, "plotly_white")


# El CSS real vive en assets/estilo.css (Dash lo carga automáticamente)
css_monitoreo = ""