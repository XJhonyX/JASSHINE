"""La cuenta que se registra es la que inicia sesión (ya no hay cuenta fija)."""
from backend.jasshine.models import Cliente, Usuario, db
from conftest import ADMIN, texto


def test_registro_inicia_sesion_con_la_cuenta_nueva(app, nav):
    r = nav.registrar("Laura Gómez Pérez", "laura@correo.com")
    t = texto(r)
    assert "Hola, Laura" in t                 # saludo con SU nombre, no el de una cuenta fija
    assert "Juan Esteban" not in t.split("<main")[1]
    with app.app_context():
        u = Usuario.query.filter_by(email="laura@correo.com").one()
        assert u.rol == "cliente" and u.estado == "activo"
        assert u.contrasena != "secreto123" and u.contrasena.startswith(("scrypt", "pbkdf2"))  # hash, no texto plano
        assert u.cliente is not None and u.cliente.nombre == "Laura Gómez Pérez"


def test_cerrar_sesion_y_volver_a_entrar(nav):
    nav.registrar("Laura Gómez", "laura@correo.com")
    r = nav.logout()
    assert "Iniciar sesión" in texto(r)
    assert "/login" in nav.get("/inicio/").request.path       # sin sesión -> manda al login
    r = nav.login("laura@correo.com", "secreto123", "cliente")
    assert "Hola, Laura" in texto(r)


def test_login_errores(nav):
    nav.registrar("Laura Gómez", "laura@correo.com")
    nav.logout()
    assert "Contraseña incorrecta" in texto(nav.login("laura@correo.com", "mala", "cliente"))
    assert "No existe una cuenta" in texto(nav.login("nadie@correo.com", "secreto123", "cliente"))
    r = nav.login("laura@correo.com", "secreto123", "admin")        # rol equivocado
    assert 'Selecciona "Cliente"' in texto(r)


def test_registro_validaciones(nav):
    assert "al menos 8" in texto(nav.registrar("Ana", "ana@correo.com", "corta"))
    nav.registrar("Ana Ruiz", "ana@correo.com")
    nav.logout()
    assert "Ya existe una cuenta" in texto(nav.registrar("Otra Ana", "ANA@correo.com"))   # sin distinguir mayúsculas


def test_cada_cuenta_ve_solo_lo_suyo(app, nav):
    from backend.jasshine.models import Reserva
    nav.registrar("Ana Ruiz", "ana@correo.com")
    nav.post("/servicio/", {"tipo": 1, "placa": "AAA111", "fecha": __import__("conftest").MANANA, "hora": "10:00", "empleado": ""})
    assert "AAA111" in texto(nav.get("/agenda/"))
    nav.logout()
    nav.registrar("Beto Díaz", "beto@correo.com")
    t = texto(nav.get("/agenda/"))
    assert "AAA111" not in t and "Todavía no tienes citas" in t
    assert "Hola, Beto" in texto(nav.get("/inicio/"))


def test_no_hay_cuenta_fija_el_equipo_de_ejemplo_no_puede_entrar(nav):
    r = nav.login("juan@jasshine.co", "cualquiera", "empleado")
    assert "aún no tiene contraseña" in texto(r)


def test_csrf_obligatorio(nav):
    r = nav.post("/login", {"email": "a@a.com", "password": "x", "rol": "cliente"}, csrf=False)
    assert r.status_code == 400


def test_recuperar_contrasena_completo(nav):
    nav.registrar("Ana Ruiz", "ana@correo.com")
    nav.logout()
    assert "No encontramos" in texto(nav.post("/recuperar", {"accion": "solicitar", "email": "x@x.com"}))
    r = nav.post("/recuperar", {"accion": "solicitar", "email": "ana@correo.com"})
    assert "Revisa tu correo" in texto(r)
    with nav.c.session_transaction() as s:
        codigo = s["rec"]["codigo"]
    assert "no es correcto" in texto(nav.post("/recuperar", {"accion": "verificar", "codigo": "000000" if codigo != "000000" else "111111"}))
    assert "Crea una nueva contraseña" in texto(nav.post("/recuperar", {"accion": "verificar", "codigo": codigo}))
    assert "no coinciden" in texto(nav.post("/recuperar", {"accion": "cambiar", "password": "nuevaClave1", "confirmar": "otra"}))
    assert "Contraseña actualizada" in texto(nav.post("/recuperar", {"accion": "cambiar", "password": "nuevaClave1", "confirmar": "nuevaClave1"}))
    assert "Contraseña incorrecta" in texto(nav.login("ana@correo.com", "secreto123", "cliente"))
    assert "Hola, Ana" in texto(nav.login("ana@correo.com", "nuevaClave1", "cliente"))


def test_permisos_por_rol(nav, admin):
    for url in ["/inicio/", "/empleados/", "/usuarios/", "/comisiones/", "/agenda/", "/servicio/",
                "/facturacion/", "/reportes/", "/configuracion/"]:
        assert admin.get(url).status_code == 200, url
    admin.logout()
    nav.registrar("Ana Ruiz", "ana@correo.com")
    for url in ["/usuarios/", "/comisiones/", "/facturacion/", "/reportes/"]:
        assert nav.get(url).status_code == 403, url
    for url in ["/inicio/", "/agenda/", "/servicio/", "/empleados/", "/recibos/", "/configuracion/"]:
        assert nav.get(url).status_code == 200, url
