"""Filtros de las plantillas: números al estilo chileno (12.050 y 61,0), signos y fechas.

Reutilizan los formatos del modelo para que la bitácora y las pantallas escriban igual.
"""
from modelo.textos import centesimas, decimal, fecha, hora, miles, signo


def porcentaje(actual, maximo):
    """Proporción de 0 a 100 para el ancho de las barras; 0 si no hay máximo."""
    if not maximo:
        return 0
    return max(0.0, min(100.0, actual * 100 / maximo))


def entero_o_decimal(numero):
    """61.0 -> '61'; 61.5 -> '61,5' (atributos por unidad)."""
    return miles(numero) if float(numero).is_integer() else decimal(numero)


def registrar_filtros(app):
    for filtro in (miles, signo, decimal, centesimas, porcentaje, fecha, hora, entero_o_decimal):
        app.add_template_filter(filtro)
