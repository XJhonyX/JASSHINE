import html
import os
import re
import sys
import uuid
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["JASSHINE_SECRET"] = "clave-de-pruebas"

from backend.jasshine import create_app  # noqa: E402
from backend.jasshine.models import db   # noqa: E402

ADMIN = ("admin@jasshine.co", "Admin12345")
MANANA = (date.today() + timedelta(days=1)).isoformat()


@pytest.fixture()
def app(tmp_path):
    """Usa una base MongoDB efímera e independiente para cada prueba."""
    app = create_app({
        "TESTING": True,
        "MONGODB_MOCK": True,
        "MONGODB_URI": "mongodb://localhost",
        "MONGODB_DB": f"jasshine_test_{uuid.uuid4().hex}",
    })
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.close()


class Cliente:
    """Navegador de pruebas con ayudas para formularios (agrega el token CSRF solo)."""

    def __init__(self, app):
        self.c = app.test_client()

    def get(self, url, **kw):
        return self.c.get(url, follow_redirects=kw.pop("follow", True), **kw)

    def post(self, url, data=None, follow=True, csrf=True):
        data = dict(data or {})
        if csrf:
            with self.c.session_transaction() as s:
                s.setdefault("_csrf", "tok")
                data["csrf_token"] = s["_csrf"]
        return self.c.post(url, data=data, follow_redirects=follow)

    def login(self, email, password, rol):
        return self.post("/login", {"email": email, "password": password, "rol": rol})

    def logout(self):
        return self.post("/logout")

    def registrar(self, nombre, email, password="secreto123"):
        return self.post("/registro", {"nombre": nombre, "email": email, "password": password})


@pytest.fixture()
def nav(app):
    return Cliente(app)


@pytest.fixture()
def admin(app):
    n = Cliente(app)
    r = n.login(*ADMIN, "admin")
    assert "Panel general" in r.get_data(as_text=True)
    return n


def texto(resp):
    return re.sub(r"\s+", " ", html.unescape(resp.get_data(as_text=True)))
