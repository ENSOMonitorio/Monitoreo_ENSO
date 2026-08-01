"""Cada módulo debe poder importarse sin tocar disco ni reventar por un
error de sintaxis/import — la clase de bug más barata de agarrar antes
de que llegue a producción."""
import importlib


def test_import_app():
    importlib.import_module("app")


def test_import_plotting():
    importlib.import_module("plotting")


def test_import_theme():
    importlib.import_module("theme")


def test_import_layout_historico():
    importlib.import_module("layout_historico")


def test_import_indices():
    importlib.import_module("indices")

