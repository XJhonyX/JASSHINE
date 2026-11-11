"""Inicio de cada rol (Panel general / Inicio). Reemplaza a los dashboards de ejemplo estáticos."""
from datetime import date, datetime, time, timedelta

from flask import Blueprint
from mongoengine import Q

from ..helpers import DIAS, panel
from ..models import Comision, Empleado, Recibo, Reserva, Servicio, db
from ..security import login_required, usuario_actual

bp = Blueprint("inicio", __name__, url_prefix="/inicio")


def _rango(dia):
    ini = datetime.combine(dia, time.min)
    return ini, ini + timedelta(days=1)


def _suma(columna, *filtros):
    modelo = next(
        (model for model in db._models if model._fields.get(columna.name) is columna),
        None,
    )
    if modelo is None:
        raise ValueError(f"No se encontró el modelo para el campo {columna.name}.")
    expresion = Q()
    for filtro in filtros:
        expresion &= filtro
    query = modelo.objects.filter(expresion)
    return sum(float(getattr(documento, columna.name) or 0) for documento in query)


def _delta(actual, anterior, unidad=""):
    """Texto tipo '↑ 12% vs ayer' / '↑ 3 más que ayer' para las tarjetas."""
    if unidad == "%":
        if anterior <= 0:
            return None
        cambio = round((actual - anterior) * 100 / anterior)
        return f"{'↑' if cambio >= 0 else '↓'} {abs(cambio)}% vs ayer"
    dif = int(actual - anterior)
    if dif == 0:
        return None
    return f"{'↑' if dif > 0 else '↓'} {abs(dif)} {'más' if dif > 0 else 'menos'} que ayer"


@bp.route("/")
@login_required
def index():
    u = usuario_actual()
    return {"admin": _admin, "empleado": _empleado, "cliente": _cliente}[u.rol](u)


def _admin(u):
    hoy, ayer = date.today(), date.today() - timedelta(days=1)
    h_ini, h_fin = _rango(hoy)
    a_ini, a_fin = _rango(ayer)

    ingresos = _suma(Recibo.total, Q(fecha_emision__gte=h_ini), Q(fecha_emision__lt=h_fin),
                     Q(estado__ne="Anulado"))
    ingresos_ayer = _suma(Recibo.total, Q(fecha_emision__gte=a_ini), Q(fecha_emision__lt=a_fin),
                          Q(estado__ne="Anulado"))
    lavados = Servicio.query.filter(
        estado="Completado", fecha_fin__gte=h_ini, fecha_fin__lt=h_fin
    ).count()
    lavados_ayer = Servicio.query.filter(
        estado="Completado", fecha_fin__gte=a_ini, fecha_fin__lt=a_fin
    ).count()
    pendientes = Servicio.query.filter(estado__in=("En espera", "En curso")).count()
    comisiones = _suma(Comision.monto, Q(fecha_calculo__gte=h_ini), Q(fecha_calculo__lt=h_fin))

    filas = []
    for e in Empleado.query.filter(estado__ne="Inactivo").order_by("id_empleado").all():
        motos = Servicio.query.filter(
            id_empleado=e.id_empleado, estado="Completado",
            fecha_fin__gte=h_ini, fecha_fin__lt=h_fin).count()
        com = _suma(Comision.monto, Q(id_empleado=e.id_empleado),
                    Q(fecha_calculo__gte=h_ini), Q(fecha_calculo__lt=h_fin))
        filas.append({"empleado": e, "motos": motos, "comision": com})

    return panel(
        "panel/inicio_admin.html", "Panel general", "Resumen del día en JASSHINE",
        ingresos=ingresos, delta_ingresos=_delta(ingresos, ingresos_ayer, "%"),
        lavados=lavados, delta_lavados=_delta(lavados, lavados_ayer),
        pendientes=pendientes, comisiones=comisiones, filas=filas,
    )


def _empleado(u):
    emp = u.empleado
    hoy = date.today()
    h_ini, h_fin = _rango(hoy)
    mes_ini = datetime.combine(hoy.replace(day=1), time.min)

    completados_hoy = Servicio.query.filter(
        id_empleado=emp.id_empleado, estado="Completado",
        fecha_fin__gte=h_ini, fecha_fin__lt=h_fin)
    motos = completados_hoy.count()
    ingresos = _suma(Servicio.costo, Q(id_empleado=emp.id_empleado), Q(estado="Completado"),
                     Q(fecha_fin__gte=h_ini), Q(fecha_fin__lt=h_fin))
    mes = _suma(Comision.monto, Q(id_empleado=emp.id_empleado), Q(fecha_calculo__gte=mes_ini))

    dias = []
    for i in range(6, -1, -1):
        d = hoy - timedelta(days=i)
        ini, fin = _rango(d)
        total = _suma(Comision.monto, Q(id_empleado=emp.id_empleado),
                      Q(fecha_calculo__gte=ini), Q(fecha_calculo__lt=fin))
        dias.append({"etiqueta": "Hoy" if i == 0 else DIAS[d.weekday()], "total": total})
    maximo = max([d["total"] for d in dias] + [1])
    for d in dias:
        d["pct"] = round(d["total"] * 100 / maximo)

    ultimos = (Servicio.query.filter_by(id_empleado=emp.id_empleado, estado="Completado")
               .order_by("-fecha_fin").limit(5).all())
    return panel(
        "panel/inicio_empleado.html", "Inicio", f"{motos} motos hoy · {_fmt(ingresos)} en ingresos",
        motos=motos, ingresos=ingresos, mes=mes, dias=dias, ultimos=ultimos, emp=emp,
    )


def _fmt(n):
    from ..helpers import cop
    return cop(n)


def _cliente(u):
    cli = u.cliente
    ahora = datetime.now()
    proxima = (Reserva.query.filter(
        id_cliente=cli.id_cliente, estado__in=("Pendiente", "Confirmada"),
        fecha_hora__gte=ahora).order_by("fecha_hora").first())
    mes_ini = datetime.combine(date.today().replace(day=1), time.min)
    usados = Reserva.query.filter(
        id_cliente=cli.id_cliente, estado="Completada", fecha_hora__gte=mes_ini).count()
    libres = Empleado.query.filter_by(estado="Disponible").count()
    return panel(
        "panel/inicio_cliente.html", f"Hola, {u.primer_nombre} 👋", "Gestiona tus servicios de lavado fácilmente.",
        proxima=proxima, usados=usados, libres=libres, hoy=date.today(),
    )
