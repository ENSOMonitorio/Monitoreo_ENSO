"""
Módulo puente / compatibilidad para code_walker.
Re-exporta la funcionalidad de backend/app/viento/walker.py.
"""

from .walker import (
    cargar_datos,
    calcular_u_divergente,
    calcular_stream_function,
    indice_intensidad_walker,
    plot_walker_cross_section,
    plot_walker_timeseries,
    generar_figuras_walker,
)

__all__ = [
    "cargar_datos",
    "calcular_u_divergente",
    "calcular_stream_function",
    "indice_intensidad_walker",
    "plot_walker_cross_section",
    "plot_walker_timeseries",
    "generar_figuras_walker",
]

