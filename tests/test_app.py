"""Pruebas de los flujos principales. Ejecutar con:  python -m pytest -q"""
import re
from datetime import date, timedelta
import uuid

import pytest

from backend.jasshine import create_app
from backend.jasshine.models import Comision, Empleado, Recibo, Reserva, Servicio, Usuario, db

MANANA = (date.today() + timedelta(days=1)).isoformat()


@pytest.fixture()
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "MONGODB_MOCK": True,
        "MONGODB_URI": "mongodb://localhost",
        "MONGODB_DB": f"jasshine_test_{uuid.uuid4().hex}",
    })
    yield app


def token(client):
    with client.session_transaction() as s:
        return s.get("_csrf")


def post(client, url, data=None, **kw):
    """POST con el token CSRF de la sesión actual."""
    if token(client) is None:
        client.get("/login")
    datos = dict(data or {})
    datos["csrf_token"] = token(client)
    return client.post(url, data=datos, **kw)


def texto(resp):
    return resp.get_data(as_text=True)


def login(client, email, password, rol):
    return post(client, "/login", {"email": email, "password": password, "rol": rol})


def registrar(client, nombre="Ana Torres", email="ana@correo.com", password="clave1234"):
    return post(client, "/registro", {"nombre": nombre, "email": email, "password": password})


def admin(app):
    c = app.test_client()
    login(c, "admin@jasshine.co", "Admin12345", "admin")
    return c


def crear_empleado(adm, nombre="Pedro Lavador", email="pedro@jasshine.co", password="pedro12345", estado="Disponible"):
    return post(adm, "/empleados/nuevo", {
        "nombre": nombre, "email": email, "telefono": "3000000000", "cargo": "Lavador",
        "estado": estado, "password": password})


# ------------------------------------------------------------------ públicas
def test_paginas_publicas_cargan(app):
    c = app.test_client()
    for url in ("/", "/login", "/registro", "/recuperar"):
        assert c.get(url).status_code == 200, url


def test_paginas_cargan_javascript_compartido_sin_manejadores_inline(app):
    """Las páginas cargan el JS de interfaz sin mover la lógica del backend al navegador."""
    adm = admin(app)
    cli = app.test_client()
    registrar(cli)
    paginas = [(app.test_client(), u) for u in ("/", "/login", "/registro", "/recuperar", "/pagina-inexistente")]
    paginas += [(adm, u) for u in ("/inicio/", "/empleados/", "/usuarios/", "/comisiones/", "/agenda/",
                                   "/servicio/", "/facturacion/", "/reportes/", "/configuracion/",
                                   "/empleados/nuevo", "/usuarios/nuevo", "/servicio/nuevo", "/agenda/nueva")]
    paginas += [(cli, u) for u in ("/inicio/", "/agenda/", "/servicio/", "/empleados/", "/recibos/", "/configuracion/")]
    for client, url in paginas:
        contenido = texto(client.get(url))
        assert "/static/js/app.js" in contenido, f"{url} no carga el JavaScript compartido"
        assert "onclick=" not in contenido.lower(), f"{url} trae un manejador onclick"

    respuesta = app.test_client().get("/static/js/app.js")
    assert respuesta.status_code == 200
    assert "javascript" in respuesta.mimetype


# ------------------------------------------------------ cuenta nueva = sesión
def test_la_cuenta_registrada_es_la_que_inicia_sesion(app):
    c = app.test_client()
    r = registrar(c, "Ana Torres", "ana@correo.com")
    assert r.status_code == 302
    html = texto(c.get("/inicio/"))
    assert "Hola, Ana" in html
    assert "Juan Esteban Torres" not in html          # ya no existe la identidad fija
    with app.app_context():
        u = Usuario.query.filter_by(email="ana@correo.com").one()
        assert u.rol == "cliente" and u.cliente is not None
        assert u.contrasena and u.contrasena != "clave1234"   # guardada con hash


def test_registro_valida_correo_repetido_y_contrasena_corta(app):
    c = app.test_client()
    registrar(c)
    c2 = app.test_client()
    assert "Ya existe una cuenta" in texto(registrar(c2))
    assert "al menos 8" in texto(registrar(c2, email="otra@correo.com", password="123"))


