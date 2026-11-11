"""Ayudas compartidas: formato de moneda/fechas y render de las páginas del panel."""
from flask import render_template, request

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# Colores de las insignias (clases .badge.<color> del CSS)
BADGE_EMPLEADO = {"Disponible": "green", "En servicio": "blue", "Descansando": "orange", "Inactivo": "red"}
BADGE_RESERVA = {"Pendiente": "orange", "Confirmada": "blue", "Completada": "green", "Cancelada": "red"}
BADGE_RECIBO = {"Pagado": "green", "Pendiente": "orange", "Anulado": "red"}
BADGE_USUARIO = {"activo": "green", "inactivo": "red", "suspendida": "red"}
BADGE_ROL = {"admin": "purple", "empleado": "blue", "cliente": "orange"}


def cop(valor):
    """1850000 -> $1.850.000"""
    try:
        n = int(round(float(valor or 0)))
    except (TypeError, ValueError):
        n = 0
    return "$" + f"{n:,}".replace(",", ".")


def fecha(dt):
    return dt.strftime("%d/%m/%Y") if dt else "—"


def hora(dt):
    return dt.strftime("%H:%M") if dt else "—"


def fecha_hora(dt):
    return dt.strftime("%d/%m/%Y %H:%M") if dt else "—"


def dia_corto(dt):
    return f"{dt.day:02d}"


def mes_corto(dt):
    return MESES[dt.month - 1]


def iniciales(nombre):
    return "".join(p[0].upper() for p in (nombre or "").split()[:2])


def registrar_filtros(app):
    app.jinja_env.filters.update(
        cop=cop, fecha=fecha, hora=hora, fecha_hora=fecha_hora,
        dia_corto=dia_corto, mes_corto=mes_corto, iniciales=iniciales,
    )
    app.jinja_env.globals.update(
        BADGE_EMPLEADO=BADGE_EMPLEADO, BADGE_RESERVA=BADGE_RESERVA, BADGE_RECIBO=BADGE_RECIBO,
        BADGE_USUARIO=BADGE_USUARIO, BADGE_ROL=BADGE_ROL,
    )


def panel(plantilla, titulo, sub="", **contexto):
    """Renderiza una página del panel dentro del marco (sidebar + topbar) del rol."""
    return render_template(plantilla, titulo=titulo, sub=sub, **contexto)


def pagina_form(titulo, sub, campos, accion, volver, boton="Guardar", error=None):
    """Página con un formulario de crear/editar (reemplaza a los modales de crud-ui.js).

    campos: lista de dicts {name, label, type, value, options, required, hint, placeholder}
    """
    if request.method == "POST":  # conserva lo que el usuario escribió (menos contraseñas)
        for c in campos:
            if c["type"] != "password" and c["name"] in request.form:
                c["value"] = request.form[c["name"]]
    return render_template(
        "panel/form.html", titulo=titulo, sub=sub, campos=campos,
        accion=accion, volver=volver, boton=boton, error=error,
    )


def pagina_confirmar(titulo, mensaje, accion, volver, boton="Eliminar"):
    """Página de confirmación antes de borrar (reemplaza a confirmDeleteModal)."""
    return render_template(
        "panel/confirmar.html", titulo=titulo, sub="", mensaje=mensaje,
        accion=accion, volver=volver, boton=boton,
    )


def campo(name, label, type="text", value="", options=None, required=True, hint=None, placeholder=None, **extra):
    """Describe un campo de formulario para la plantilla panel/form.html."""
    d = {"name": name, "label": label, "type": type, "value": value, "options": options,
         "required": required, "hint": hint, "placeholder": placeholder}
    d.update(extra)
    return d
