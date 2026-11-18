"""Números, fechas y frases de la bitácora, al estilo chileno: 12.050 y 61,0.

El modelo redacta los sucesos de la bitácora; la vista reutiliza estos formatos como filtros.
"""
from datetime import datetime

# Nombre de cada tipo de unidad en singular y plural, para las frases de la bitácora.
NOMBRES_TROPA = {
    "legionario": ("legionario", "legionarios"),
    "caballeria": ("de caballería", "de caballería"),
    "ballesta": ("ballesta", "ballestas"),
    "ingeniero": ("ingeniero", "ingenieros"),
    "esclavo": ("esclavo", "esclavos"),
}


def ahora():
    """Instante actual en formato ISO, sin microsegundos: 2026-11-17T18:30:05."""
    return datetime.now().isoformat(timespec="seconds")


def dividir_redondeando(numerador, denominador):
    """División entera redondeada al entero más cercano; los ,5 suben.

    Los cálculos del juego usan enteros para que el resultado no dependa de errores de
    coma flotante: 25 × 110 / 100 se calcula como dividir_redondeando(25 * 110, 100).
    """
    return (2 * numerador + denominador) // (2 * denominador)


def miles(numero):
    """12050 -> '12.050'; -2000 -> '−2.000'."""
    numero = int(numero)
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
    """61.0 -> '61,0'; 13750.5 -> '13.750,5'; -2.5 -> '−2,5'."""
    texto = f"{numero:,.{cifras}f}".replace(",", "\0").replace(".", ",").replace("\0", ".")
    return texto.replace("-", "−")


def centesimas(valor_x100):
    """Valor guardado en centésimas, sin redondear: 2993865 -> '29.938,65'; 3156000 -> '31.560'.

    El ATK y la DEF totales se calculan en centésimas; mostrarlos exactos permite comprobar
    a mano que Daño = ATK_TOTAL − DEF_TOTAL.
    """
    enteros, resto = divmod(abs(int(valor_x100)), 100)
    texto = miles(enteros) + (f",{resto:02d}" if resto else "")
    return "−" + texto if valor_x100 < 0 else texto


def fecha(instante):
    """'2026-11-17T18:30:05' -> '17-11-2026 18:30:05'."""
    try:
        return datetime.fromisoformat(instante).strftime("%d-%m-%Y %H:%M:%S")
    except (TypeError, ValueError):
        return instante or "—"


def hora(instante):
    """'2026-11-17T18:30:05' -> '18:30:05'."""
    try:
        return datetime.fromisoformat(instante).strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return instante or "—"


def contar(cantidad, singular, plural):
    """(1, 'legión', 'legiones') -> '1 legión'; (3, ...) -> '3 legiones'."""
    return f"{miles(cantidad)} {singular if cantidad == 1 else plural}"


def cantidad_tropa(tipo, cantidad):
    """('caballeria', 200) -> '200 de caballería'; ('legionario', 1) -> '1 legionario'."""
    return contar(cantidad, *NOMBRES_TROPA[tipo])


def enumerar(partes):
    """['a', 'b', 'c'] -> 'a, b y c'."""
    partes = [p for p in partes if p]
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + " y " + partes[-1]


def tropas_en_texto(cantidades, vacio="ninguna tropa"):
    """{'legionario': 500, 'caballeria': 200} -> '500 legionarios y 200 de caballería'."""
    partes = [cantidad_tropa(tipo, cantidades.get(tipo, 0)) for tipo in NOMBRES_TROPA if cantidades.get(tipo, 0)]
    return enumerar(partes) or vacio
