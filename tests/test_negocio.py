"""CRUD, reservas y el ciclo completo de un lavado (cola -> comisión -> recibo)."""
import re
from datetime import date, timedelta

from conftest import ADMIN, MANANA, Cliente as Nav, texto
from backend.jasshine.models import (
    Comision, Empleado, Preferencia, Recibo, Reserva, Servicio, TipoServicio, Usuario, Vehiculo, db,
)

AYER = (date.today() - timedelta(days=1)).isoformat()
# Equipo de ejemplo: 1 Juan (Disponible) · 2 Santiago (En servicio) · 3 David (Disponible)
#                    4 Maria (Descansando) · 5 Camila (Disponible) · 6 Luis (Inactivo)


def reservar(nav, tipo=1, placa="AAA111", empleado="", fecha=MANANA, hora="10:00"):
    return nav.post("/servicio/", {"tipo": tipo, "placa": placa, "fecha": fecha, "hora": hora, "empleado": empleado})


def nuevo_empleado(admin, nombre="Pedro Lava", email="pedro@jasshine.co", password="clave12345", estado="Disponible"):
    return admin.post("/empleados/nuevo", {"nombre": nombre, "email": email, "telefono": "300", "cargo": "Lavador",
                                           "estado": estado, "password": password})


# ------------------------------------------------------------------ empleados
def test_admin_crea_empleado_que_puede_iniciar_sesion(app, admin):
    assert "Pedro Lava creado" in texto(nuevo_empleado(admin))
    assert "Pedro Lava" in texto(admin.get("/empleados/"))
    emp = Nav(app)
    r = emp.login("pedro@jasshine.co", "clave12345", "empleado")
    t = texto(r)
    assert "Pedro Lava" in t and "Cola de lavados" not in t and "Inicio" in t
    assert emp.get("/usuarios/").status_code == 403            # un empleado no entra a administración


def test_empleado_editar_inactivar_y_eliminar(app, admin):
    nuevo_empleado(admin)
    with app.app_context():
        eid = Empleado.query.filter_by(email="pedro@jasshine.co").one().id_empleado
    assert "ya existe" in texto(nuevo_empleado(admin)).lower()                      # correo repetido
    r = admin.post(f"/empleados/{eid}/editar", {"nombre": "Pedro Lavador", "email": "pedro@jasshine.co", "telefono": "311",
                                                "cargo": "Pulido", "estado": "Inactivo", "password": ""})
    assert "Empleado actualizado" in texto(r)
    with app.app_context():
        e = db.session.get(Empleado, eid)
        assert e.nombre == "Pedro Lavador" and e.usuario.nombre == "Pedro Lavador" and e.usuario.estado == "inactivo"
    assert "inactiva" in texto(Nav(app).login("pedro@jasshine.co", "clave12345", "empleado"))
    admin.post(f"/empleados/{eid}/eliminar")                                          # sin historial: se borra de verdad
    with app.app_context():
        assert db.session.get(Empleado, eid) is None
        assert Usuario.query.filter_by(email="pedro@jasshine.co").first() is None
    assert "no coinciden" in texto(admin.get("/empleados/?q=zzzz")) or "No hay empleados" in texto(admin.get("/empleados/?q=zzzz"))


# ------------------------------------------------------------------- usuarios
def test_usuarios_crud_y_protecciones(app, admin):
    campos = {"nombre": "Carla Mesa", "email": "carla@correo.com", "rol": "cliente", "estado": "activo", "password": "clave12345"}
    assert "Usuario creado" in texto(admin.post("/usuarios/nuevo", campos))
    assert "Ya existe una cuenta" in texto(admin.post("/usuarios/nuevo", campos))
    assert "al menos 8" in texto(admin.post("/usuarios/nuevo", {**campos, "email": "otra@correo.com", "password": "123"}))
    with app.app_context():
        uid = Usuario.query.filter_by(email="carla@correo.com").one().id_usuario
        assert db.session.get(Usuario, uid).cliente is not None

    r = admin.post(f"/usuarios/{uid}/editar", {**campos, "nombre": "Carla M.", "rol": "empleado", "password": ""})
    assert "Usuario actualizado" in texto(r)
    with app.app_context():
        u = db.session.get(Usuario, uid)
        assert u.nombre == "Carla M." and u.rol == "empleado" and u.empleado is not None
    assert "Carla M." in texto(admin.get("/usuarios/?rol=empleado&q=carla"))
    assert "Carla M." not in texto(admin.get("/usuarios/?rol=cliente"))

    assert "Usuario eliminado" in texto(admin.post(f"/usuarios/{uid}/eliminar"))
    with app.app_context():
        assert db.session.get(Usuario, uid) is None

    # el admin no puede borrarse ni quitarse el acceso a sí mismo
    with app.app_context():
        mi_id = Usuario.query.filter_by(email=ADMIN[0]).one().id_usuario
    assert "No puedes eliminar tu propia cuenta" in texto(admin.post(f"/usuarios/{mi_id}/eliminar"))
    r = admin.post(f"/usuarios/{mi_id}/editar", {"nombre": "Admin", "email": ADMIN[0], "rol": "cliente", "estado": "activo", "password": ""})
    assert "No puedes quitarte" in texto(r)


