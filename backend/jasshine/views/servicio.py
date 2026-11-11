"""Servicio: catálogo (admin), cola del empleado y agendar (cliente).

Reemplaza servicios-admin.js, servicio-empleado.js y servicio-cliente.js.
"""
from datetime import date, datetime, time

from flask import Blueprint, abort, flash, redirect, request, url_for
from mongoengine import Q

from ..helpers import campo, pagina_confirmar, pagina_form, panel
from ..logic import finalizar_servicio, iniciar_servicio, sincronizar_servicio, vehiculo_para
from ..models import Empleado, Reserva, Servicio, TipoServicio, db
from ..security import login_required, roles_requeridos, usuario_actual

bp = Blueprint("servicio", __name__, url_prefix="/servicio")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    u = usuario_actual()
    if u.rol == "admin":
        return _catalogo()
    if u.rol == "empleado":
        return _cola(u)
    return _agendar(u)


# ===================================================================== admin
def _catalogo():
    tipos = TipoServicio.query.order_by("id_tipo_servicio").all()
    mes_ini = datetime.combine(date.today().replace(day=1), time.min)
    conteo = []
    for t in tipos:
        n = Reserva.query.filter(
            id_tipo_servicio=t.id_tipo_servicio,
            estado__ne="Cancelada",
            fecha_hora__gte=mes_ini,
        ).count()
        conteo.append({"tipo": t, "n": n})
    conteo.sort(key=lambda x: -x["n"])
    maximo = max([c["n"] for c in conteo] + [1])
    for c in conteo:
        c["pct"] = round(c["n"] * 100 / maximo)
    return panel("panel/servicios_admin.html", "Servicios", "Catálogo y precios de lavado",
                 tipos=tipos, conteo=conteo)


def _campos(t=None):
    return [
        campo("nombre", "Nombre del servicio", "text", t.nombre if t else ""),
        campo("descripcion", "Descripción", "text", (t.descripcion or "") if t else "", required=False),
        campo("precio", "Precio (COP)", "number", int(t.precio) if t else "", min=0, step=500),
        campo("duracion", "Duración (minutos)", "number", t.duracion_min if t else "", min=1),
        campo("activo", "Disponible para agendar", "select", "1" if (t is None or t.activo) else "0",
              [("1", "Sí, visible para los clientes"), ("0", "No, oculto")]),
    ]


def _guardar_tipo(t, f):
    nombre = f.get("nombre", "").strip()
    if not nombre:
        return "Escribe el nombre del servicio."
    otro = TipoServicio.query.filter(nombre__iexact=nombre)
    if t.id_tipo_servicio:
        otro = otro.filter(id_tipo_servicio__ne=t.id_tipo_servicio)
    if otro.first() is not None:
        return "Ya existe un servicio con ese nombre."
    try:
        precio, duracion = float(f.get("precio", "")), int(f.get("duracion", ""))
    except ValueError:
        return "Revisa el precio y la duración."
    if precio < 0 or duracion < 1:
        return "El precio y la duración deben ser positivos."
    t.nombre, t.descripcion = nombre, f.get("descripcion", "").strip()
    t.precio, t.duracion_min, t.activo = precio, duracion, f.get("activo") == "1"
    db.session.add(t)
    return None


@bp.route("/nuevo", methods=["GET", "POST"])
@roles_requeridos("admin")
def nuevo():
    error = None
    if request.method == "POST":
        error = _guardar_tipo(TipoServicio(), request.form)
        if error is None:
            db.session.commit()
            flash("Servicio agregado al catálogo.", "ok")
            return redirect(url_for("servicio.index"))
        db.session.rollback()
    return pagina_form("Nuevo servicio", "Catálogo de servicios", _campos(), url_for("servicio.nuevo"),
                       url_for("servicio.index"), "Crear servicio", error)


@bp.route("/<int:tid>/editar", methods=["GET", "POST"])
@roles_requeridos("admin")
def editar(tid):
    t = db.get_or_404(TipoServicio, tid)
    error = None
    if request.method == "POST":
        error = _guardar_tipo(t, request.form)
        if error is None:
            db.session.commit()
            flash("Servicio actualizado.", "ok")
            return redirect(url_for("servicio.index"))
        db.session.rollback()
        t = db.get_or_404(TipoServicio, tid)
    return pagina_form("Editar servicio", "Catálogo de servicios", _campos(t), url_for("servicio.editar", tid=tid),
                       url_for("servicio.index"), "Guardar cambios", error)


