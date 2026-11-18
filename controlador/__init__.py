"""Controladores (C de MVC): reciben cada acción del usuario, piden al modelo que aplique las
reglas del juego y eligen la vista que responde."""
from urllib.parse import urlsplit

from flask import flash, g, redirect, render_template, request, url_for

from controlador import bitacora, campana, combate, legiones
from controlador.sesion import SinCampana, es_fetch, id_campana_activa, persistencia
from modelo.archivo import prefijo_archivo
from modelo.persistencia import CampanaNoEncontrada
from modelo.serializacion import DatoInvalido


def registrar_controladores(app):
    for modulo in (campana, legiones, combate, bitacora):
        app.register_blueprint(modulo.bp)

    @app.context_processor
    def contexto_comun():
        # La cabecera habilita «Guardar campaña» solo si hay una campaña abierta, y sugiere
        # el nombre del archivo en el diálogo «Guardar como».
        campana = g.get("campana")
        if campana is not None:
            return {"archivo_prefijo": prefijo_archivo(campana.nombre)}
        id_campana = id_campana_activa()
        nombre = persistencia().nombre_campana(id_campana) if id_campana else None
        return {"archivo_prefijo": prefijo_archivo(nombre) if nombre else None}

    @app.errorhandler(SinCampana)
    @app.errorhandler(CampanaNoEncontrada)
    def sin_campana(_error):
        if es_fetch():
            return render_template("error.html", titulo="No hay una campaña abierta",
                                   mensaje="Crea una campaña o carga un archivo para continuar."), 409
        flash("Crea una campaña nueva o carga un archivo de campaña para empezar.", "info")
        return redirect(url_for("campana.inicio"))

    @app.errorhandler(DatoInvalido)
    def base_danada(error):
        app.logger.error("Campaña dañada en la base de datos: %s", error)
        return render_template(
            "error.html", titulo="La campaña guardada está dañada",
            mensaje="La base de datos tiene datos que no cumplen las reglas del juego. Carga un archivo de "
                    "campaña o crea una campaña nueva.",
        ), 500

    @app.errorhandler(404)
    def no_encontrada(_error):
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def archivo_grande(_error):
        limite = app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
        flash(f"El archivo es demasiado grande: elige una campaña de hasta {limite} MB.", "error")
        origen = urlsplit(request.referrer or "")
        mismo_sitio = origen.netloc == request.host and origen.path.startswith("/")
        return redirect(origen.path if mismo_sitio else url_for("campana.inicio"))
