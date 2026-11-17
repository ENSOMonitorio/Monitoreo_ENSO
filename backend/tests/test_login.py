"""Login rediseñado (spec de rediseño §6.1) y redirección `next` segura."""
import importlib
from urllib.parse import urlparse

import pytest
from werkzeug.security import generate_password_hash


@pytest.fixture
def auth_client(monkeypatch):
    app_module = importlib.import_module("app")
    monkeypatch.setattr(app_module, "AUTH_USER", "demo")
    monkeypatch.setattr(app_module, "AUTH_PASS_HASH", generate_password_hash("clave"))
    return app_module.server.test_client()


def test_login_page_renders_new_design(auth_client):
    html = auth_client.get("/login").get_data(as_text=True)
    assert "El Niño–Oscilación del Sur" in html
    assert "/login-assets/past-el-nino-gif-1.webp" in html
    assert "Iniciar sesión" in html and "Mostrar" in html
    assert "La sesión queda abierta 7 días" in html
    assert "no reemplaza los comunicados del ENFEN" in html
    assert "Continuar con Google" not in html


def test_login_page_shows_no_enso_data(auth_client):
    html = auth_client.get("/login").get_data(as_text=True)
    assert "/api/" not in html
    assert "/figures/" not in html


def test_wrong_password_shows_error(auth_client):
    resp = auth_client.post("/login", data={"username": "demo", "password": "mal"})
    assert resp.status_code == 200
    assert "Usuario o contraseña incorrectos." in resp.get_data(as_text=True)


def test_login_page_without_error_has_no_alert(auth_client):
    html = auth_client.get("/login").get_data(as_text=True)
    assert "Usuario o contraseña incorrectos." not in html


def test_good_login_redirects_to_next_path(auth_client):
    resp = auth_client.post("/login?next=/subsurf", data={"username": "demo", "password": "clave"})
    assert resp.status_code == 302
    assert urlparse(resp.headers["Location"]).path == "/subsurf"


@pytest.mark.parametrize("bad", ["https://evil.example", "//evil.example", "/\\evil.example"])
def test_good_login_ignores_external_next(auth_client, bad):
    resp = auth_client.post("/login", query_string={"next": bad},
                            data={"username": "demo", "password": "clave"})
    assert resp.status_code == 302
    loc = urlparse(resp.headers["Location"])
    assert loc.netloc in ("", "localhost")
    assert loc.path == "/"
