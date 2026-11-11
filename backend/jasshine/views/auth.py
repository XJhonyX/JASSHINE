"""Login, registro, recuperación de contraseña y cierre de sesión.

Reemplaza js/login.js, js/registro.js y js/recuperar.js: ahora las cuentas se
guardan en la base de datos y la cuenta que se registra es la que inicia sesión.
"""
import secrets

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..models import ROL_LABEL, ROLES, Usuario, db
from ..security import (
    cerrar_sesion, crear_usuario, email_ocupado, hash_password, iniciar_sesion,
    normalizar_email, usuario_actual, validar_password, verificar_password,
)

bp = Blueprint("auth", __name__)

MAX_INTENTOS_CODIGO = 5


@bp.route("/login", methods=["GET", "POST"])
def login():
    if usuario_actual():
        return redirect(url_for("inicio.index"))

    email, rol, error = "", "cliente", None
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        rol = request.form.get("rol", "cliente")
        if rol not in ROLES:
            rol = "cliente"

        usuario = Usuario.query.filter(email__iexact=normalizar_email(email)).first()
        if usuario is None:
            error = "No existe una cuenta con ese correo."
        elif not usuario.contrasena:
            error = "Esta cuenta aún no tiene contraseña. Pídele al administrador que la active."
        elif not verificar_password(usuario, password):
            error = "Contraseña incorrecta."
        elif usuario.estado != "activo":
            error = "Tu cuenta está inactiva o suspendida."
        elif usuario.rol != rol:
            error = (f'Esta cuenta es de tipo {ROL_LABEL[usuario.rol]}. '
                     f'Selecciona "{ROL_LABEL[usuario.rol]}" para ingresar.')
        else:
            iniciar_sesion(usuario)
            return redirect(url_for("inicio.index"))

    return render_template("auth/login.html", email=email, rol=rol, error=error)


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    if usuario_actual():
        return redirect(url_for("inicio.index"))

    nombre, email, error = "", "", None
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        if not nombre:
            error = "Escribe tu nombre completo."
        elif email_ocupado(email):
            error = "Ya existe una cuenta con ese correo."
        else:
            error = validar_password(password)
        if error is None:
            # La cuenta que se crea aquí es la que queda con la sesión iniciada.
            usuario = crear_usuario(nombre, email, password, "cliente")
            db.session.commit()
            iniciar_sesion(usuario)
            flash(f"¡Bienvenido, {usuario.primer_nombre}! Tu cuenta fue creada.", "ok")
            return redirect(url_for("inicio.index"))

    return render_template("auth/registro.html", nombre=nombre, email=email, error=error)


@bp.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    """Pasos: 1 correo -> 2 código -> 3 nueva contraseña -> 4 listo."""
    if request.args.get("reiniciar"):
        session.pop("rec", None)
        return redirect(url_for("auth.recuperar"))

    rec = session.get("rec", {})
    error, paso = None, 1
    if rec.get("ok"):
        paso = 3
    elif rec.get("codigo"):
        paso = 2

    if request.method == "POST":
        accion = request.form.get("accion")

        if accion == "solicitar":
            email = request.form.get("email", "")
            usuario = Usuario.query.filter(email__iexact=normalizar_email(email)).first()
            if usuario is None:
                error = "No encontramos una cuenta con ese correo."
            else:
                codigo = f"{secrets.randbelow(10 ** 6):06d}"
                session["rec"] = {"uid": usuario.id_usuario, "email": usuario.email, "codigo": codigo, "intentos": 0}
                # No hay servidor de correo en el prototipo: el código se muestra en pantalla.
                flash(f"Código de verificación (demo, normalmente llegaría por correo): {codigo}", "info")
                return redirect(url_for("auth.recuperar"))

        elif accion == "verificar" and rec.get("codigo"):
            rec["intentos"] = rec.get("intentos", 0) + 1
            if rec["intentos"] > MAX_INTENTOS_CODIGO:
                session.pop("rec", None)
                flash("Demasiados intentos. Solicita un código nuevo.", "error")
                return redirect(url_for("auth.recuperar"))
            if secrets.compare_digest(request.form.get("codigo", "").strip(), rec["codigo"]):
                rec["ok"] = True
                session["rec"] = rec
                return redirect(url_for("auth.recuperar"))
            session["rec"] = rec
            error, paso = "El código no es correcto.", 2

        elif accion == "cambiar" and rec.get("ok"):
            nueva = request.form.get("password", "")
            confirmar = request.form.get("confirmar", "")
            error = validar_password(nueva)
            if error is None and nueva != confirmar:
                error = "Las contraseñas no coinciden."
            if error is None:
                usuario = db.session.get(Usuario, rec["uid"])
                usuario.contrasena = hash_password(nueva)
                db.session.commit()
                session.pop("rec", None)
                return render_template("auth/recuperar.html", paso=4, error=None, email=usuario.email)
            paso = 3

    return render_template("auth/recuperar.html", paso=paso, error=error, email=rec.get("email", ""))


@bp.route("/logout", methods=["POST"])
def logout():
    cerrar_sesion()
    return redirect(url_for("public.index"))
