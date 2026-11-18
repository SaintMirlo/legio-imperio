"""Errores del dominio y validaciones de los datos que ingresa el usuario."""
from modelo.textos import miles


class ReglaInvalida(ValueError):
    """La acción no cumple una regla del enunciado. El mensaje se muestra al usuario tal cual."""


class ArchivoCampanaInvalido(ValueError):
    """El archivo no contiene una campaña compatible con Legio Imperium."""


def _mayuscula(texto):
    return texto[:1].upper() + texto[1:]


def texto_requerido(valor, que, largo_maximo=60):
    """Limpia espacios repetidos y exige un texto no vacío. que: «el nombre de la legión»."""
    if not isinstance(valor, str) or not valor.strip():
        raise ReglaInvalida(f"Escribe {que}.")
    limpio = " ".join(valor.split())
    if len(limpio) > largo_maximo:
        raise ReglaInvalida(f"{_mayuscula(que)} admite hasta {largo_maximo} caracteres.")
    return limpio


def entero_en_rango(valor, que, minimo, maximo):
    """Exige un entero (no booleano) dentro de [minimo, maximo]."""
    if type(valor) is not int or not minimo <= valor <= maximo:
        raise ReglaInvalida(
            f"{_mayuscula(que)} debe ser un número entero entre {miles(minimo)} y {miles(maximo)}."
        )
    return valor
