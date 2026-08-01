import os
import sys

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# El login queda deshabilitado en tests (mismo comportamiento que producción
# cuando ENSO_AUTH_PASS_HASH no está seteada, ver app.py: _require_login).
os.environ.setdefault("ENSO_SECRET_KEY", "test-secret-key")
os.environ.pop("ENSO_AUTH_PASS_HASH", None)
