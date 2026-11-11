"""Datos iniciales (se cargan solo si la base está vacía).

Cuenta inicial para entrar al panel de administración:
    correo:      admin@jasshine.co
    contraseña:  Admin12345      (cámbiala en Gestión de usuarios)

El equipo de ejemplo se crea SIN contraseña: el administrador se la asigna
desde Gestión de usuarios (o crea empleados nuevos con contraseña).
"""
from .models import Negocio, TipoServicio, Usuario, db
from .security import crear_usuario

ADMIN_EMAIL = "admin@jasshine.co"
ADMIN_PASSWORD = "Admin12345"

TIPOS = [
    ("Lavado básico", "Exterior completo", 8000, 20),
    ("Lavado completo", "Exterior + interior", 15000, 35),
    ("Lavado + Pulido", "Brillo de todas las piezas", 22000, 55),
    ("Lavado Full", "Interior, exterior y pulida", 25000, 70),
]

EQUIPO = [
    ("Juan Esteban", "juan@jasshine.co", "+57 311 234 5678", "Lavador senior", "Disponible", "activo"),
    ("Santiago Ariza", "santiago@jasshine.co", "+57 300 456 7812", "Lavador", "En servicio", "activo"),
    ("David Andrade", "david@jasshine.co", "+57 315 908 2231", "Lavador", "Disponible", "activo"),
    ("Maria Alejandra", "maria@jasshine.co", "+57 320 118 4470", "Lavadora senior", "Descansando", "activo"),
    ("Camila Rojas", "camila@jasshine.co", "+57 301 774 9902", "Pulido y detallado", "Disponible", "activo"),
    ("Luis Peña", "luis@jasshine.co", "+57 312 665 3390", "Lavador", "Inactivo", "inactivo"),
]


def sembrar_si_vacia():
    if Usuario.query.first() is not None:
        return False

    crear_usuario("Admin Principal", ADMIN_EMAIL, ADMIN_PASSWORD, "admin")

    for nombre, descripcion, precio, minutos in TIPOS:
        db.session.add(TipoServicio(nombre=nombre, descripcion=descripcion, precio=precio, duracion_min=minutos))

    for nombre, email, telefono, cargo, estado, estado_cuenta in EQUIPO:
        u = crear_usuario(nombre, email, "", "empleado", estado=estado_cuenta)
        emp = u.empleado
        emp.telefono, emp.especialidad, emp.estado = telefono, cargo, estado

    db.session.add(Negocio(
        nombre="JASSHINE — Lavadero Inteligente", correo="contacto@jasshine.co",
        telefono="+57 311 234 5678", direccion="Cra 45 #12-30, Bogotá", meta_mensual=5720000,
    ))
    db.session.commit()
    return True
