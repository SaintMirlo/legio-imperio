"""Formatos de número para las plantillas, al estilo chileno: 12.050 y 61,0."""


def miles(numero):
    """12050 -> '12.050'; -2000 -> '−2.000'."""
    if numero < 0:
        return "−" + miles(-numero)
    return f"{numero:,}".replace(",", ".")


def signo(porcentaje):
    """Bonificación con signo: 10 -> '+10%', -20 -> '−20%', 0 -> '0%'."""
    if porcentaje > 0:
        return f"+{porcentaje}%"
    if porcentaje < 0:
        return f"−{-porcentaje}%"
    return "0%"


def decimal(numero, cifras=1):
    """61.0 -> '61,0'."""
    return f"{numero:.{cifras}f}".replace(".", ",")


def porcentaje(actual, maximo):
    """Proporción de 0 a 100 para el ancho de las barras; 0 si no hay máximo."""
    if not maximo:
        return 0
    return max(0, min(100, actual * 100 / maximo))


def registrar_filtros(app):
    for filtro in (miles, signo, decimal, porcentaje):
        app.add_template_filter(filtro)
