"""Estrategias tácticas (tabla 3 del enunciado): Triplex Acies, Cuneus y Orbis.

Cada formación modifica el %ATK y el %DEF de toda la legión y agrega su sinergia. Antes de
usarla se valida la composición: Cuneus requiere caballería y Orbis, legionarios.
"""
from dataclasses import dataclass, field

from modelo.catalogos import ESTRATEGIA
from modelo.errores import ReglaInvalida
from modelo.textos import decimal, signo


@dataclass(frozen=True)
class Modificadores:
    """Efecto de una formación sobre la legión que la usa."""
    atk: int = 0                 # % de ATK de la formación
    defensa: int = 0             # % de DEF de la formación
    defensa_sinergia: int = 0    # % de DEF extra por la sinergia de la formación
    dano_tipo: dict = field(default_factory=dict)  # % de daño extra por tipo atacante
    dano_recibido: int = 0       # % de daño extra que recibe la legión
    no_atacan: frozenset = frozenset()  # tipos que no atacan en esta formación
    inmunes: frozenset = frozenset()    # tipos que no reciben daño
    sinergias: tuple = ()        # descripción para la vista


class EstrategiaTactica:
    clave = nombre = apodo = None
    mod_atk = mod_def = 0
    cerrada = False                    # los legionarios ignoran 20% del daño
    caballeria_ataca_esclavos = False
    requiere = None                    # tipo de unidad indispensable

    def __init_subclass__(cls, clave=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if clave:
            datos = ESTRATEGIA[clave]
            cls.clave, cls.nombre, cls.apodo = clave, datos["nombre"], datos["apodo"]
            cls.mod_atk, cls.mod_def = datos["atk"], datos["def"]

    def __repr__(self):
        return f"{type(self).__name__}()"

    def validar_composicion(self, conteo):
        """None si la legión puede formar así; si no, el motivo."""
        if self.requiere and conteo.get(self.requiere, 0) <= 0:
            return REQUISITOS[self.requiere]
        return None

    def aplicar_modificadores(self, conteo):
        return Modificadores(atk=self.mod_atk, defensa=self.mod_def, sinergias=(self.resumen(),))

    def resumen(self):
        return f"{self.nombre}: {signo(self.mod_atk)} ATK y {signo(self.mod_def)} DEF"

    def anunciar(self, nombre_legion, conteo):
        """Frase de la bitácora cuando una legión adopta la formación."""
        return f"{nombre_legion} forma en {self.nombre} ({signo(self.mod_atk)} ATK, {signo(self.mod_def)} DEF)."


REQUISITOS = {
    "caballeria": "requiere al menos una unidad de caballería",
    "legionario": "requiere al menos un legionario",
}


class TriplexAcies(EstrategiaTactica, clave="triplex"):
    cerrada = True
    PROPORCION_LEGIONARIOS = 50  # % mínimo de legionarios para la sinergia
    DEF_GLOBAL = 35
    DANO_BALLESTAS = 15

    @staticmethod
    def proporcion_legionarios(conteo):
        total = sum(conteo.values())
        return conteo.get("legionario", 0) * 100 / total if total else 0.0

    def sinergia_activa(self, conteo):
        total = sum(conteo.values())
        return total > 0 and conteo.get("legionario", 0) * 100 >= self.PROPORCION_LEGIONARIOS * total

    def aplicar_modificadores(self, conteo):
        proporcion = decimal(self.proporcion_legionarios(conteo))
        if self.sinergia_activa(conteo):
            return Modificadores(
                atk=self.mod_atk, defensa=self.mod_def, defensa_sinergia=self.DEF_GLOBAL,
                dano_tipo={"ballesta": self.DANO_BALLESTAS},
                sinergias=(self.resumen(),
                           f"Sinergia activa ({proporcion}% legionarios): +35% DEF global y +15% de daño de ballestas"),
            )
        return Modificadores(
            atk=self.mod_atk, defensa=self.mod_def,
            sinergias=(self.resumen(), f"Sin sinergia: {proporcion}% de legionarios (se requiere 50%)"),
        )

    def anunciar(self, nombre_legion, conteo):
        proporcion = decimal(self.proporcion_legionarios(conteo))
        if self.sinergia_activa(conteo):
            detalle = f"y activa su sinergia ({proporcion}% de legionarios): +35% DEF global y +15% de daño de ballestas"
        else:
            detalle = f"sin sinergia: tiene {proporcion}% de legionarios y se requiere 50%"
        return f"{nombre_legion} forma en Triplex Acies (+10% ATK, +10% DEF) {detalle}."


class Cuneus(EstrategiaTactica, clave="cuneus"):
    requiere = "caballeria"
    caballeria_ataca_esclavos = True
    DANO_CABALLERIA = 50
    DANO_RECIBIDO = 50

    def aplicar_modificadores(self, conteo):
        return Modificadores(
            atk=self.mod_atk, defensa=self.mod_def,
            dano_tipo={"caballeria": self.DANO_CABALLERIA}, dano_recibido=self.DANO_RECIBIDO,
            sinergias=(self.resumen(), "Caballería: +50% de daño y también ataca esclavos", "Recibe +50% de daño"),
        )

    def anunciar(self, nombre_legion, conteo):
        return (f"{nombre_legion} forma en Cuneus (+45% ATK, −25% DEF): su caballería causa +50% de daño "
                "y alcanza a los esclavos, pero la legión recibe +50% de daño.")


class Orbis(EstrategiaTactica, clave="orbis"):
    requiere = "legionario"
    cerrada = True

    def aplicar_modificadores(self, conteo):
        return Modificadores(
            atk=self.mod_atk, defensa=self.mod_def,
            no_atacan=frozenset({"caballeria"}), inmunes=frozenset({"ballesta", "ingeniero"}),
            sinergias=(self.resumen(), "La caballería no ataca", "Ballestas e ingenieros no reciben daño"),
        )

    def anunciar(self, nombre_legion, conteo):
        return (f"{nombre_legion} forma en Orbis (−35% ATK, +60% DEF): su caballería no ataca "
                "y sus ballestas e ingenieros no reciben daño.")


FORMACION_INICIAL = "triplex"
ESTRATEGIAS_TACTICAS = {clase.clave: clase() for clase in (TriplexAcies, Cuneus, Orbis)}


def obtener_estrategia(clave):
    try:
        return ESTRATEGIAS_TACTICAS[clave]
    except (KeyError, TypeError):
        raise ReglaInvalida("Elige una formación válida: Triplex Acies, Cuneus u Orbis.") from None
