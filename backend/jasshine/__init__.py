"""JASSHINE — Lavadero Inteligente (aplicación web en Python / Flask)."""
import os
import secrets
from pathlib import Path

from flask import Flask, render_template
from dotenv import load_dotenv

from .helpers import registrar_filtros
from .icons import ICONS
from .models import db
from .security import NAV, PANEL_CSS, csrf_token, usuario_actual, verificar_csrf
from .seed import sembrar_si_vacia


def _secret_key(instance_path):
    """Clave para firmar las sesiones: variable de entorno o archivo generado una vez."""
    env = os.environ.get("JASSHINE_SECRET")
    if env:
        return env
    ruta = Path(instance_path) / "secret.key"
    if not ruta.exists():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(secrets.token_hex(32))
    return ruta.read_text().strip()


def create_app(config=None):
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env", override=False)
    app = Flask(
        __name__,
        instance_relative_config=True,
        instance_path=str(project_root / "instance"),
        template_folder=str(project_root / "frontend" / "templates"),
        static_folder=str(project_root / "frontend" / "static"),
    )
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app.config.update(
        SECRET_KEY=_secret_key(app.instance_path),
        MONGODB_URI=os.environ.get("MONGODB_URI"),
        MONGODB_DB=os.environ.get("MONGODB_DB", "jasshine"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)

    db.init_app(app)
    registrar_filtros(app)
    app.jinja_env.globals["csrf_token"] = csrf_token

    from .views import registrar_modulos
    registrar_modulos(app)

    app.before_request(db.session.clear)
    app.before_request(verificar_csrf)
    app.teardown_request(lambda error: db.session.clear())

    @app.context_processor
    def contexto_global():
        u = usuario_actual()
        return {
            "ICONS": ICONS,
            "usuario": u,
            "perfil": (u.cliente or u.empleado) if u else None,
            "csrf_token": csrf_token,
            "NAV": NAV.get(u.rol, []) if u else [],
            "PANEL_CSS": PANEL_CSS.get(u.rol) if u else None,
        }

    def pagina_error(codigo, titulo, mensaje):
        return render_template("error.html", codigo=codigo, titulo=titulo, mensaje=mensaje), codigo

    @app.errorhandler(400)
    def e400(err):
        return pagina_error(400, "Solicitud no válida", getattr(err, "description", "") or "No se pudo procesar la solicitud.")

    @app.errorhandler(403)
    def e403(err):
        return pagina_error(403, "Sin acceso", "Tu cuenta no tiene permiso para ver esta sección.")

    @app.errorhandler(404)
    def e404(err):
        return pagina_error(404, "Página no encontrada", "La página que buscas no existe.")

    with app.app_context():
        db.create_all()
        sembrar_si_vacia()

    return app
