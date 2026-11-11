"""Agenda / reservas. Reemplaza agenda-admin.js, agenda-cliente.js y la vista de agenda del empleado."""
from datetime import date, datetime, time

from flask import Blueprint, abort, flash, redirect, request, url_for
from mongoengine import Q

from ..helpers import campo, pagina_confirmar, pagina_form, panel
from ..logic import (
    ESTADOS_RESERVA, borrar_reserva, puede_borrar_reserva, sincronizar_servicio, vehiculo_para,
)
from ..models import Cliente, Empleado, Reserva, TipoServicio, db
from ..security import login_required, roles_requeridos, usuario_actual

bp = Blueprint("agenda", __name__, url_prefix="/agenda")


@bp.route("/")
@login_required
def index():
    u = usuario_actual()
    if u.rol == "admin":
        reservas = Reserva.query.order_by("fecha_hora").all()
        return panel("panel/agenda_admin.html", "Agenda", f"Reservas · {len(reservas)} en total", reservas=reservas)

    if u.rol == "empleado":
        desde = datetime.combine(date.today(), time.min)
        reservas = Reserva.query.filter(
            id_empleado=u.empleado.id_empleado,
            estado__in=("Pendiente", "Confirmada"),
            fecha_hora__gte=desde,
        ).order_by("fecha_hora").all()
        return panel("panel/agenda_empleado.html", "Mi agenda", "Tus citas asignadas", reservas=reservas)

    reservas = (Reserva.query.filter_by(id_cliente=u.cliente.id_cliente)
                .order_by("-fecha_hora").all())
    return panel("panel/agenda_cliente.html", "Mi agenda", "Tus próximas citas y tu historial", reservas=reservas)


# ------------------------------------------------------------------ admin CRUD
def _campos(r=None):
    clientes = Cliente.query.order_by("nombre").all()
    tipos = TipoServicio.query.filter(
        Q(activo=True) | Q(id_tipo_servicio=(r.id_tipo_servicio if r else -1))
    ).all()
    empleados = Empleado.query.filter(estado__ne="Inactivo").order_by("nombre").all()
    return [
        campo("cliente", "Cliente", "select", r.id_cliente if r else "",
              [(c.id_cliente, f"{c.nombre} · {c.email}") for c in clientes],
              hint=None if clientes else "Aún no hay clientes registrados: la agenda se llena cuando un cliente se registra."),
        campo("placa", "Placa del vehículo", "text", r.vehiculo.placa if r else "", placeholder="Ej: WPQ 341"),
        campo("tipo", "Servicio", "select", r.id_tipo_servicio if r else "",
              [(t.id_tipo_servicio, t.nombre) for t in tipos]),
        campo("empleado", "Empleado asignado", "select", (r.id_empleado or "") if r else "",
              [("", "Sin asignar")] + [(e.id_empleado, f"{e.nombre} · {e.estado}") for e in empleados], required=False),
        campo("fecha", "Fecha", "date", r.fecha_hora.strftime("%Y-%m-%d") if r else ""),
        campo("hora", "Hora", "time", r.fecha_hora.strftime("%H:%M") if r else ""),
        campo("estado", "Estado", "select", r.estado if r else "Pendiente", [(e, e) for e in ESTADOS_RESERVA]),
    ]


def _guardar(r, form):
    """Aplica el formulario a la reserva. Devuelve un mensaje de error o None."""
    try:
        cliente = db.session.get(Cliente, int(form.get("cliente", "")))
        tipo = db.session.get(TipoServicio, int(form.get("tipo", "")))
        momento = datetime.strptime(f"{form.get('fecha')} {form.get('hora')}", "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return "Revisa cliente, servicio, fecha y hora."
    if cliente is None or tipo is None:
        return "Elige un cliente y un servicio válidos."
    estado = form.get("estado", "Pendiente")
    if estado not in ESTADOS_RESERVA:
        return "Estado no válido."

    emp_id = form.get("empleado", "")
    empleado = db.session.get(Empleado, int(emp_id)) if emp_id.isdigit() else None
    if empleado is not None and estado in ("Pendiente", "Confirmada") and not empleado.en_operacion:
        return f"{empleado.nombre} no está operando hoy. Elige otro lavador."

    vehiculo, error = vehiculo_para(cliente, form.get("placa"))
    if error:
        return error

    r.id_cliente, r.id_vehiculo, r.id_tipo_servicio = cliente.id_cliente, vehiculo.id_vehiculo, tipo.id_tipo_servicio
    r.id_empleado = empleado.id_empleado if empleado else None
    r.fecha_hora, r.estado = momento, estado
    db.session.add(r)
    db.session.flush()
    sincronizar_servicio(r)
    return None


@bp.route("/nueva", methods=["GET", "POST"])
@roles_requeridos("admin")
def nueva():
    error = None
    if request.method == "POST":
        error = _guardar(Reserva(), request.form)
        if error is None:
            db.session.commit()
            flash("Cita creada.", "ok")
            return redirect(url_for("agenda.index"))
        db.session.rollback()
    return pagina_form("Nueva cita", "Agenda de reservas", _campos(), url_for("agenda.nueva"),
                       url_for("agenda.index"), "Crear cita", error)


@bp.route("/<int:rid>/editar", methods=["GET", "POST"])
@roles_requeridos("admin")
def editar(rid):
    r = db.get_or_404(Reserva, rid)
    if r.servicio is not None and r.servicio.estado != "En espera":
        flash("Ese servicio ya está en curso o finalizado y no se puede editar.", "error")
        return redirect(url_for("agenda.index"))
    error = None
    if request.method == "POST":
        error = _guardar(r, request.form)
        if error is None:
            db.session.commit()
            flash("Cita actualizada.", "ok")
            return redirect(url_for("agenda.index"))
        db.session.rollback()
        r = db.get_or_404(Reserva, rid)
    return pagina_form("Editar cita", "Agenda de reservas", _campos(r), url_for("agenda.editar", rid=rid),
                       url_for("agenda.index"), "Guardar cambios", error)


@bp.route("/<int:rid>/eliminar", methods=["GET", "POST"])
@roles_requeridos("admin")
def eliminar(rid):
    r = db.get_or_404(Reserva, rid)
    if not puede_borrar_reserva(r):
        flash("Ese servicio ya está en curso o finalizado y no se puede eliminar.", "error")
        return redirect(url_for("agenda.index"))
    if request.method == "POST":
        borrar_reserva(r)
        db.session.commit()
        flash("Cita eliminada.", "ok")
        return redirect(url_for("agenda.index"))
    return pagina_confirmar(
        "Eliminar cita", f"¿Cancelar y eliminar la cita de {r.cliente.nombre} ({r.vehiculo.placa}) de la agenda?",
        url_for("agenda.eliminar", rid=rid), url_for("agenda.index"))


# -------------------------------------------------------------- cliente cancela
@bp.route("/<int:rid>/cancelar", methods=["POST"])
@roles_requeridos("cliente")
def cancelar(rid):
    r = db.get_or_404(Reserva, rid)
    if r.id_cliente != usuario_actual().cliente.id_cliente:
        abort(403)
    if r.estado not in ("Pendiente", "Confirmada"):
        flash("Esa cita ya no se puede cancelar.", "error")
    elif r.servicio is not None and r.servicio.estado != "En espera":
        flash("Tu lavado ya comenzó y no se puede cancelar.", "error")
    else:
        r.estado = "Cancelada"
        sincronizar_servicio(r)
        db.session.commit()
        flash("Cita cancelada.", "ok")
    return redirect(url_for("agenda.index"))
