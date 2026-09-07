import importlib
import os


def _client():
    app_module = importlib.import_module("app")
    return app_module, app_module.server.test_client()


def test_api_config_lists_map_tabs():
    app_module, client = _client()
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "map_tabs" in body and "auth_enabled" in body
    prefixes = {tab["prefix"] for tab in body["map_tabs"]}
    assert prefixes == {prefix for prefix, _ in app_module.MAP_TABS}
    assert body["auth_enabled"] is False


def test_api_figures_unknown_prefix_is_404():
    _, client = _client()
    resp = client.get("/api/figures/no-existe")
    assert resp.status_code == 404


def test_api_figures_known_prefix_shape():
    _, client = _client()
    resp = client.get("/api/figures/tsm")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["prefix"] == "tsm"
    assert isinstance(body["dates"], list)
    assert "image_url" in body and "anim_url" in body and "composite_anim_url" in body


def test_api_indices_lists_all_four_regions():
    _, client = _client()
    resp = client.get("/api/indices")
    assert resp.status_code == 200
    keys = {region["key"] for region in resp.get_json()["regions"]}
    assert keys == {"nino12", "nino34", "nino3", "nino4"}


def test_api_indices_unknown_region_is_404():
    _, client = _client()
    resp = client.get("/api/indices/no-existe")
    assert resp.status_code == 404


def test_api_indices_region_returns_plotly_figure_json():
    _, client = _client()
    resp = client.get("/api/indices/nino12")
    assert resp.status_code == 200
    body = resp.get_json()
    if body != {"available": False}:
        assert "data" in body and "layout" in body


def test_api_historico_oni_returns_plotly_figure_json():
    _, client = _client()
    resp = client.get("/api/historico/oni")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "data" in body and "layout" in body


def test_api_historico_eventos_returns_nine_events():
    _, client = _client()
    resp = client.get("/api/historico/eventos")
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body) == 9
    assert {"yr", "title", "stat", "desc", "src"} <= body[0].keys()


def test_api_status_shape():
    _, client = _client()
    resp = client.get("/api/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "text" in body and "is_running" in body


def test_api_pipeline_status_shape():
    _, client = _client()
    resp = client.get("/api/pipeline/status")
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body.keys()) == {"running", "ok", "error", "last_attempt_ts", "last_success"}


def test_api_pipeline_run_rejects_when_already_running(monkeypatch):
    app_module, client = _client()
    monkeypatch.setattr(app_module, "_pipeline_running", lambda: True)
    resp = client.post("/api/pipeline/run")
    assert resp.status_code == 409
    assert resp.get_json()["started"] is False


def test_spa_fallback_404s_without_a_frontend_build(monkeypatch):
    # En este checkout backend/app/static/ no existe (se genera recién en el
    # stage de build de Angular del Dockerfile) — la SPA debe degradar a 404
    # en vez de reventar, tanto para "/" como para una ruta profunda.
    app_module, client = _client()
    assert not os.path.exists(app_module.STATIC_DIR)
    assert client.get("/").status_code == 404
    assert client.get("/indices").status_code == 404


def test_api_pipeline_run_spawns_when_idle(monkeypatch):
    app_module, client = _client()
    monkeypatch.setattr(app_module, "_pipeline_running", lambda: False)
    calls = {}

    def fake_popen(args, cwd=None):
        calls["args"] = args
        calls["cwd"] = cwd
        return None

    monkeypatch.setattr(app_module.subprocess, "Popen", fake_popen)
    resp = client.post("/api/pipeline/run")
    assert resp.status_code == 202
    assert resp.get_json()["started"] is True
    assert calls["args"][-1] == app_module.PIPELINE_SCRIPT
