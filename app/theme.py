"""Paleta y layout compartido para los gráficos Plotly, alineado con el
sistema de diseño verde-bosque-oscuro de assets/style.css (misma identidad
visual que los otros dashboards del VPS)."""

BG = "#0d2a1e"
PANEL = "rgba(0,0,0,0)"
GRID = "rgba(255,255,255,0.08)"
TEXT = "#e2f0e8"
MUTED = "#a0bfaa"
ACCENT_2 = "#5fcf8d"

FONT = dict(family="Inter, system-ui, sans-serif", color=TEXT)


def dark_layout(**overrides):
    layout = dict(
        paper_bgcolor=PANEL,
        plot_bgcolor=PANEL,
        font=FONT,
        title_font=dict(family="Space Grotesk, Inter, sans-serif", color=TEXT, size=15),
        legend=dict(font=dict(color=MUTED)),
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=MUTED, linecolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=MUTED, linecolor=GRID),
        hoverlabel=dict(bgcolor="#0b1f16", font=dict(color=TEXT), bordercolor=ACCENT_2),
    )
    layout.update(overrides)
    return layout
