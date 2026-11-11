"""Gestión de usuarios (admin). Reemplaza usuarios-admin.js."""
from flask import Blueprint, flash, redirect, request, url_for
from mongoengine import Q

from ..helpers import campo, pagina_confirmar, pagina_form, panel
from ..logic import tiene_historial_cliente, tiene_historial_empleado
from ..models import ROL_LABEL, ROLES, Usuario, Vehiculo, db
from ..security import (
    crear_usuario, email_ocupado, hash_password, normalizar_email, perfil_de,
    roles_requeridos, sincronizar_perfil, usuario_actual, validar_password,
)

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

ESTADOS = ("activo", "inactivo", "suspendida")


@bp.route("/")
@roles_requeridos("admin")
def index():
    q = request.args.get("q", "").strip()
    rol = request.args.get("rol", "")
    query = Usuario.query
    if rol in ROLES:
        query = query.filter_by(rol=rol)
    if q:
        query = query.filter(Q(nombre__icontains=q) | Q(email__icontains=q))
    usuarios = query.order_by("id_usuario").all()
    conteo = {r: Usuario.query.filter_by(rol=r).count() for r in ROLES}
    return panel("panel/usuarios.html", "Gestión de usuarios",
                 "Cuentas de acceso al sistema (admin, empleados y clientes)",
                 usuarios=usuarios, conteo=conteo, total=sum(conteo.values()), q=q, rol=rol, ROL_LABEL=ROL_LABEL)


def _campos(u=None):
    return [
        campo("nombre", "Nombre completo", "text", u.nombre if u else ""),
        campo("email", "Correo electrónico", "email", u.email if u else ""),
        campo("rol", "Rol", "select", u.rol if u else "cliente", [(r, ROL_LABEL[r]) for r in ROLES]),
        campo("estado", "Estado", "select", u.estado if u else "activo", [(s, s.capitalize()) for s in ESTADOS]),
        campo("password", "Contraseña" if not u else "Nueva contraseña (opcional)", "password", "",
              required=u is None, minlength=8,
              hint="Sin contraseña la cuenta no puede iniciar sesión." if u and not u.contrasena
              else ("Déjala vacía para no cambiarla." if u else None)),
    ]


@bp.route("/nuevo", methods=["GET", "POST"])
@roles_requeridos("admin")
def nuevo():
    error = None
    if request.method == "POST":
        f = request.form
        if not f.get("nombre", "").strip():
            error = "Escribe el nombre."
        elif f.get("rol") not in ROLES or f.get("estado") not in ESTADOS:
            error = "Rol o estado no válido."
        elif email_ocupado(f.get("email")):
            error = "Ya existe una cuenta con ese correo."
        else:
            error = validar_password(f.get("password", ""))
        if error is None:
            crear_usuario(f.get("nombre"), f.get("email"), f.get("password"), f.get("rol"), f.get("estado"))
            db.session.commit()
            flash("Usuario creado.", "ok")
            return redirect(url_for("usuarios.index"))
        db.session.rollback()
    return pagina_form("Nuevo usuario", "Cuentas de acceso", _campos(), url_for("usuarios.nuevo"),
                       url_for("usuarios.index"), "Crear usuario", error)


@bp.route("/<int:uid>/editar", methods=["GET", "POST"])
@roles_requeridos("admin")
def editar(uid):
    u = db.get_or_404(Usuario, uid)
    error = None
    if request.method == "POST":
        f = request.form
        yo = usuario_actual()
        if not f.get("nombre", "").strip():
            error = "Escribe el nombre."
        elif f.get("rol") not in ROLES or f.get("estado") not in ESTADOS:
            error = "Rol o estado no válido."
        elif email_ocupado(f.get("email"), excepto_id=uid):
            error = "Ya existe una cuenta con ese correo."
        elif u.id_usuario == yo.id_usuario and (f.get("rol") != "admin" or f.get("estado") != "activo"):
            error = "No puedes quitarte el acceso de administrador a ti mismo."
        elif f.get("password"):
            error = validar_password(f.get("password"))
        if error is None:
            u.nombre, u.email = f.get("nombre").strip(), normalizar_email(f.get("email"))
            u.rol, u.estado = f.get("rol"), f.get("estado")
            if f.get("password"):
                u.contrasena = hash_password(f.get("password"))
            perfil_de(u)
            sincronizar_perfil(u)
            db.session.commit()
            flash("Usuario actualizado.", "ok")
            return redirect(url_for("usuarios.index"))
        db.session.rollback()
        u = db.get_or_404(Usuario, uid)
    return pagina_form("Editar usuario", "Cuentas de acceso", _campos(u), url_for("usuarios.editar", uid=uid),
                       url_for("usuarios.index"), "Guardar cambios", error)


def _tiene_historial(u):
    if u.cliente is not None and tiene_historial_cliente(u.cliente):
        return True
    return u.empleado is not None and tiene_historial_empleado(u.empleado)


@bp.route("/<int:uid>/eliminar", methods=["GET", "POST"])
@roles_requeridos("admin")
def eliminar(uid):
    u = db.get_or_404(Usuario, uid)
    if u.id_usuario == usuario_actual().id_usuario:
        flash("No puedes eliminar tu propia cuenta.", "error")
        return redirect(url_for("usuarios.index"))
    historial = _tiene_historial(u)
    if request.method == "POST":
        if historial:
            u.estado = "inactivo"
            if u.empleado is not None:
                u.empleado.estado = "Inactivo"
            flash(f"{u.nombre} tiene historial: la cuenta quedó Inactiva en vez de eliminarse.", "info")
        else:
            if u.cliente is not None:
                Vehiculo.query.filter_by(id_cliente=u.cliente.id_cliente).delete()
                db.session.delete(u.cliente)
            if u.empleado is not None:
                db.session.delete(u.empleado)
            db.session.flush()
            db.session.delete(u)
            flash("Usuario eliminado.", "ok")
        db.session.commit()
        return redirect(url_for("usuarios.index"))
    msg = f"¿Eliminar la cuenta de {u.nombre}? Esta acción no se puede deshacer."
    if historial:
        msg = f"{u.nombre} tiene historial de citas o servicios, así que no se borra: quedará Inactiva y sin acceso."
    return pagina_confirmar("Eliminar usuario", msg, url_for("usuarios.eliminar", uid=uid),
                            url_for("usuarios.index"), "Inactivar" if historial else "Eliminar")
