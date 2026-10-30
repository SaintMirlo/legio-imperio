"""Controladores (C de MVC): reciben cada acción del usuario, piden los datos al modelo
y eligen la vista que responde. En el Hito 2 no aplican reglas de negocio: solo
navegan y muestran mensajes simulados."""
from flask import render_template

from controlador import bitacora, campana, combate, legiones


def registrar_controladores(app):
    for modulo in (campana, legiones, combate, bitacora):
        app.register_blueprint(modulo.bp)

    @app.errorhandler(404)
    def no_encontrada(_error):
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def archivo_grande(_error):
        return render_template(
            "error.html", titulo="El archivo es demasiado grande",
            mensaje="Elige una campaña JSON de hasta 1 MB.",
        ), 413
