"""Campaña abierta y utilidades comunes de los controladores.

La sesión del navegador solo guarda el id de la campaña abierta; la campaña se lee de la base
de datos en cada petición. Si la sesión no tiene una campaña válida se abre la última
modificada, para que al volver a la aplicación se continúe donde se dejó.
"""
import re
from contextlib import contextmanager

from flask import current_app, g, request, session

from modelo.catalogos import UNIDAD
from modelo.errores import ReglaInvalida

CLAVE_SESION = "campana_id"


class SinCampana(Exception):
    """No hay una campaña abierta: el usuario debe crear o cargar una."""


def persistencia():
    return current_app.extensions["persistencia"]


def id_campana_activa():
    id_campana = session.get(CLAVE_SESION)
    if id_campana and persistencia().existe(id_campana):
        return id_campana
    id_campana = persistencia().ultima_campana_id()
    if id_campana:
        session[CLAVE_SESION] = id_campana
    else:
        session.pop(CLAVE_SESION, None)
    return id_campana


def abrir_campana(id_campana):
    session[CLAVE_SESION] = id_campana
    g.pop("campana", None)


def campana_actual(requerida=True):
    """La campaña abierta, leída una vez por petición. Lanza SinCampana si no hay."""
    if "campana" not in g:
        id_campana = id_campana_activa()
        g.campana = persistencia().cargar_campana(id_campana) if id_campana else None
    if g.campana is None and requerida:
        raise SinCampana()
    return g.campana


@contextmanager
def modificar_campana():
    """Entrega la campaña abierta para cambiarla y la guarda solo si no hubo errores."""
    id_campana = id_campana_activa()
    if not id_campana:
        raise SinCampana()
    with persistencia().editar(id_campana) as campana:
        yield campana
    g.campana = campana


def es_fetch():
    """La consola pide fragmentos HTML con fetch para no recargar la página."""
    return request.headers.get("X-Requested-With") == "fetch"


def leer_entero(datos, campo, que, defecto=0):
    """Entero de un formulario. Vacío -> defecto (o error si defecto es None)."""
    texto = (datos.get(campo) or "").strip().replace("−", "-")
    if not texto:
        if defecto is None:
            raise ReglaInvalida(f"Indica {que}.")
        return defecto
    if not re.fullmatch(r"[+-]?\d{1,9}", texto):
        raise ReglaInvalida(f"{que[:1].upper()}{que[1:]} debe ser un número entero.")
    return int(texto)


def leer_tropas(datos, tipos, prefijo=""):
    """{tipo: cantidad} desde campos «{prefijo}{tipo}» de un formulario."""
    return {
        tipo: leer_entero(datos, f"{prefijo}{tipo}", f"la cantidad de {UNIDAD[tipo]['plural'].lower()}")
        for tipo in tipos
    }