# ------------------------------------------------------------------- catálogo
def test_catalogo_de_servicios_crud(app, admin):
    campos = {"nombre": "Lavado Express", "descripcion": "Rápido", "precio": "5000", "duracion": "10", "activo": "1"}
    assert "agregado al catálogo" in texto(admin.post("/servicio/nuevo", campos))
    assert "Lavado Express" in texto(admin.get("/servicio/"))
    assert "Ya existe un servicio" in texto(admin.post("/servicio/nuevo", campos))
    with app.app_context():
        tid = TipoServicio.query.filter_by(nombre="Lavado Express").one().id_tipo_servicio
    assert "Servicio actualizado" in texto(admin.post(f"/servicio/{tid}/editar", {**campos, "precio": "6500"}))
    with app.app_context():
        assert int(db.session.get(TipoServicio, tid).precio) == 6500
    admin.post(f"/servicio/{tid}/eliminar")
    with app.app_context():
        assert db.session.get(TipoServicio, tid) is None
    # uno que ya se usó no se borra: se oculta
    c = Nav(app); c.registrar("Ana Ruiz", "ana@correo.com"); reservar(c, tipo=1)
    admin.post("/servicio/1/eliminar")
    with app.app_context():
        t = db.session.get(TipoServicio, 1)
        assert t is not None and t.activo is False
    assert "Lavado básico" not in texto(c.get("/servicio/")).split("TIPO DE SERVICIO")[1].split("DATOS DE LA CITA")[0]


# ------------------------------------------------------------------- reservas
def test_reglas_de_reserva_del_cliente(app):
    c = Nav(app); c.registrar("Ana Ruiz", "ana@correo.com")

    assert "aceptó tu cita de inmediato" in texto(reservar(c, placa="AAA111", empleado=1))          # libre
    assert "quedó en la cola de Santiago" in texto(reservar(c, placa="AAA111", empleado=2))          # en servicio
    assert "no está operando" in texto(reservar(c, placa="AAA111", empleado=4))                      # descansando
    assert "no está operando" in texto(reservar(c, placa="AAA111", empleado=6))                      # inactivo
    assert "agendada con éxito" in texto(reservar(c, placa="AAA111", empleado=""))                   # cualquiera
    assert "ya pasó" in texto(reservar(c, placa="AAA111", fecha=AYER))
    assert "Elige un tipo" in texto(c.post("/servicio/", {"tipo": "", "placa": "AAA111", "fecha": MANANA, "hora": "10:00"}))

    with app.app_context():
        rs = Reserva.query.order_by("id_reserva").all()
        assert [(r.id_empleado, r.estado) for r in rs] == [(1, "Confirmada"), (2, "Pendiente"), (None, "Pendiente")]
        assert Servicio.query.count() == 2 and all(s.estado == "En espera" for s in Servicio.query.all())

    # otra persona no puede usar la misma placa
    otro = Nav(app); otro.registrar("Beto Díaz", "beto@correo.com")
    assert "otro cliente" in texto(reservar(otro, placa="aaa111"))

    # cancelar: la cita sale de la cola; una ajena da 403
    with app.app_context():
        rid = Reserva.query.filter_by(id_empleado=1).one().id_reserva
    assert otro.post(f"/agenda/{rid}/cancelar").status_code == 403
    assert "Cita cancelada" in texto(c.post(f"/agenda/{rid}/cancelar"))
    with app.app_context():
        assert db.session.get(Reserva, rid).estado == "Cancelada"
        assert Servicio.query.filter_by(id_reserva=rid).first() is None