def test_dos_cuentas_no_se_mezclan(app):
    a, b = app.test_client(), app.test_client()
    registrar(a, "Ana Torres", "ana@correo.com")
    registrar(b, "Beto Ruiz", "beto@correo.com")
    assert "Hola, Ana" in texto(a.get("/inicio/"))
    assert "Hola, Beto" in texto(b.get("/inicio/"))


def test_login_correcto_incorrecto_y_rol_equivocado(app):
    c = app.test_client()
    registrar(c)
    post(c, "/logout")
    otro = app.test_client()
    assert "Contraseña incorrecta" in texto(login(otro, "ana@correo.com", "mala-clave", "cliente"))
    assert "No existe una cuenta" in texto(login(otro, "nadie@correo.com", "x" * 9, "cliente"))
    assert "Esta cuenta es de tipo Cliente" in texto(login(otro, "ana@correo.com", "clave1234", "admin"))
    assert login(otro, "ana@correo.com", "clave1234", "cliente").status_code == 302


def test_cuentas_sin_contrasena_no_pueden_entrar(app):
    c = app.test_client()
    assert "aún no tiene contraseña" in texto(login(c, "juan@jasshine.co", "lo-que-sea1", "empleado"))


def test_logout_cierra_la_sesion(app):
    c = app.test_client()
    registrar(c)
    post(c, "/logout")
    r = c.get("/inicio/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_permisos_por_rol(app):
    anon = app.test_client()
    assert anon.get("/inicio/").status_code == 302
    cli = app.test_client()
    registrar(cli)
    for url in ("/usuarios/", "/comisiones/", "/facturacion/", "/reportes/", "/usuarios/nuevo", "/servicio/nuevo"):
        assert cli.get(url).status_code == 403, url
    assert admin(app).get("/recibos/").status_code == 302   # admin no tiene "Mis recibos"


def test_csrf_rechaza_formularios_sin_token(app):
    c = app.test_client()
    assert c.post("/registro", data={"nombre": "X", "email": "x@x.com", "password": "clave1234"}).status_code == 400


# ------------------------------------------------------------------- empleados
def test_admin_crea_empleado_con_contrasena_y_el_empleado_entra(app):
    adm = admin(app)
    assert crear_empleado(adm).status_code == 302
    emp = app.test_client()
    assert login(emp, "pedro@jasshine.co", "pedro12345", "empleado").status_code == 302
    html = texto(emp.get("/inicio/"))
    assert "Pedro Lavador" in html and "Juan Esteban" not in html.split("Cerrar sesión")[0].split("who-name")[1][:60]


def test_admin_activa_a_un_empleado_de_ejemplo_desde_usuarios(app):
    adm = admin(app)
    with app.app_context():
        uid = Usuario.query.filter_by(email="juan@jasshine.co").one().id_usuario
    assert post(adm, f"/usuarios/{uid}/editar", {
        "nombre": "Juan Esteban", "email": "juan@jasshine.co", "rol": "empleado",
        "estado": "activo", "password": "juan123456"}).status_code == 302
    emp = app.test_client()
    assert login(emp, "juan@jasshine.co", "juan123456", "empleado").status_code == 302


# ------------------------------------------------------------ reserva completa
def reservar(cli, empleado_id="", placa="WPQ 341", tipo=1, hora="10:00"):
    return post(cli, "/servicio/", {"tipo": tipo, "placa": placa, "fecha": MANANA, "hora": hora,
                                    "empleado": empleado_id}, follow_redirects=False)


def test_lavador_libre_confirma_de_una_vez_y_entra_a_su_cola(app):
    adm = admin(app)
    crear_empleado(adm)
    with app.app_context():
        eid = Empleado.query.filter_by(email="pedro@jasshine.co").one().id_empleado
    cli = app.test_client()
    registrar(cli)
    assert reservar(cli, eid).status_code == 302
    with app.app_context():
        r = Reserva.query.one()
        assert r.estado == "Confirmada" and r.id_empleado == eid
        assert r.servicio.estado == "En espera"
    html = texto(cli.get("/agenda/"))
    assert "WPQ 341" in html and "Confirmada" in html


def test_lavador_ocupado_deja_la_cita_en_cola(app):
    cli = app.test_client()
    registrar(cli)
    with app.app_context():
        santiago = Empleado.query.filter_by(email="santiago@jasshine.co").one()
        assert santiago.estado == "En servicio"
        sid = santiago.id_empleado
    reservar(cli, sid)
    with app.app_context():
        r = Reserva.query.one()
        assert r.estado == "Pendiente" and r.servicio.estado == "En espera"


def test_no_se_puede_elegir_lavador_que_no_opera(app):
    cli = app.test_client()
    registrar(cli)
    with app.app_context():
        maria = Empleado.query.filter_by(email="maria@jasshine.co").one().id_empleado   # Descansando
    r = reservar(cli, maria)
    assert r.status_code == 200 and "no está operando" in texto(r)
    with app.app_context():
        assert Reserva.query.count() == 0


def test_cliente_sin_lavador_queda_pendiente_sin_cola(app):
    cli = app.test_client()
    registrar(cli)
    reservar(cli, "")
    with app.app_context():
        r = Reserva.query.one()
        assert r.estado == "Pendiente" and r.id_empleado is None and r.servicio is None


def test_validaciones_de_la_reserva(app):
    cli = app.test_client()
    registrar(cli)
    assert "placa" in texto(post(cli, "/servicio/", {"tipo": 1, "placa": "", "fecha": MANANA, "hora": "10:00"}))
    ayer = (date.today() - timedelta(days=1)).isoformat()
    assert "ya pasó" in texto(post(cli, "/servicio/", {"tipo": 1, "placa": "AAA111", "fecha": ayer, "hora": "10:00"}))
    assert "tipo de servicio" in texto(post(cli, "/servicio/", {"placa": "AAA111", "fecha": MANANA, "hora": "10:00"}))


def test_una_placa_no_se_comparte_entre_clientes(app):
    a, b = app.test_client(), app.test_client()
    registrar(a, "Ana", "ana@correo.com")
    registrar(b, "Beto", "beto@correo.com")
    reservar(a, "", placa="ZZZ999")
    assert "otro cliente" in texto(reservar(b, "", placa="ZZZ999"))


def test_cada_cliente_solo_ve_sus_citas_y_puede_cancelar(app):
    a, b = app.test_client(), app.test_client()
    registrar(a, "Ana", "ana@correo.com")
    registrar(b, "Beto", "beto@correo.com")
    reservar(a, "", placa="AAA111")
    assert "AAA111" in texto(a.get("/agenda/")) and "AAA111" not in texto(b.get("/agenda/"))
    with app.app_context():
        rid = Reserva.query.one().id_reserva
    assert post(b, f"/agenda/{rid}/cancelar").status_code == 403       # no es suya
    post(a, f"/agenda/{rid}/cancelar")
    with app.app_context():
        assert Reserva.query.one().estado == "Cancelada"


def test_flujo_completo_lavado_comision_y_recibo(app):
    adm = admin(app)
    crear_empleado(adm)
    emp = app.test_client()
    login(emp, "pedro@jasshine.co", "pedro12345", "empleado")
    with app.app_context():
        eid = Empleado.query.filter_by(email="pedro@jasshine.co").one().id_empleado
    cli = app.test_client()
    registrar(cli)
    reservar(cli, eid, tipo=2)                                    # Lavado completo $15.000

    assert "WPQ 341" in texto(emp.get("/servicio/"))              # llegó a su cola
    with app.app_context():
        sid = Servicio.query.one().id_servicio
    post(emp, f"/servicio/{sid}/iniciar")
    with app.app_context():
        assert db.session.get(Empleado, eid).estado == "En servicio"
    post(emp, f"/servicio/{sid}/finalizar")

    with app.app_context():
        s = Servicio.query.one()
        assert s.estado == "Completado" and float(s.costo) == 15000
        assert float(Comision.query.one().monto) == 2700          # 18 % de 15.000
        assert float(Recibo.query.one().total) == 15000
        assert s.reserva.estado == "Completada"
        assert db.session.get(Empleado, eid).estado == "Disponible"     # quedó libre otra vez

    assert "$2.700" in texto(emp.get("/recibos/"))                # comisión del empleado
    assert "$15.000" in texto(cli.get("/recibos/"))               # recibo del cliente
    html = texto(adm.get("/facturacion/"))
    assert "$15.000" in html and "Pendiente" in html
    post(adm, "/facturacion/1/estado", {"accion": "pagar"})
    assert "Pagado" in texto(adm.get("/facturacion/"))
    assert "$15.000" in texto(adm.get("/inicio/"))                # ingresos de hoy
    assert "$2.700" in texto(adm.get("/comisiones/"))
    post(adm, f"/comisiones/pagar/{eid}")
    assert "Pagado" in texto(adm.get("/comisiones/"))


def test_un_empleado_solo_toca_sus_servicios(app):
    adm = admin(app)
    crear_empleado(adm)
    crear_empleado(adm, "Otro Lavador", "otro@jasshine.co", "otro12345")
    e1, e2 = app.test_client(), app.test_client()
    login(e1, "pedro@jasshine.co", "pedro12345", "empleado")
    login(e2, "otro@jasshine.co", "otro12345", "empleado")
    with app.app_context():
        eid = Empleado.query.filter_by(email="pedro@jasshine.co").one().id_empleado
    cli = app.test_client()
    registrar(cli)
    reservar(cli, eid)
    with app.app_context():
        sid = Servicio.query.one().id_servicio
    assert post(e2, f"/servicio/{sid}/iniciar").status_code == 403


# ------------------------------------------------------------------------ CRUD
def test_crud_de_usuarios(app):
    adm = admin(app)
    assert post(adm, "/usuarios/nuevo", {"nombre": "Lola Mora", "email": "lola@correo.com", "rol": "cliente",
                                         "estado": "activo", "password": "lola123456"}).status_code == 302
    with app.app_context():
        uid = Usuario.query.filter_by(email="lola@correo.com").one().id_usuario
    assert "Lola Mora" in texto(adm.get("/usuarios/?q=lola"))
    post(adm, f"/usuarios/{uid}/editar", {"nombre": "Lola M.", "email": "lola@correo.com", "rol": "cliente",
                                          "estado": "suspendida", "password": ""})
    with app.app_context():
        u = db.session.get(Usuario, uid)
        assert u.nombre == "Lola M." and u.estado == "suspendida"
    assert "Esta cuenta" not in texto(adm.get(f"/usuarios/{uid}/eliminar"))
    post(adm, f"/usuarios/{uid}/eliminar")
    with app.app_context():
        assert db.session.get(Usuario, uid) is None


def test_el_admin_no_puede_borrarse_ni_quitarse_el_rol(app):
    adm = admin(app)
    assert "No puedes eliminar tu propia cuenta" in texto(adm.get("/usuarios/1/eliminar", follow_redirects=True))
    r = post(adm, "/usuarios/1/editar", {"nombre": "Admin", "email": "admin@jasshine.co", "rol": "cliente",
                                         "estado": "activo", "password": ""})
    assert "No puedes quitarte" in texto(r)


def test_usuario_con_historial_se_inactiva_en_vez_de_borrarse(app):
    cli = app.test_client()
    registrar(cli)
    reservar(cli, "")
    adm = admin(app)
    with app.app_context():
        uid = Usuario.query.filter_by(email="ana@correo.com").one().id_usuario
    post(adm, f"/usuarios/{uid}/eliminar")
    with app.app_context():
        assert db.session.get(Usuario, uid).estado == "inactivo"
    assert "inactiva" in texto(login(app.test_client(), "ana@correo.com", "clave1234", "cliente")).lower()


def test_crud_del_catalogo_de_servicios(app):
    adm = admin(app)
    post(adm, "/servicio/nuevo", {"nombre": "Lavado Express", "descripcion": "Rápido", "precio": "5000",
                                  "duracion": "10", "activo": "1"})
    assert "Lavado Express" in texto(adm.get("/servicio/"))
    assert "Ya existe" in texto(post(adm, "/servicio/nuevo", {"nombre": "lavado express", "precio": "1",
                                                              "duracion": "1", "activo": "1"}))
    cli = app.test_client()
    registrar(cli)
    assert "Lavado Express" in texto(cli.get("/servicio/"))
    post(adm, "/servicio/5/editar", {"nombre": "Lavado Express", "descripcion": "", "precio": "6000",
                                     "duracion": "10", "activo": "0"})
    assert "Lavado Express" not in texto(cli.get("/servicio/"))     # oculto para clientes
    post(adm, "/servicio/5/eliminar")
    assert "Lavado Express" not in texto(adm.get("/servicio/"))


def test_agenda_de_admin_crea_y_asigna_cola(app):
    adm = admin(app)
    cli = app.test_client()
    registrar(cli)
    with app.app_context():
        from backend.jasshine.models import Cliente
        cid = Cliente.query.one().id_cliente
        eid = Empleado.query.filter_by(email="david@jasshine.co").one().id_empleado
    assert post(adm, "/agenda/nueva", {"cliente": cid, "placa": "MNO456", "tipo": 1, "empleado": eid,
                                       "fecha": MANANA, "hora": "09:30", "estado": "Confirmada"}).status_code == 302
    with app.app_context():
        r = Reserva.query.one()
        assert r.servicio is not None and r.servicio.id_empleado == eid
    post(adm, f"/agenda/{r.id_reserva}/eliminar") if False else None


# --------------------------------------------------------- configuración/clave
def test_configuracion_guarda_perfil_y_preferencias(app):
    c = app.test_client()
    registrar(c)
    post(c, "/configuracion/", {"accion": "perfil", "nombre": "Ana María Torres", "email": "ana@correo.com",
                                "telefono": "3001112233", "moto": "Yamaha MT-03", "placa": "WPQ341",
                                "pref_promos": "on"})
    html = texto(c.get("/configuracion/"))
    assert "Ana María Torres" in html and "3001112233" in html and "WPQ341" in html
    assert re.search(r'name="pref_promos"[^>]*checked', html)
    assert not re.search(r'name="pref_recordatorios"[^>]*checked', html)   # desmarcada
    assert "Hola, Ana" in texto(c.get("/inicio/"))


def test_cambiar_contrasena_desde_configuracion(app):
    c = app.test_client()
    registrar(c)
    assert "no es correcta" in texto(post(c, "/configuracion/", {"accion": "password", "actual": "mala",
                                                                 "nueva": "nueva12345", "confirmar": "nueva12345"}))
    post(c, "/configuracion/", {"accion": "password", "actual": "clave1234", "nueva": "nueva12345",
                                "confirmar": "nueva12345"})
    post(c, "/logout")
    assert login(app.test_client(), "ana@correo.com", "nueva12345", "cliente").status_code == 302


def test_recuperar_contrasena_en_tres_pasos(app):
    c = app.test_client()
    registrar(c)
    post(c, "/logout")
    r = app.test_client()
    assert "No encontramos" in texto(post(r, "/recuperar", {"accion": "solicitar", "email": "nadie@x.com"}))
    post(r, "/recuperar", {"accion": "solicitar", "email": "ana@correo.com"})
    with r.session_transaction() as s:
        codigo = s["rec"]["codigo"]
    assert "no es correcto" in texto(post(r, "/recuperar", {"accion": "verificar", "codigo": "000000" if codigo != "000000" else "111111"}))
    post(r, "/recuperar", {"accion": "verificar", "codigo": codigo})
    assert "no coinciden" in texto(post(r, "/recuperar", {"accion": "cambiar", "password": "nueva12345", "confirmar": "otra12345"}))
    assert "Contraseña actualizada" in texto(post(r, "/recuperar", {"accion": "cambiar", "password": "nueva12345", "confirmar": "nueva12345"}))
    assert login(app.test_client(), "ana@correo.com", "nueva12345", "cliente").status_code == 302
    assert login(app.test_client(), "ana@correo.com", "clave1234", "cliente").status_code == 200   # la vieja ya no sirve


def test_reportes_y_dashboards_cargan_vacios_y_con_datos(app):
    adm = admin(app)
    for url in ("/inicio/", "/reportes/", "/comisiones/", "/facturacion/", "/agenda/", "/servicio/", "/empleados/", "/usuarios/"):
        assert adm.get(url).status_code == 200, url
