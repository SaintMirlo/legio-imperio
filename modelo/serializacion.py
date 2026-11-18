"""Lectura estricta de diccionarios al reconstruir el modelo.

La base de datos y los archivos de campaña guardan diccionarios simples. Antes de volver a
crear los objetos se comprueba cada dato: un archivo alterado no debe producir un estado
imposible ni un error interno.
"""
from datetime import datetime

from modelo.catalogos import UNIDADES


class DatoInvalido(ValueError):
    """Un dato guardado no tiene el tipo, el rango o la relación esperados."""


def exigir(condicion, mensaje="dato inválido"):
    if not condicion:
        raise DatoInvalido(mensaje)


def mapa(datos, clave=None):
    valor = datos if clave is None else (datos.get(clave) if isinstance(datos, dict) else None)
    exigir(isinstance(valor, dict), f"{clave or 'dato'} debe ser un objeto")
    return valor


def lista(datos, clave):
    valor = mapa(datos).get(clave)
    exigir(isinstance(valor, list), f"{clave} debe ser una lista")
    return valor


def entero(datos, clave, minimo=None, maximo=None, nulo=False):
    valor = mapa(datos).get(clave)
    if valor is None and nulo:
        return None
    exigir(type(valor) is int, f"{clave} debe ser un entero")
    exigir(minimo is None or valor >= minimo, f"{clave} fuera de rango")
    exigir(maximo is None or valor <= maximo, f"{clave} fuera de rango")
    return valor


def texto(datos, clave, nulo=False, opciones=None):
    valor = mapa(datos).get(clave)
    if valor is None and nulo:
        return None
    exigir(isinstance(valor, str) and valor.strip() != "", f"{clave} debe ser un texto")
    exigir(opciones is None or valor in opciones, f"{clave} tiene un valor desconocido")
    return valor


def instante(datos, clave):
    """Fecha y hora en formato ISO, como la escribe textos.ahora()."""
    valor = texto(datos, clave)
    try:
        datetime.fromisoformat(valor)
    except ValueError:
        raise DatoInvalido(f"{clave} debe ser una fecha ISO") from None
    return valor


def booleano(datos, clave):
    valor = mapa(datos).get(clave)
    exigir(type(valor) is bool, f"{clave} debe ser verdadero o falso")
    return valor


def tropas(datos, clave, tipos=UNIDADES, minimo=0):
    """Cantidades por tipo de unidad: {'legionario': 500, ...} con todos los tipos."""
    valor = mapa(datos, clave)
    exigir(set(valor) == set(tipos), f"{clave} debe indicar cada tipo de unidad")
    return {tipo: entero(valor, tipo, minimo=minimo) for tipo in tipos}
