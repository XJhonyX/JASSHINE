"""Módulos del sistema (uno por apartado, igual que las carpetas de views/ del proyecto original)."""


def registrar_modulos(app):
    from . import public, auth, inicio, agenda, empleados, usuarios, servicio, finanzas, configuracion

    for bp in (
        public.bp, auth.bp, inicio.bp, agenda.bp, empleados.bp, usuarios.bp, servicio.bp,
        finanzas.comisiones_bp, finanzas.facturacion_bp, finanzas.reportes_bp, finanzas.recibos_bp,
        configuracion.bp,
    ):
        app.register_blueprint(bp)
