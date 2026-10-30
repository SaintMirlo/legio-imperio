"""Legio Imperium: prototipo navegable del Hito 2.

Uso: python app.py y abrir http://127.0.0.1:8000
"""
import secrets

from flask import Flask

from controlador import registrar_controladores
from vista.formato import registrar_filtros
from vista.trazabilidad import registrar_trazabilidad


def crear_app():
    app = Flask(__name__, template_folder="vista/templates", static_folder="vista/static")
    # Firma la cookie de los mensajes flash; el prototipo no guarda datos de sesión.
    app.secret_key = secrets.token_hex(16)
    registrar_filtros(app)
    registrar_trazabilidad(app)
    registrar_controladores(app)
    return app


if __name__ == "__main__":
    crear_app().run(host="127.0.0.1", port=8000, debug=True)
