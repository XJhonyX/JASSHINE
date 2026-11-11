"""Autenticación y autorización (lo que antes hacía js/auth.js, ahora en el servidor)."""
import secrets
from functools import wraps

from flask import abort, flash, g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .models import Cliente, Empleado, Usuario, db

PASSWORD_MIN = 8


# ---------------------------------------------------------------- contraseñas
def validar_password(password):
    if not password or len(password) < PASSWORD_MIN:
        return f"La contraseña debe tener al menos {PASSWORD_MIN} caracteres."
    return None


def hash_password(password):
    return generate_password_hash(password)


def verificar_password(usuario, password):
    return bool(usuario.contrasena) and check_password_hash(usuario.contrasena, password)


def normalizar_email(email):
    return (email or "").strip().lower()


def email_ocupado(email, excepto_id=None):
    q = Usuario.query.filter(email__iexact=normalizar_email(email))
    if excepto_id is not None:
        q = q.filter(id_usuario__ne=excepto_id)
    return q.first() is not None


# ------------------------------------------------------------------- sesión
def usuario_actual():
    """Cuenta con la sesión iniciada (o None). Se valida contra la base en cada petición."""
    if "usuario" not in g:
        g.usuario = None
        uid = session.get("uid")
        if uid:
            u = db.session.get(Usuario, uid)
            if u and u.estado == "activo":
                g.usuario = u
            else:
                session.pop("uid", None)
    return g.usuario


def iniciar_sesion(usuario):
    session.clear()
    session["uid"] = usuario.id_usuario
    session["_csrf"] = secrets.token_hex(16)


def cerrar_sesion():
    session.clear()


def crear_usuario(nombre, email, password, rol, estado="activo"):
    u = Usuario(
        nombre=nombre.strip(),
        email=normalizar_email(email),
        contrasena=hash_password(password) if password else "",
        rol=rol,
        estado=estado,
    )
    db.session.add(u)
    db.session.flush()
    perfil_de(u)
    return u


# --------------------------------------------------------- perfiles vinculados
def perfil_de(usuario):
    """Perfil de Cliente o Empleado de la cuenta (se crea si falta)."""
    if usuario.rol == "cliente":
        p = usuario.cliente
        if p is None:
            p = Cliente(
                id_usuario=usuario.id_usuario,
                nombre=usuario.nombre,
                email=usuario.email,
                telefono="",
            )
            db.session.add(p)
            db.session.flush()
        return p
    if usuario.rol == "empleado":
        p = usuario.empleado
        if p is None:
            p = Empleado(
                id_usuario=usuario.id_usuario, nombre=usuario.nombre, email=usuario.email,
                telefono="", especialidad="Lavador", estado="Disponible",
            )
            db.session.add(p)
            db.session.flush()
        return p
    return None


def sincronizar_perfil(usuario):
    """Mantiene el perfil igual que la cuenta cuando cambia nombre o correo."""
    p = perfil_de(usuario)
    if p is not None:
        p.nombre = usuario.nombre
        p.email = usuario.email


# ---------------------------------------------------------------------- CSRF
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def verificar_csrf():
    if request.method == "POST":
        enviado = request.form.get("csrf_token", "")
        esperado = session.get("_csrf", "")
        if not esperado or not secrets.compare_digest(enviado, esperado):
            abort(400, description="Formulario vencido o inválido. Recarga la página e inténtalo de nuevo.")


# ---------------------------------------------------------------- decoradores
def login_required(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if usuario_actual() is None:
            flash("Inicia sesión para continuar.", "error")
            return redirect(url_for("auth.login"))
        return vista(*args, **kwargs)
    return envoltura


def roles_requeridos(*roles):
    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(*args, **kwargs):
            if usuario_actual().rol not in roles:
                abort(403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


# ----------------------------------------------------------------------- menú
# (blueprint, etiqueta, ícono)
NAV = {
    "admin": [
        ("inicio", "Panel general", "panel"),
        ("empleados", "Empleados", "empleados"),
        ("usuarios", "Gestión de usuarios", "usuarios"),
        ("comisiones", "Comisiones", "comisiones"),
        ("agenda", "Agenda", "agenda"),
        ("servicio", "Servicios", "servicios"),
        ("facturacion", "Facturación", "facturacion"),
        ("reportes", "Reportes", "reportes"),
    ],
    "empleado": [
        ("inicio", "Inicio", "inicio"),
        ("agenda", "Mi agenda", "mi-agenda"),
        ("servicio", "Servicio", "servicio"),
        ("recibos", "Mis Recibos", "recibos"),
    ],
    "cliente": [
        ("inicio", "Inicio", "inicio"),
        ("agenda", "Mi agenda", "mi-agenda"),
        ("servicio", "Servicio", "servicio"),
        ("empleados", "Empleados", "empleados"),
        ("recibos", "Mis Recibos", "recibos"),
    ],
}

PANEL_CSS = {
    "admin": "panel-administrador.css",
    "empleado": "panel-empleado.css",
    "cliente": "panel-cliente.css",
}
