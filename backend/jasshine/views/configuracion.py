"""Configuración de cada rol: perfil, preferencias, datos del negocio y contraseña.

Reemplaza configuracion-admin.js, configuracion-empleado.js y configuracion-cliente.js.
"""
from flask import Blueprint, flash, redirect, request, url_for

from ..helpers import panel
from ..models import Negocio, Preferencia, Vehiculo, db
from ..security import (
    email_ocupado, hash_password, login_required, normalizar_email, sincronizar_perfil,
    usuario_actual, validar_password, verificar_password,
)

bp = Blueprint("configuracion", __name__, url_prefix="/configuracion")

# (clave, título, descripción, valor por defecto)
PREFERENCIAS = {
    "admin": [
        ("notif-correo", "Notificaciones por correo", "Nuevas citas y cancelaciones", True),
        ("notif-push", "Notificaciones push", "Alertas en tiempo real", True),
        ("recordatorios", "Recordatorios a clientes", "SMS 1 hora antes de la cita", False),
        ("mantenimiento", "Modo mantenimiento", "Oculta la agenda en línea temporalmente", False),
    ],
    "empleado": [
        ("notif-citas", "Notificaciones de nuevas citas", "Avisos cuando te asignen un servicio", True),
        ("resumen-diario", "Resumen diario", "Comisión del día por correo", True),
        ("disponible", "Disponible para citas", "Aparecer en la agenda de administración", True),
    ],
    "cliente": [
        ("recordatorios", "Recordatorios de citas", "SMS 1 hora antes", True),
        ("promos", "Notificaciones de promociones", "Ofertas y descuentos de JASSHINE", False),
        ("empleado-favorito", "Lavador de confianza", "Priorizar a tu lavador favorito al agendar", True),
    ],
}


def _prefs(u):
    guardadas = {p.clave: p.valor for p in Preferencia.query.filter_by(id_usuario=u.id_usuario)}
    return [{"clave": c, "titulo": t, "sub": s, "valor": guardadas.get(c, d)} for c, t, s, d in PREFERENCIAS[u.rol]]


def _guardar_prefs(u, form):
    for clave, _, _, _ in PREFERENCIAS[u.rol]:
        marcado = f"pref_{clave}" in form
        p = Preferencia.query.filter_by(id_usuario=u.id_usuario, clave=clave).first()
        if p is None:
            db.session.add(Preferencia(id_usuario=u.id_usuario, clave=clave, valor=marcado))
        else:
            p.valor = marcado


def _guardar_perfil(u, f):
    nombre = f.get("nombre", "").strip()
    if not nombre:
        return "Escribe tu nombre."
    if email_ocupado(f.get("email"), excepto_id=u.id_usuario):
        return "Ese correo ya lo usa otra cuenta."
    u.nombre, u.email = nombre, normalizar_email(f.get("email"))
    sincronizar_perfil(u)
    if u.rol in ("cliente", "empleado"):
        (u.cliente or u.empleado).telefono = f.get("telefono", "").strip()

    if u.rol == "cliente":
        placa, tipo = f.get("placa", "").strip().upper(), f.get("moto", "").strip() or "Moto"
        cli = u.cliente
        if placa:
            existente = Vehiculo.query.filter_by(placa=placa).first()
            if existente is not None and existente.id_cliente != cli.id_cliente:
                return "Esa placa ya está registrada a nombre de otro cliente."
            if cli.vehiculos:
                v = cli.vehiculos[0]
                v.placa, v.tipo = placa, tipo
            else:
                db.session.add(Vehiculo(id_cliente=cli.id_cliente, tipo=tipo, placa=placa))
        elif cli.vehiculos:
            cli.vehiculos[0].tipo = tipo

    if u.rol == "admin":
        n = Negocio.query.first() or Negocio(nombre="", meta_mensual=0)
        n.nombre = f.get("neg_nombre", "").strip() or n.nombre or "JASSHINE"
        n.correo, n.telefono = f.get("neg_correo", "").strip(), f.get("neg_telefono", "").strip()
        n.direccion = f.get("neg_direccion", "").strip()
        try:
            n.meta_mensual = max(0, float(f.get("neg_meta", "0") or 0))
        except ValueError:
            return "La meta mensual debe ser un número."
        db.session.add(n)

    _guardar_prefs(u, f)
    return None


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    u = usuario_actual()
    error_perfil = error_pass = None

    if request.method == "POST":
        if request.form.get("accion") == "password":
            actual, nueva = request.form.get("actual", ""), request.form.get("nueva", "")
            if not verificar_password(u, actual):
                error_pass = "La contraseña actual no es correcta."
            elif request.form.get("confirmar", "") != nueva:
                error_pass = "Las contraseñas nuevas no coinciden."
            else:
                error_pass = validar_password(nueva)
            if error_pass is None:
                u.contrasena = hash_password(nueva)
                db.session.commit()
                flash("Contraseña actualizada.", "ok")
                return redirect(url_for("configuracion.index"))
        else:
            error_perfil = _guardar_perfil(u, request.form)
            if error_perfil is None:
                db.session.commit()
                flash("Cambios guardados.", "ok")
                return redirect(url_for("configuracion.index"))
            db.session.rollback()

    perfil = u.cliente or u.empleado
    vehiculo = u.cliente.vehiculos[0] if u.rol == "cliente" and u.cliente.vehiculos else None
    sub = {"admin": "Datos del negocio y preferencias"}.get(u.rol, "Tu perfil y preferencias")
    return panel("panel/configuracion.html", "Configuración", sub,
                 prefs=_prefs(u), negocio=Negocio.query.first(), perfil=perfil, vehiculo=vehiculo,
                 form=request.form if error_perfil else None,
                 error_perfil=error_perfil, error_pass=error_pass)
