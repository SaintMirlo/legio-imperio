"""Vista (V de MVC): plantillas HTML, estilos, JS de la interfaz y formatos de número."""
from flask import current_app

from modelo.catalogos import CATALOGO, ESTRATEGIAS, ETAPAS, TIPOS_EVENTO, UNIDAD


def registrar_contexto(app):
    # Las macros importadas sin contexto también necesitan los catálogos.
    app.jinja_env.globals.update(
        catalogo=CATALOGO, unidades=UNIDAD, estrategias=ESTRATEGIAS,
        tipos_evento=TIPOS_EVENTO, etapas=ETAPAS,
    )

    @app.context_processor
    def contexto_comun():
        return {
            "campana_actual": current_app.extensions["prototipo"].campana(),
        }
