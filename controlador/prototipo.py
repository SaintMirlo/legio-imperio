"""Acceso al escenario de esta aplicación, sin depender de sus datos internos."""
from flask import abort, current_app


def obtener_prototipo():
    return current_app.extensions["prototipo"]


def obtener_legion(id_legion):
    try:
        return obtener_prototipo().legion(id_legion)
    except KeyError:
        abort(404)
