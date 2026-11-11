"""Empleados: gestión (admin) y directorio del equipo (cliente). Reemplaza empleados-admin.js."""
from flask import Blueprint, flash, redirect, request, url_for
from mongoengine import Q

from ..helpers import campo, pagina_confirmar, pagina_form, panel
from ..logic import ESTADOS_EMPLEADO, tiene_historial_empleado
from ..models import Empleado, Usuario, db
from ..security import (
    crear_usuario, email_ocupado, hash_password, login_required, normalizar_email,
    roles_requeridos, sincronizar_perfil, usuario_actual, validar_password,
)

bp = Blueprint("empleados", __name__, url_prefix="/empleados")


@bp.route("/")
@login_required
def index():
    u = usuario_actual()
    if u.rol == "cliente":
        equipo = Empleado.query.filter(estado__ne="Inactivo").order_by("nombre").all()
        return panel("panel/empleados_cliente.html", "Empleados", "Conoce al equipo de JASSHINE", equipo=equipo)
    if u.rol != "admin":
        return redirect(url_for("inicio.index"))

    q = request.args.get("q", "").strip()
    query = Empleado.query
    if q:
        query = query.filter(
            Q(nombre__icontains=q) | Q(especialidad__icontains=q) | Q(email__icontains=q)
        )
    empleados = query.order_by("id_empleado").all()
    total = Empleado.query.count()
    return panel("panel/empleados_admin.html", "Empleados", "Gestiona el equipo de lavadores",
                 empleados=empleados, total=total, q=q)


def _campos(e=None):
    return [
        campo("nombre", "Nombre completo", "text", e.nombre if e else ""),
        campo("email", "Correo electrónico", "email", e.email if e else ""),
        campo("telefono", "Teléfono", "text", (e.telefono or "") if e else ""),
        campo("cargo", "Cargo", "text", e.cargo if e else "", placeholder="Ej: Lavador senior"),
        campo("estado", "Estado", "select", e.estado if e else "Disponible", [(s, s) for s in ESTADOS_EMPLEADO]),
        campo("password", "Contraseña" if not e else "Nueva contraseña (opcional)", "password", "",
              required=e is None, minlength=8,
              hint="Con ella el empleado inicia sesión." if not e else "Déjala vacía para no cambiarla."),
    ]


def _sincronizar_estado_cuenta(emp):
    """Un empleado Inactivo no puede iniciar sesión; al reactivarlo recupera el acceso."""
    if emp.estado == "Inactivo":
        emp.usuario.estado = "inactivo"
    elif emp.usuario.estado == "inactivo":
        emp.usuario.estado = "activo"


@bp.route("/nuevo", methods=["GET", "POST"])
@roles_requeridos("admin")
def nuevo():
    error = None
    if request.method == "POST":
        f = request.form
        nombre = f.get("nombre", "").strip()
        if not nombre:
            error = "Escribe el nombre."
        elif f.get("estado") not in ESTADOS_EMPLEADO:
            error = "Estado no válido."
        elif email_ocupado(f.get("email")):
            error = "Ya existe una cuenta con ese correo."
        else:
            error = validar_password(f.get("password", ""))
        if error is None:
            u = crear_usuario(nombre, f.get("email"), f.get("password"), "empleado")
            e = u.empleado
            e.telefono, e.especialidad, e.estado = f.get("telefono", "").strip(), f.get("cargo", "").strip(), f.get("estado")
            _sincronizar_estado_cuenta(e)
            db.session.commit()
            flash(f"Empleado {nombre} creado. Ya puede iniciar sesión.", "ok")
            return redirect(url_for("empleados.index"))
        db.session.rollback()
    return pagina_form("Nuevo empleado", "Equipo de lavadores", _campos(), url_for("empleados.nuevo"),
                       url_for("empleados.index"), "Crear empleado", error)


@bp.route("/<int:eid>/editar", methods=["GET", "POST"])
@roles_requeridos("admin")
def editar(eid):
    e = db.get_or_404(Empleado, eid)
    error = None
    if request.method == "POST":
        f = request.form
        if not f.get("nombre", "").strip():
            error = "Escribe el nombre."
        elif f.get("estado") not in ESTADOS_EMPLEADO:
            error = "Estado no válido."
        elif email_ocupado(f.get("email"), excepto_id=e.id_usuario):
            error = "Ya existe una cuenta con ese correo."
        elif f.get("password"):
            error = validar_password(f.get("password"))
        if error is None:
            e.usuario.nombre = f.get("nombre").strip()
            e.usuario.email = normalizar_email(f.get("email"))
            e.telefono, e.especialidad, e.estado = f.get("telefono", "").strip(), f.get("cargo", "").strip(), f.get("estado")
            if f.get("password"):
                e.usuario.contrasena = hash_password(f.get("password"))
            sincronizar_perfil(e.usuario)
            _sincronizar_estado_cuenta(e)
            db.session.commit()
            flash("Empleado actualizado.", "ok")
            return redirect(url_for("empleados.index"))
        db.session.rollback()
        e = db.get_or_404(Empleado, eid)
    return pagina_form("Editar empleado", "Equipo de lavadores", _campos(e), url_for("empleados.editar", eid=eid),
                       url_for("empleados.index"), "Guardar cambios", error)


@bp.route("/<int:eid>/eliminar", methods=["GET", "POST"])
@roles_requeridos("admin")
def eliminar(eid):
    e = db.get_or_404(Empleado, eid)
    historial = tiene_historial_empleado(e)
    if request.method == "POST":
        if historial:
            e.estado = "Inactivo"
            e.usuario.estado = "inactivo"
            flash(f"{e.nombre} tiene historial de servicios: quedó Inactivo en vez de eliminarse.", "info")
        else:
            usuario = e.usuario
            db.session.delete(e)
            db.session.flush()
            db.session.delete(usuario)
            flash("Empleado eliminado.", "ok")
        db.session.commit()
        return redirect(url_for("empleados.index"))
    msg = f"¿Eliminar a {e.nombre} del equipo? Esta acción no se puede deshacer."
    if historial:
        msg = f"{e.nombre} tiene historial de servicios, así que no se borra: quedará como Inactivo y sin acceso."
    return pagina_confirmar("Eliminar empleado", msg, url_for("empleados.eliminar", eid=eid),
                            url_for("empleados.index"), "Inactivar" if historial else "Eliminar")