def test_agenda_admin_crud(app, admin):
    c = Nav(app); c.registrar("Ana Ruiz", "ana@correo.com")
    base = {"cliente": 1, "placa": "BBB222", "tipo": 2, "empleado": 1, "fecha": MANANA, "hora": "09:00", "estado": "Confirmada"}
    assert "Cita creada" in texto(admin.post("/agenda/nueva", base))
    with app.app_context():
        r = Reserva.query.one(); rid = r.id_reserva
        assert r.servicio is not None and r.servicio.id_empleado == 1
    assert "BBB222" in texto(admin.get("/agenda/"))

    assert "no está operando" in texto(admin.post("/agenda/nueva", {**base, "empleado": 4}))
    admin.post(f"/agenda/{rid}/editar", {**base, "empleado": 3})
    with app.app_context():
        assert db.session.get(Reserva, rid).servicio.id_empleado == 3
    admin.post(f"/agenda/{rid}/editar", {**base, "empleado": 3, "estado": "Cancelada"})
    with app.app_context():
        assert db.session.get(Reserva, rid).servicio is None
    assert "Cita eliminada" in texto(admin.post(f"/agenda/{rid}/eliminar"))
    with app.app_context():
        assert Reserva.query.count() == 0


# ---------------------------------------------------- ciclo completo del lavado
def test_ciclo_completo_cola_comision_recibo(app, admin):
    nuevo_empleado(admin)
    with app.app_context():
        eid = Empleado.query.filter_by(email="pedro@jasshine.co").one().id_empleado
    c = Nav(app); c.registrar("Ana Ruiz", "ana@correo.com")
    assert "aceptó" in texto(reservar(c, tipo=4, placa="AAA111", empleado=eid, hora="09:00"))     # Lavado Full $25.000
    emp = Nav(app); emp.login("pedro@jasshine.co", "clave12345", "empleado")

    # el empleado ve SU cola (y solo la suya)
    t = texto(emp.get("/servicio/"))
    assert "AAA111" in t and "Iniciar lavado" in t and "1 en turno" in t
    assert "AAA111" not in texto(Nav(app).login("juan@jasshine.co", "x", "empleado"))

    # una segunda cita queda en cola y no puede iniciarse mientras hay un lavado en curso
    reservar(c, tipo=1, placa="AAA111", empleado=eid, hora="11:00")
    with app.app_context():
        s1, s2 = [s.id_servicio for s in Servicio.query.order_by("fecha_inicio").all()]
    assert "Lavado iniciado" in texto(emp.post(f"/servicio/{s1}/iniciar"))
    with app.app_context():
        assert db.session.get(Empleado, eid).estado == "En servicio"
    assert "Termina el lavado en curso" in texto(emp.post(f"/servicio/{s2}/iniciar"))
    assert "Marcar finalizado" in texto(emp.get("/servicio/"))

    # no puede tocar el servicio de otro empleado
    assert emp.post("/servicio/99999/iniciar").status_code == 404

    assert "Lavado finalizado" in texto(emp.post(f"/servicio/{s1}/finalizar"))
    with app.app_context():
        s = db.session.get(Servicio, s1)
        assert s.estado == "Completado" and s.fecha_fin is not None and int(s.costo) == 25000
        assert round(float(s.comision.monto), 2) == 4500.00                 # 18 %
        assert int(s.recibo.total) == 25000 and s.recibo.estado == "Pendiente"
        assert s.reserva.estado == "Completada"
        assert db.session.get(Empleado, eid).estado == "Disponible"

    # lo ven las pantallas que antes eran de ejemplo
    assert "$4.500" in texto(emp.get("/recibos/")) and "$4.500" in texto(emp.get("/inicio/"))
    assert "$25.000" in texto(c.get("/recibos/")) and "Pendiente" in texto(c.get("/recibos/"))
    assert "$25.000" in texto(admin.get("/facturacion/")) and "Ana Ruiz" in texto(admin.get("/facturacion/"))
    assert "$25.000" in texto(admin.get("/inicio/"))
    assert "Pedro Lava" in texto(admin.get("/reportes/"))
    assert "$4.500" in texto(admin.get("/comisiones/"))

    # el administrador cobra el recibo y paga la comisión
    with app.app_context():
        rid = Recibo.query.one().id_recibo
    assert "marcado como pagado" in texto(admin.post(f"/facturacion/{rid}/estado", {"accion": "pagar"}))
    assert "ya no está pendiente" in texto(admin.post(f"/facturacion/{rid}/estado", {"accion": "anular"}))
    assert "Pagado" in texto(c.get("/recibos/"))
    assert "Se marcaron 1 comisiones" in texto(admin.post(f"/comisiones/pagar/{eid}"))
    assert "Pagada" in texto(emp.get("/recibos/"))

    # con historial, el empleado no se borra: se inactiva
    assert "quedó Inactivo" in texto(admin.post(f"/empleados/{eid}/eliminar"))
    with app.app_context():
        assert db.session.get(Empleado, eid).estado == "Inactivo"


