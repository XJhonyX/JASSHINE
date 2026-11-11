"""Reglas del negocio: cola del empleado, comisiones y recibos.

Antes vivían repartidas entre servicio-cliente.js, servicio-empleado.js y
agenda-*.js; ahora están en un solo lugar del servidor.
"""
from datetime import datetime

from .models import COMISION_PCT, Comision, Recibo, Reserva, Servicio, Vehiculo, db

ESTADOS_RESERVA = ("Pendiente", "Confirmada", "Completada", "Cancelada")
ESTADOS_EMPLEADO = ("Disponible", "En servicio", "Descansando", "Inactivo")


def vehiculo_para(cliente, placa, tipo="Moto"):
    """Vehículo del cliente con esa placa (se crea si no existe).

    Devuelve (vehiculo, error). La placa es única en todo el sistema.
    """
    placa = (placa or "").strip().upper()
    if not placa:
        return None, "Escribe la placa del vehículo."
    v = Vehiculo.query.filter_by(placa=placa).first()
    if v is not None:
        if v.id_cliente != cliente.id_cliente:
            return None, "Esa placa ya está registrada a nombre de otro cliente."
        return v, None
    v = Vehiculo(id_cliente=cliente.id_cliente, tipo=tipo, placa=placa)
    db.session.add(v)
    db.session.flush()
    return v, None


def sincronizar_servicio(reserva):
    """Mantiene la cola del empleado alineada con la reserva (hace flush)."""
    db.session.flush()
    s = reserva.servicio
    en_cola = reserva.id_empleado and reserva.estado in ("Pendiente", "Confirmada")

    if reserva.estado == "Cancelada" or not reserva.id_empleado:
        if s is not None and s.estado == "En espera":
            db.session.delete(s)
        return

    if en_cola:
        if s is None:
            db.session.add(Servicio(
                id_vehiculo=reserva.id_vehiculo, id_empleado=reserva.id_empleado,
                id_reserva=reserva.id_reserva, id_tipo_servicio=reserva.id_tipo_servicio,
                fecha_inicio=reserva.fecha_hora, costo=reserva.tipo.precio, estado="En espera",
            ))
        elif s.estado == "En espera":
            s.id_vehiculo = reserva.id_vehiculo
            s.id_empleado = reserva.id_empleado
            s.id_tipo_servicio = reserva.id_tipo_servicio
            s.costo = reserva.tipo.precio
            s.fecha_inicio = reserva.fecha_hora


def puede_borrar_reserva(reserva):
    s = reserva.servicio
    return s is None or s.estado == "En espera"


def borrar_reserva(reserva):
    if reserva.servicio is not None:
        db.session.delete(reserva.servicio)
    db.session.delete(reserva)


def iniciar_servicio(servicio):
    """Pasa un lavado de En espera a En curso. Devuelve un mensaje de error o None."""
    if servicio.estado != "En espera":
        return "Ese lavado ya no está en espera."
    en_curso = Servicio.query.filter_by(id_empleado=servicio.id_empleado, estado="En curso").first()
    if en_curso is not None:
        return "Termina el lavado en curso antes de iniciar otro."
    servicio.estado = "En curso"
    servicio.fecha_inicio = datetime.now()
    servicio.empleado.estado = "En servicio"
    if servicio.reserva is not None and servicio.reserva.estado == "Pendiente":
        servicio.reserva.estado = "Confirmada"
    return None


def finalizar_servicio(servicio):
    """Cierra el lavado: calcula tiempo, comisión y recibo. Devuelve error o None."""
    if servicio.estado != "En curso":
        return "Solo se puede finalizar un lavado que está en curso."
    ahora = datetime.now()
    servicio.estado = "Completado"
    servicio.fecha_fin = ahora
    servicio.tiempo_total = max(1, int((ahora - servicio.fecha_inicio).total_seconds() // 60))
    servicio.costo = servicio.tipo.precio
    db.session.add(Comision(
        id_servicio=servicio.id_servicio, id_empleado=servicio.id_empleado,
        monto=round(float(servicio.costo) * COMISION_PCT, 2), fecha_calculo=ahora,
    ))
    db.session.add(Recibo(
        id_servicio=servicio.id_servicio, fecha_emision=ahora, total=servicio.costo, estado="Pendiente",
    ))
    if servicio.reserva is not None:
        servicio.reserva.estado = "Completada"
    db.session.flush()
    quedan = Servicio.query.filter_by(id_empleado=servicio.id_empleado, estado="En curso").count()
    if quedan == 0 and servicio.empleado.estado == "En servicio":
        servicio.empleado.estado = "Disponible"
    return None


def tiene_historial_empleado(emp):
    return (
        Servicio.query.filter_by(id_empleado=emp.id_empleado).first() is not None
        or Reserva.query.filter_by(id_empleado=emp.id_empleado).first() is not None
        or Comision.query.filter_by(id_empleado=emp.id_empleado).first() is not None
    )


def tiene_historial_cliente(cli):
    return Reserva.query.filter_by(id_cliente=cli.id_cliente).first() is not None
