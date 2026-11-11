"""Comisiones, facturación, reportes y recibos. Antes eran páginas con datos de ejemplo fijos."""
from datetime import date, datetime, time, timedelta

from flask import Blueprint, abort, flash, redirect, request, url_for
from mongoengine import Q

from ..helpers import DIAS, panel
from ..models import Comision, Empleado, Negocio, Recibo, Servicio, Vehiculo, db
from ..security import login_required, roles_requeridos, usuario_actual

comisiones_bp = Blueprint("comisiones", __name__, url_prefix="/comisiones")
facturacion_bp = Blueprint("facturacion", __name__, url_prefix="/facturacion")
reportes_bp = Blueprint("reportes", __name__, url_prefix="/reportes")
recibos_bp = Blueprint("recibos", __name__, url_prefix="/recibos")

MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                "septiembre", "octubre", "noviembre", "diciembre"]


def _inicio_mes():
    return datetime.combine(date.today().replace(day=1), time.min)


def _suma(col, *filtros):
    modelo = next(
        (model for model in db._models if model._fields.get(col.name) is col),
        None,
    )
    if modelo is None:
        raise ValueError(f"No se encontró el modelo para el campo {col.name}.")
    expresion = Q()
    for filtro in filtros:
        expresion &= filtro
    return sum(float(getattr(documento, col.name) or 0)
               for documento in modelo.objects.filter(expresion))


def _nombre_mes():
    h = date.today()
    return f"{MESES_LARGOS[h.month - 1].capitalize()} {h.year}"


# ================================================================ comisiones
@comisiones_bp.route("/")
@roles_requeridos("admin")
def index():
    mes = _inicio_mes()
    filas = []
    for e in Empleado.query.filter(estado__ne="Inactivo").order_by("id_empleado").all():
        cs = Comision.query.filter(id_empleado=e.id_empleado, fecha_calculo__gte=mes).all()
        total = sum(float(c.monto) for c in cs)
        pagado = sum(float(c.monto) for c in cs if c.pagada)
        filas.append({"empleado": e, "lavadas": len(cs), "total": total, "pagado": pagado, "pendiente": total - pagado})
    total_mes = sum(f["total"] for f in filas)
    pendiente = sum(f["pendiente"] for f in filas)
    promedio = total_mes / len(filas) if filas else 0
    return panel("panel/comisiones.html", "Comisiones", "Seguimiento de pagos por empleado",
                 filas=filas, total_mes=total_mes, pendiente=pendiente, promedio=promedio,
                 mes=_nombre_mes(), n_empleados=len(filas))


@comisiones_bp.route("/pagar/<int:eid>", methods=["POST"])
@roles_requeridos("admin")
def pagar(eid):
    n = Comision.query.filter(
        id_empleado=eid, fecha_calculo__gte=_inicio_mes(), pagada=False
    ).update(set__pagada=True)
    db.session.commit()
    flash(f"Se marcaron {n} comisiones como pagadas." if n else "No había comisiones pendientes.", "ok" if n else "info")
    return redirect(url_for("comisiones.index"))


# =============================================================== facturación
@facturacion_bp.route("/")
@roles_requeridos("admin")
def index():
    mes = _inicio_mes()
    recibos = Recibo.query.order_by("-fecha_emision").limit(100).all()
    facturado = _suma(Recibo.total, Q(fecha_emision__gte=mes), Q(estado__ne="Anulado"))
    emitidos = Recibo.query.filter(fecha_emision__gte=mes).count()
    por_cobrar = _suma(Recibo.total, Q(estado="Pendiente"))
    n_por_cobrar = Recibo.query.filter_by(estado="Pendiente").count()
    return panel("panel/facturacion.html", "Facturación", "Recibos e ingresos del negocio",
                 recibos=recibos, facturado=facturado, emitidos=emitidos,
                 por_cobrar=por_cobrar, n_por_cobrar=n_por_cobrar, mes=_nombre_mes())


