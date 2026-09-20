"""
Funciones de graficado ENSO, adaptadas del notebook original del usuario
(noaa_parameters_porras.py, curso ENSO). Misma lógica visual (cajas Niño,
paleta Spectral_r / seismic, extensión Pacífico tropical) — solo se quitó
todo lo específico de Colab (drive.mount, %cd, !pip, !mkdir) y se
parametrizó la ruta de salida para correr en el VPS.

Cada variable vive en su propia carpeta hermana (backend/app/tsm/,
anomalia/, viento/, slp/, hovmoller/, subsuperficie/ — mismo patrón que
GOES19/), para que cada integrante del equipo tenga un espacio propio y
obvio donde trabajar sin pisarse con los demás. Los helpers/constantes
compartidos por todas quedan acá en plotting/common.py. Se re-exporta
todo acá para que el resto del código siga usando `import plotting` /
`plotting.plot_x(...)` sin cambios, sin que le importe dónde vive cada
implementación.
"""

from .common import EXTENT_PACIFICO, NINO_COLORS, NINO_REGIONS_EQ, NINO_BOXES
from tsm.sst import plot_sst
from anomalia.anomalia import plot_sst_anom
from viento.viento import plot_wind_850hpa_vectors
from slp.slp import plot_slp
from hovmoller.hovmoller import plot_hovmoller_nino, plot_hovmoller_nino_lat
from subsuperficie.subsuperficie import plot_equatorial_depth_section, plot_subsurf_composite

__all__ = [
    "EXTENT_PACIFICO", "NINO_COLORS", "NINO_REGIONS_EQ", "NINO_BOXES",
    "plot_sst", "plot_sst_anom", "plot_wind_850hpa_vectors", "plot_slp",
    "plot_hovmoller_nino", "plot_hovmoller_nino_lat",
    "plot_equatorial_depth_section", "plot_subsurf_composite",
]
