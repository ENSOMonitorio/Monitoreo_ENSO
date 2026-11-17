"""Paleta y layout compartidos de los gráficos Plotly, alineados con el sistema
visual del frontend (frontend/src/styles.scss, spec de rediseño §5): claro,
tinta azul océano. Plotly no lee variables CSS, así que los hex se repiten
aquí y hay que mantenerlos sincronizados a mano."""

TEXT = "#0E2233"      # --ink
TEXT_2 = "#45576A"    # --ink-2
MUTED = "#5C6E80"     # --muted
GRID = "#E6EAED"      # --line-soft
AXIS = "#9AA7B3"      # línea del cero y umbrales neutros
SURFACE = "#FFFFFF"   # --surface
TRANSPARENT = "rgba(0,0,0,0)"

# Colores de las regiones Niño: los usan las cajas de todos los mapas
# (plotting.common los reexporta) y los gráficos de índices, para que cada
# región se reconozca igual en todas partes. Iguales a --nino* del frontend.
NINO_COLORS = {
    "Niño 4":   "#7b1fa2",
    "Niño 3.4": "#1565c0",
    "Niño 3":   "#2e7d32",
    "Niño 1+2": "#c62828",
}

FONT = dict(family="Inter, system-ui, sans-serif", color=TEXT)


def chart_layout(**overrides):
    layout = dict(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        font=FONT,
        title_font=dict(family="Space Grotesk, Inter, sans-serif", color=TEXT, size=15),
        legend=dict(font=dict(color=TEXT_2)),
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=MUTED, linecolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, color=MUTED, linecolor=GRID),
        hoverlabel=dict(bgcolor=TEXT, font=dict(color=SURFACE, family="Inter, sans-serif"),
                        bordercolor=TEXT),
    )
    layout.update(overrides)
    return layout
