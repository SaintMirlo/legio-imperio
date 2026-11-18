"""Legio Imperium: gestión táctica y simulación de batallas del ejército romano (Hito 3).

Uso:  python app.py  y abrir http://127.0.0.1:8000

Arquitectura MVC: modelo/ (reglas del juego y persistencia), vista/ (plantillas, estilos y
JavaScript) y controlador/ (rutas de Flask). La base de datos SQLite se crea sola en
instance/legio_imperium.db; la variable de entorno LEGIO_DB permite usar otra ruta.
"""
import os
import secrets

from flask import Flask

from controlador import registrar_controladores
from modelo.persistencia import GestorPersistencia
from vista import registrar_vista


def _clave_secreta(carpeta):
    """Clave de las sesiones, guardada en instance/ para que sobreviva a los reinicios."""
    ruta = os.path.join(carpeta, "clave_secreta.txt")
    try:
        with open(ruta, encoding="ascii") as archivo:
            clave = archivo.read().strip()
        if len(clave) >= 32:
            return clave
    except OSError:
        pass
    clave = secrets.token_hex(32)
    try:
        os.makedirs(carpeta, exist_ok=True)
        with open(ruta, "w", encoding="ascii") as archivo:
            archivo.write(clave)
    except OSError:
        pass
    return clave


def crear_app(config=None):
    app = Flask(__name__, template_folder="vista/templates", static_folder="vista/static",
                instance_relative_config=True)
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,  # archivos de campaña de hasta 8 MB
        DATABASE=os.environ.get("LEGIO_DB") or os.path.join(app.instance_path, "legio_imperium.db"),
    )
    if config:
        app.config.update(config)
    os.makedirs(os.path.dirname(os.path.abspath(app.config["DATABASE"])), exist_ok=True)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.environ.get("LEGIO_SECRET_KEY") or _clave_secreta(app.instance_path)
    app.extensions["persistencia"] = GestorPersistencia(app.config["DATABASE"])
    registrar_vista(app)
    registrar_controladores(app)
    return app


if __name__ == "__main__":
    crear_app().run(host="127.0.0.1", port=8000, debug=True)
