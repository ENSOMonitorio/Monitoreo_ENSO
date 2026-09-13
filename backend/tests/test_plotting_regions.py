"""Guardia de regresión de los límites geográficos de las cajas Niño:
ya se rompieron una vez (latitudes incorrectas para Niño 1+2) y deben
coincidir exactamente entre plotting.py e indices.py."""
import plotting
import indices


def test_nino_regions_have_a_color_from_the_shared_palette():
    for name, (lon0, lon1, lat0, lat1, color) in plotting.NINO_REGIONS_EQ.items():
        assert color == plotting.NINO_COLORS[name]


def test_nino_1_2_is_the_only_southern_hemisphere_leaning_box():
    lon0, lon1, lat0, lat1, _ = plotting.NINO_REGIONS_EQ["Niño 1+2"]
    assert (lat0, lat1) == (-10, 0)
    for name in ("Niño 4", "Niño 3.4", "Niño 3"):
        lon0, lon1, lat0, lat1, _ = plotting.NINO_REGIONS_EQ[name]
        assert (lat0, lat1) == (-5, 5)


def test_longitudes_are_ascending_and_within_0_360():
    for name, (lon0, lon1, lat0, lat1, _) in plotting.NINO_REGIONS_EQ.items():
        assert 0 <= lon0 < lon1 <= 360, name


def test_plotting_and_indices_agree_on_box_bounds():
    key_map = {"Niño 1+2": "nino12", "Niño 3": "nino3", "Niño 3.4": "nino34", "Niño 4": "nino4"}
    for plot_name, idx_key in key_map.items():
        lon0, lon1, lat0, lat1, _ = plotting.NINO_REGIONS_EQ[plot_name]
        idx_box = indices.NINO_REGIONS_0_360[idx_key]
        assert idx_box["lat"] == (lat0, lat1), plot_name
        assert idx_box["lon"] == (lon0, lon1), plot_name
