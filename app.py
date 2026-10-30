"""Legio Imperium: prototipo navegable del Hito 2.

Uso: python app.py y abrir http://127.0.0.1:8000
"""
import os
import secrets

from flask import Flask

from controlador import registrar_controladores
from modelo.prototipo import RepositorioPrototipo
from vista import registrar_contexto
from vista.formato import registrar_filtros
from vista.trazabilidad import registrar_trazabilidad


def crear_app(config=None):
    app = Flask(__name__, template_folder="vista/templates", static_folder="vista/static")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("LEGIO_SECRET_KEY") or secrets.token_hex(32),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    if config:
        app.config.update(config)
    # Cada aplicación tiene su escenario; las peticiones no modifican las cifras.
    app.extensions["prototipo"] = RepositorioPrototipo()
    registrar_filtros(app)
    registrar_trazabilidad(app)
    registrar_contexto(app)
    registrar_controladores(app)
    return app


if __name__ == "__main__":
    crear_app().run(host="127.0.0.1", port=8000, debug=True)
