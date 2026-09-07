import importlib


def test_health_endpoint_ok():
    app_module = importlib.import_module("app")
    client = app_module.server.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_bypasses_login_when_auth_enabled(monkeypatch):
    app_module = importlib.import_module("app")
    monkeypatch.setattr(app_module, "AUTH_PASS_HASH", "scrypt:32768:8:1$fake$fake")
    client = app_module.server.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200

    resp_root = client.get("/", follow_redirects=False)
    assert resp_root.status_code in (301, 302)
    assert "/login" in resp_root.headers.get("Location", "")
