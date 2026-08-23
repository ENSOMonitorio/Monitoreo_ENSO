"""
Funciones de graficado ENSO, adaptadas del notebook original del usuario
(noaa_parameters_porras.py, curso ENSO). Misma lógica visual (cajas Niño,
paleta Spectral_r / seismic, extensión Pacífico tropical) — solo se quitó
todo lo específico de Colab (drive.mount, %cd, !pip, !mkdir) y se
parametrizó la ruta de salida para correr en el VPS.

Un módulo por tipo de gráfico (mismo orden que las pestañas del dashboard),
con las constantes y helpers compartidos en `common.py`. Se re-exporta todo
acá para que el resto del código siga usando `import plotting` /
`plotting.plot_x(...)` sin cambios.
"""

from .common import EXTENT_PACIFICO, NINO_COLORS, NINO_REGIONS_EQ, NINO_BOXES
from .sst import plot_sst
from .anomalia import plot_sst_anom
from .viento import plot_wind_850hpa_vectors
from .slp import plot_slp
from .hovmoller import plot_hovmoller_nino, plot_hovmoller_nino_lat
from .subsuperficie import plot_equatorial_depth_section, plot_subsurf_composite

__all__ = [
    "EXTENT_PACIFICO", "NINO_COLORS", "NINO_REGIONS_EQ", "NINO_BOXES",
    "plot_sst", "plot_sst_anom", "plot_wind_850hpa_vectors", "plot_slp",
    "plot_hovmoller_nino", "plot_hovmoller_nino_lat",
    "plot_equatorial_depth_section", "plot_subsurf_composite",
]
