"""GOES-19 Band 13 utilities.

Este modulo concentra la logica que estaba dispersa en el notebook
`AUTOMATIZACION_GOES19.ipynb` para poder ejecutarla de forma reproducible
desde scripts y pipeline.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import cm
from netCDF4 import Dataset
from PIL import Image

try:
	from .utilities_2 import download_CMI, loadCPT, reproject
except ImportError:
	from utilities_2 import download_CMI, loadCPT, reproject

from plotting.common import _autocrop_whitespace



# lon_min, lat_min, lon_max, lat_max. Ampliado al máximo Pacífico que
# GOES-19 realmente alcanza a ver (geoestacionario sobre América, ~75°W —
# no puede ver el Pacífico occidental como el resto de los mapas del
# dashboard, que sí usan datos satelitales polares/reanálisis). Latitud
# alineada a EXTENT_PACIFICO (app/plotting/common.py) para que las cajas
# Niño 1+2 / 3 / parte de 3.4 queden comparables con el resto del tablero.
DEFAULT_EXTENT = [-165.0, -21.0, -25.0, 21.0]


@dataclass
class Goes19Config:
	band: int = 13
	n_images: int = 5
	max_hours_back: int = 6
	gif_delay_ms: int = 1000
	extent: tuple[float, float, float, float] = tuple(DEFAULT_EXTENT)
	cpt_path: Optional[Path] = None
	samples_dir: Optional[Path] = None
	output_dir: Optional[Path] = None
	figures_dir: Optional[Path] = None


def _project_root() -> Path:
	return Path(__file__).resolve().parents[2]


def _default_data_dirs() -> tuple[Path, Path, Path]:
	today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
	root = _project_root()
	data_root = root / "data"
	samples_dir = data_root / "goes19" / "Samples" / today
	output_dir = data_root / "goes19" / "Output" / today
	figures_dir = data_root / "figures"
	return samples_dir, output_dir, figures_dir


def _is_valid_download(result) -> bool:
	if result is None:
		return False
	if isinstance(result, int):
		return result >= 0
	if isinstance(result, str):
		try:
			return int(result) >= 0
		except ValueError:
			return result.strip() != ""
	return False


def collect_latest_images(band: int, dest: Path, n: int = 5, max_hours_back: int = 6) -> list[str]:
	now = datetime.now(timezone.utc)
	found: list[str] = []
	tried: set[str] = set()

	for minutes_back in range(0, max_hours_back * 60 + 1, 10):
		if len(found) == n:
			break

		candidate = now - timedelta(minutes=minutes_back)
		minute_rounded = (candidate.minute // 10) * 10
		yyyymmddhhmn = candidate.strftime("%Y%m%d%H") + f"{minute_rounded:02d}"

		if yyyymmddhhmn in tried:
			continue
		tried.add(yyyymmddhhmn)

		print(f"  [{len(found)+1}/{n}] Probando {yyyymmddhhmn} UTC ...", end=" ", flush=True)
		result = download_CMI(yyyymmddhhmn, band, str(dest))
		if _is_valid_download(result):
			print(f"ok ({result})")
			found.append(str(result))
		else:
			print("sin archivo")

	if not found:
		raise RuntimeError(f"No se encontro ninguna imagen GOES en las ultimas {max_hours_back} horas")
	if len(found) < n:
		print(f"Aviso: solo se encontraron {len(found)} imagenes (se solicitaron {n})")

	return list(reversed(found))


def process_nc(file_name: str, samples_dir: Path, output_dir: Path, extent: tuple[float, float, float, float]):
	from osgeo import gdal

	gdal.UseExceptions()

	var = "CMI"
	nc_path = samples_dir / f"{file_name}.nc"
	img = gdal.Open(f"NETCDF:{nc_path}:{var}")
	if img is None:
		raise FileNotFoundError(f"GDAL no pudo abrir: {nc_path}")

	metadata = img.GetMetadata()
	scale = float(metadata[var + "#scale_factor"])
	offset = float(metadata[var + "#add_offset"])
	undef = float(metadata[var + "#_FillValue"])
	dtime = metadata["NC_GLOBAL#time_coverage_start"]

	ds_cmi = img.ReadAsArray(0, 0, img.RasterXSize, img.RasterYSize).astype(float)
	ds_cmi = (ds_cmi * scale + offset) - 273.15

	reproj_nc = output_dir / f"IR_{file_name}.nc"
	reproject(str(reproj_nc), img, ds_cmi, list(extent), undef)

	nc_repr = Dataset(str(reproj_nc))
	data = nc_repr.variables["Band1"][:]
	dt = datetime.strptime(dtime, "%Y-%m-%dT%H:%M:%S.%fZ")
	return data, dt


def make_frame(
	data,
	dt: datetime,
	frame_idx: int,
	cmap,
	output_dir: Path,
	extent: tuple[float, float, float, float],
	band: int = 13,
) -> Path:
	fig = plt.figure(figsize=(12, 12), dpi=120)
	ax = plt.axes(projection=ccrs.PlateCarree())
	fig.subplots_adjust(left=0.06, right=0.85, top=0.92, bottom=0.06)

	img_extent = [extent[0], extent[2], extent[1], extent[3]]
	ax.set_extent(img_extent, ccrs.PlateCarree())

	img1 = ax.imshow(
		data,
		origin="upper",
		vmin=-103.0,
		vmax=84.0,
		extent=img_extent,
		cmap=cmap,
		alpha=1.0,
	)
	ax.coastlines(resolution="10m", color="white", linewidth=0.8)
	ax.add_feature(cfeature.BORDERS, edgecolor="white", linewidth=0.5)

	gl = ax.gridlines(
		crs=ccrs.PlateCarree(),
		color="white",
		alpha=1.0,
		linestyle="--",
		linewidth=0.25,
		xlocs=np.arange(-180, 180, 5),
		ylocs=np.arange(-90, 90, 5),
		draw_labels=True,
	)
	gl.top_labels = False
	gl.right_labels = False

	plt.colorbar(
		img1,
		label="Temperatura de brillo (C)",
		extend="both",
		orientation="vertical",
		pad=0.03,
		fraction=0.05,
	)

	# fig.text() en vez de plt.title() (que ancla al axes): con extents muy
	# anchos cartopy encoge el GeoAxes para preservar el aspecto real en
	# grados, y un título anclado al axes queda empujado fuera del canvas
	# guardado. Mismo fix que _base_map()/fig.suptitle() en plotting/common.py.
	fig.text(0.06, 0.965, f"GOES-19 Band {band}  {dt.strftime('%Y-%m-%d %H:%M')} UTC",
			 fontweight="bold", fontsize=10, ha="left", va="top")
	fig.text(0.85, 0.965, f"Reg.: {list(extent)}", fontsize=10, ha="right", va="top")

	out_path = output_dir / f"frame_{frame_idx:02d}_{dt.strftime('%Y%m%d%H%M')}.png"
	plt.savefig(str(out_path), dpi=120)
	plt.close(fig)
	_autocrop_whitespace(str(out_path))
	return out_path


def generate_goes19_animation(config: Optional[Goes19Config] = None) -> Path:
	cfg = config or Goes19Config()

	samples_dir, output_dir, figures_dir = _default_data_dirs()
	samples_dir = cfg.samples_dir or samples_dir
	output_dir = cfg.output_dir or output_dir
	figures_dir = cfg.figures_dir or figures_dir
	cpt_path = cfg.cpt_path or (Path(__file__).resolve().parent / "IR4AVHRR6.cpt")

	samples_dir.mkdir(parents=True, exist_ok=True)
	output_dir.mkdir(parents=True, exist_ok=True)
	figures_dir.mkdir(parents=True, exist_ok=True)

	if not cpt_path.exists():
		raise FileNotFoundError(
			f"No se encontro el archivo CPT en {cpt_path}. "
			"Descargalo desde https://www.dropbox.com/s/fdgnaqt91cy3x97/IR4AVHRR6.cpt "
			"y guardalo en el directorio del modulo."
		)

	cpt = loadCPT(str(cpt_path))
	if cpt is None:
		raise ValueError(f"No se pudo cargar la paleta CPT desde {cpt_path}")
	cmap = cm.colors.LinearSegmentedColormap("cpt", cpt)

	print(f"Buscando {cfg.n_images} imagenes recientes GOES-19 banda {cfg.band}...")
	files = collect_latest_images(
		cfg.band,
		samples_dir,
		n=cfg.n_images,
		max_hours_back=cfg.max_hours_back,
	)

	frame_paths: list[Path] = []
	for i, fname in enumerate(files, start=1):
		print(f"Procesando frame {i}/{len(files)}: {fname}")
		data, dt = process_nc(fname, samples_dir, output_dir, cfg.extent)
		frame_paths.append(make_frame(data, dt, i, cmap, output_dir, cfg.extent, cfg.band))

	gif_path = output_dir / f"GOES19_B{cfg.band}_animation.gif"
	frames = [Image.open(str(p)).convert("RGB") for p in frame_paths]
	frames[0].save(
		str(gif_path),
		save_all=True,
		append_images=frames[1:],
		duration=cfg.gif_delay_ms,
		loop=0,
		optimize=False,
	)

	# Nombre estable para el dashboard
	stable_gif = figures_dir / "goes19_anim.gif"
	with open(gif_path, "rb") as src, open(stable_gif, "wb") as dst:
		dst.write(src.read())

	print(f"GIF generado: {gif_path}")
	print(f"GIF para dashboard: {stable_gif}")
	return stable_gif


def _parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Genera animacion GOES-19 para dashboard ENSO")
	parser.add_argument("--band", type=int, default=13)
	parser.add_argument("--n-images", type=int, default=5)
	parser.add_argument("--max-hours-back", type=int, default=6)
	parser.add_argument("--gif-delay-ms", type=int, default=1000)
	return parser.parse_args()


def main() -> None:
	args = _parse_args()
	cfg = Goes19Config(
		band=args.band,
		n_images=args.n_images,
		max_hours_back=args.max_hours_back,
		gif_delay_ms=args.gif_delay_ms,
	)
	generate_goes19_animation(cfg)


if __name__ == "__main__":
	main()