@facturacion_bp.route("/<int:rid>/estado", methods=["POST"])
@roles_requeridos("admin")
def estado(rid):
    r = db.get_or_404(Recibo, rid)
    accion = request.form.get("accion")
    if r.estado != "Pendiente":
        flash("Ese recibo ya no está pendiente.", "error")
    elif accion == "pagar":
        r.estado = "Pagado"
        flash(f"Recibo #{r.id_recibo} marcado como pagado.", "ok")
    elif accion == "anular":
        r.estado = "Anulado"
        flash(f"Recibo #{r.id_recibo} anulado.", "info")
    else:
        abort(400)
    db.session.commit()
    return redirect(url_for("facturacion.index"))


# ================================================================== reportes
@reportes_bp.route("/")
@roles_requeridos("admin")
def index():
    hoy = date.today()
    dias = []
    for i in range(6, -1, -1):
        d = hoy - timedelta(days=i)
        ini = datetime.combine(d, time.min)
        total = _suma(Recibo.total, Q(fecha_emision__gte=ini),
                      Q(fecha_emision__lt=ini + timedelta(days=1)), Q(estado__ne="Anulado"))
        dias.append({"etiqueta": DIAS[d.weekday()], "total": total})
    maximo = max([d["total"] for d in dias] + [1])
    for d in dias:
        d["pct"] = max(4, round(d["total"] * 100 / maximo)) if d["total"] else 3

    mes = _inicio_mes()
    ingresos_mes = _suma(Recibo.total, Q(fecha_emision__gte=mes), Q(estado__ne="Anulado"))
    negocio = Negocio.query.first()
    meta = float(negocio.meta_mensual) if negocio else 0
    avance = min(100, round(ingresos_mes * 100 / meta)) if meta else 0

    desempeno = []
    for e in Empleado.query.filter(estado__ne="Inactivo").order_by("id_empleado").all():
        total = _suma(Servicio.costo, Q(id_empleado=e.id_empleado), Q(estado="Completado"),
                      Q(fecha_fin__gte=mes))
        desempeno.append({"empleado": e, "total": total})
    desempeno.sort(key=lambda x: -x["total"])
    mx = max([d["total"] for d in desempeno] + [1])
    for d in desempeno:
        d["pct"] = round(d["total"] * 100 / mx)

    return panel("panel/reportes.html", "Reportes", "Desempeño e ingresos de JASSHINE",
                 dias=dias, ingresos_mes=ingresos_mes, meta=meta, avance=avance,
                 faltan=max(0, meta - ingresos_mes), desempeno=desempeno, mes=_nombre_mes())


# =================================================================== recibos
@recibos_bp.route("/")
@login_required
def index():
    u = usuario_actual()
    mes = _inicio_mes()
    if u.rol == "empleado":
        emp = u.empleado
        comisiones = (Comision.query.filter_by(id_empleado=emp.id_empleado)
                      .order_by("-fecha_calculo").limit(100).all())
        total_mes = _suma(Comision.monto, Q(id_empleado=emp.id_empleado), Q(fecha_calculo__gte=mes))
        n_mes = Comision.query.filter(id_empleado=emp.id_empleado, fecha_calculo__gte=mes).count()
        return panel("panel/recibos_empleado.html", "Mis Recibos", "Historial de tus comisiones",
                     comisiones=comisiones, total_mes=total_mes, n_mes=n_mes, mes=_nombre_mes())
    if u.rol != "cliente":
        return redirect(url_for("facturacion.index"))

    cli = u.cliente
    recibos = [
        recibo for recibo in Recibo.query.order_by("-fecha_emision")
        if recibo.servicio is not None
        and recibo.servicio.vehiculo is not None
        and recibo.servicio.vehiculo.id_cliente == cli.id_cliente
    ][:100]
    gastado = sum(float(r.total) for r in recibos if r.estado != "Anulado" and r.fecha_emision >= mes)
    return panel("panel/recibos_cliente.html", "Mis Recibos", "Historial de pagos de tus lavadas",
                 recibos=recibos, gastado=gastado, n=len(recibos), mes=_nombre_mes())