def test_anular_recibo(app, admin):
    nuevo_empleado(admin)
    with app.app_context():
        eid = Empleado.query.filter_by(email="pedro@jasshine.co").one().id_empleado
    c = Nav(app); c.registrar("Ana Ruiz", "ana@correo.com"); reservar(c, empleado=eid)
    emp = Nav(app); emp.login("pedro@jasshine.co", "clave12345", "empleado")
    with app.app_context():
        sid = Servicio.query.one().id_servicio
    emp.post(f"/servicio/{sid}/iniciar"); emp.post(f"/servicio/{sid}/finalizar")
    with app.app_context():
        rid = Recibo.query.one().id_recibo
    assert "anulado" in texto(admin.post(f"/facturacion/{rid}/estado", {"accion": "anular"}))
    assert "Anulado" in texto(admin.get("/facturacion/"))
    assert "Anulado" in texto(c.get("/recibos/"))


# -------------------------------------------------------------- configuración
def test_configuracion_cliente(app):
    c = Nav(app); c.registrar("Ana Ruiz", "ana@correo.com")
    r = c.post("/configuracion/", {"accion": "perfil", "nombre": "Ana María Ruiz", "email": "ana.maria@correo.com",
                                   "telefono": "3001112233", "moto": "Yamaha MT-03", "placa": "xyz987", "pref_promos": "on"})
    assert "Cambios guardados" in texto(r)
    t = texto(c.get("/inicio/"))
    assert "Hola, Ana" in t
    with app.app_context():
        u = Usuario.query.filter_by(email="ana.maria@correo.com").one()
        assert u.cliente.nombre == "Ana María Ruiz" and u.cliente.telefono == "3001112233"
        v = Vehiculo.query.filter_by(id_cliente=u.cliente.id_cliente).one()
        assert (v.placa, v.tipo) == ("XYZ987", "Yamaha MT-03")
    html = c.get("/configuracion/").get_data(as_text=True)
    caja = lambda n: re.search(rf'<input type="checkbox" class="toggle-input" name="pref_{n}"[^>]*>', html).group(0)
    assert "checked" in caja("promos") and "checked" not in caja("recordatorios")      # se guardó lo marcado
    assert 'value="XYZ987"' in html and 'value="3001112233"' in html

    # correo ajeno / placa ajena
    Nav(app).registrar("Beto Díaz", "beto@correo.com")
    assert "otra cuenta" in texto(c.post("/configuracion/", {"accion": "perfil", "nombre": "Ana", "email": "beto@correo.com"}))
    b = Nav(app); b.login("beto@correo.com", "secreto123", "cliente")
    assert "otro cliente" in texto(b.post("/configuracion/", {"accion": "perfil", "nombre": "Beto", "email": "beto@correo.com", "placa": "XYZ987"}))


def test_cambiar_contrasena_desde_configuracion(app):
    c = Nav(app); c.registrar("Ana Ruiz", "ana@correo.com")
    p = lambda a, n, f: texto(c.post("/configuracion/", {"accion": "password", "actual": a, "nueva": n, "confirmar": f}))
    assert "actual no es correcta" in p("mala", "nuevaClave1", "nuevaClave1")
    assert "no coinciden" in p("secreto123", "nuevaClave1", "otra")
    assert "al menos 8" in p("secreto123", "corta", "corta")
    assert "Contraseña actualizada" in p("secreto123", "nuevaClave1", "nuevaClave1")
    c.logout()
    assert "incorrecta" in texto(c.login("ana@correo.com", "secreto123", "cliente"))
    assert "Hola, Ana" in texto(c.login("ana@correo.com", "nuevaClave1", "cliente"))


def test_configuracion_admin_y_empleado(app, admin):
    r = admin.post("/configuracion/", {"accion": "perfil", "nombre": "Admin Jefe", "email": ADMIN[0],
                                       "neg_nombre": "Mi Lavadero", "neg_correo": "c@x.co", "neg_telefono": "1", "neg_direccion": "Calle 1",
                                       "neg_meta": "1000000", "pref_notif-push": "on"})
    assert "Cambios guardados" in texto(r)
    assert "Mi Lavadero" in texto(admin.get("/configuracion/")) and "$1.000.000" in texto(admin.get("/reportes/"))
    assert "Admin Jefe" in texto(admin.get("/inicio/"))
    nuevo_empleado(admin)
    e = Nav(app); e.login("pedro@jasshine.co", "clave12345", "empleado")
    e.post("/configuracion/", {"accion": "perfil", "nombre": "Pedro Lava", "email": "pedro@jasshine.co", "telefono": "3109998877"})
    with app.app_context():
        assert Empleado.query.filter_by(email="pedro@jasshine.co").one().telefono == "3109998877"
        assert Preferencia.query.filter_by(clave="disponible", valor=False).count() == 1    # lo no marcado queda apagado
