"""Controladores (C de MVC): reciben cada acción del usuario, piden los datos al modelo
y eligen la vista que responde. En el Hito 2 no aplican reglas de negocio: solo
navegan y muestran mensajes simulados."""
from flask import render_template

from controlador import bitacora, campana, combate, legiones
from modelo import datos_prototipo as datos


def registrar_controladores(app):
    for modulo in (campana, legiones, combate, bitacora):
        app.register_blueprint(modulo.bp)

    # Catálogos que usan casi todas las vistas.
    app.jinja_env.globals.update(
        campana_actual=datos.CAMPANA,
        catalogo=datos.CATALOGO,
        unidades=datos.UNIDAD,
        estrategias=datos.ESTRATEGIAS,
        tipos_evento=datos.TIPOS_EVENTO,
        etapas=datos.ETAPAS,
    )

    @app.errorhandler(404)
    def no_encontrada(_error):
        return render_template("404.html"), 404