@bp.route("/<int:tid>/eliminar", methods=["GET", "POST"])
@roles_requeridos("admin")
def eliminar(tid):
    t = db.get_or_404(TipoServicio, tid)
    usado = (Reserva.query.filter_by(id_tipo_servicio=tid).first() is not None
             or Servicio.query.filter_by(id_tipo_servicio=tid).first() is not None)
    if request.method == "POST":
        if usado:
            t.activo = False
            flash(f'"{t.nombre}" ya se usó en citas: quedó oculto en vez de eliminarse.', "info")
        else:
            db.session.delete(t)
            flash("Servicio eliminado del catálogo.", "ok")
        db.session.commit()
        return redirect(url_for("servicio.index"))
    msg = f'¿Eliminar "{t.nombre}" del catálogo?'
    if usado:
        msg = f'"{t.nombre}" ya se usó en citas, así que no se borra: quedará oculto para los clientes.'
    return pagina_confirmar("Eliminar servicio", msg, url_for("servicio.eliminar", tid=tid),
                            url_for("servicio.index"), "Ocultar" if usado else "Eliminar")


# ================================================================== empleado
def _cola(u):
    emp = u.empleado
    todos = Servicio.query.filter(
        id_empleado=emp.id_empleado, estado__in=("En espera", "En curso")
    ).order_by("fecha_inicio").all()
    espera = [s for s in todos if s.estado == "En espera"]
    en_curso = [s for s in todos if s.estado == "En curso"]
    return panel("panel/servicio_empleado.html", "Servicio", "Cola de lavados asignados a ti",
                 espera=espera, en_curso=en_curso, total=len(todos))


def _servicio_propio(sid):
    s = db.get_or_404(Servicio, sid)
    if s.id_empleado != usuario_actual().empleado.id_empleado:
        abort(403)
    return s


@bp.route("/<int:sid>/iniciar", methods=["POST"])
@roles_requeridos("empleado")
def iniciar(sid):
    error = iniciar_servicio(_servicio_propio(sid))
    if error:
        flash(error, "error")
    else:
        db.session.commit()
        flash("Lavado iniciado.", "ok")
    return redirect(url_for("servicio.index"))


@bp.route("/<int:sid>/finalizar", methods=["POST"])
@roles_requeridos("empleado")
def finalizar(sid):
    error = finalizar_servicio(_servicio_propio(sid))
    if error:
        flash(error, "error")
    else:
        db.session.commit()
        flash("Lavado finalizado ✓ — se generó la comisión y el recibo.", "ok")
    return redirect(url_for("servicio.index"))


# =================================================================== cliente
def _agendar(u):
    cli = u.cliente
    tipos = TipoServicio.query.filter_by(activo=True).order_by("id_tipo_servicio").all()
    empleados = Empleado.query.order_by("id_empleado").all()
    form, error = {"tipo": "", "placa": "", "fecha": "", "hora": "", "empleado": ""}, None

    if cli.vehiculos:
        form["placa"] = cli.vehiculos[0].placa

    if request.method == "POST":
        form = {k: request.form.get(k, "").strip() for k in form}
        error = _crear_reserva(cli, form)
        if error is None:
            return redirect(url_for("agenda.index"))

    return panel("panel/servicio_cliente.html", "Agendar nuevo servicio", "Completa los pasos para agendar tu servicio.",
                 tipos=tipos, empleados=empleados, form=form, error=error, hoy=date.today().isoformat())


def _crear_reserva(cli, f):
    tipo = db.session.get(TipoServicio, int(f["tipo"])) if f["tipo"].isdigit() else None
    if tipo is None or not tipo.activo:
        return "Elige un tipo de servicio."
    if not f["placa"]:
        return "Escribe la placa de tu vehículo."
    try:
        momento = datetime.strptime(f"{f['fecha']} {f['hora']}", "%Y-%m-%d %H:%M")
    except ValueError:
        return "Elige la fecha y la hora de tu cita."
    if momento < datetime.now().replace(second=0, microsecond=0):
        return "La cita no puede ser en una fecha u hora que ya pasó."

    empleado = None
    if f["empleado"]:
        empleado = db.session.get(Empleado, int(f["empleado"])) if f["empleado"].isdigit() else None
        if empleado is None or not empleado.en_operacion:
            nombre = empleado.nombre if empleado else "Ese lavador"
            return f"{nombre} no está operando hoy. Elige otro lavador."

    vehiculo, error = vehiculo_para(cli, f["placa"])
    if error:
        db.session.rollback()
        return error

    # Libre y en operación -> se confirma de una vez. Ocupado pero en operación -> entra en su cola.
    estado = "Confirmada" if (empleado and empleado.estado == "Disponible") else "Pendiente"
    reserva = Reserva(
        id_cliente=cli.id_cliente, id_vehiculo=vehiculo.id_vehiculo, id_tipo_servicio=tipo.id_tipo_servicio,
        id_empleado=empleado.id_empleado if empleado else None, fecha_hora=momento, estado=estado,
    )
    db.session.add(reserva)
    sincronizar_servicio(reserva)
    db.session.commit()

    if empleado is None:
        flash("¡Cita agendada con éxito! Te asignaremos el primer lavador que quede libre.", "ok")
    elif empleado.estado == "Disponible":
        flash(f"¡Listo! {empleado.nombre} aceptó tu cita de inmediato.", "ok")
    else:
        flash(f"Tu cita quedó en la cola de {empleado.nombre}. La iniciará cuando termine su lavado actual.", "info")
    return None
