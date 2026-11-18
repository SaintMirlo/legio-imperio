"""Legatus: comandante de una legión (sección 4 del enunciado).

Sus bonificaciones de %ATK y %DEF van de −25% a +25%. El %Costo es su suma y solo afecta
el mantenimiento (sueldos de cada turno), no la contratación de unidades.
"""
from modelo import serializacion as s
from modelo.errores import ReglaInvalida, texto_requerido
from modelo.textos import dividir_redondeando, signo

BONO_MINIMO = -25
BONO_MAXIMO = 25


class Legatus:
    def __init__(self, nombre, bono_atk, bono_def):
        self.nombre = texto_requerido(nombre, "el nombre del Legatus")
        self.bono_atk = self._validar_bono(bono_atk, "ATK")
        self.bono_def = self._validar_bono(bono_def, "DEF")

    @staticmethod
    def _validar_bono(valor, atributo):
        if type(valor) is not int or not BONO_MINIMO <= valor <= BONO_MAXIMO:
            raise ReglaInvalida(f"La bonificación de %{atributo} del Legatus debe estar entre −25% y +25%.")
        return valor

    @property
    def bono_costo(self):
        """%Costo = %ATK + %DEF: más ataque o defensa encarece los sueldos."""
        return self.bono_atk + self.bono_def

    def calcular_bonos(self):
        return {"atk": self.bono_atk, "def": self.bono_def, "costo": self.bono_costo}

    def aplicar_bonos(self, sueldos_base):
        """Sueldos con el %Costo del Legatus aplicado."""
        return dividir_redondeando(sueldos_base * (100 + self.bono_costo), 100)

    def describir(self):
        """'Marco Antonio (+10% ATK, +5% DEF, +15% costo)'."""
        return f"{self.nombre} ({signo(self.bono_atk)} ATK, {signo(self.bono_def)} DEF, {signo(self.bono_costo)} costo)"

    def a_dict(self):
        return {"nombre": self.nombre, "atk": self.bono_atk, "def": self.bono_def}

    @classmethod
    def desde_dict(cls, datos):
        return cls(s.texto(datos, "nombre"), s.entero(datos, "atk"), s.entero(datos, "def"))
