"""Unidades militares romanas (tabla 2 del enunciado).

UnidadMilitar reúne lo común: HP propio (una unidad puede quedar herida), ATK, DEF y costo.
Cada tipo de la tabla es una subclase con su habilidad especial:

- Legionario: ignora 20% del daño en formaciones cerradas (Triplex Acies y Orbis).
- Caballería: su carga causa 20% de daño adicional a los legionarios.
- Ballesta: causa 50% de daño extra a la caballería y puede atacar a cualquier unidad.
- Ingeniero: no ataca; por cada 10, +1% de DEF global y +2% de daño de artillería.
- EsclavoAuxiliar: no ataca; por cada 50, −15% de mantenimiento; se convierte en
  legionario o caballería durante la reagrupación.

Reglas de objetivos del enunciado: legionarios y caballería solo atacan ballestas,
ingenieros y esclavos cuando el enemigo ya no tiene legionarios ni caballería; en Cuneus la
caballería también puede atacar esclavos; las ballestas atacan a cualquiera.
"""
from modelo.catalogos import UNIDAD, UNIDADES
from modelo.textos import dividir_redondeando

CUERPO_A_CUERPO = ("legionario", "caballeria")
RETAGUARDIA = ("ballesta", "ingeniero", "esclavo")


def objetivos_cuerpo_a_cuerpo(enemigos):
    """Mientras el enemigo tenga legionarios o caballería, solo se puede atacar a esos."""
    if any(enemigos.get(tipo, 0) > 0 for tipo in CUERPO_A_CUERPO):
        return CUERPO_A_CUERPO
    return RETAGUARDIA


class UnidadMilitar:
    """Integrante de una legión. Los valores base salen de la tabla 2; el HP es de cada unidad."""

    __slots__ = ("hp",)

    tipo = None
    nombre = None
    hp_base = atk_base = def_base = costo = 0
    puede_atacar = True
    bonos_contra = {}  # % de daño extra según el tipo de unidad golpeada

    def __init_subclass__(cls, tipo=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if tipo is not None:
            datos = UNIDAD[tipo]
            cls.tipo = tipo
            cls.nombre = datos["nombre"]
            cls.hp_base, cls.atk_base = datos["hp"], datos["atk"]
            cls.def_base, cls.costo = datos["def"], datos["costo"]

    def __init__(self, hp=None):
        if hp is None:
            hp = self.hp_base
        if type(hp) is not int or not 0 < hp <= self.hp_base:
            raise ValueError(f"HP inválido para {self.nombre}: {hp!r}")
        self.hp = hp

    def __repr__(self):
        return f"{type(self).__name__}(hp={self.hp})"

    def esta_viva(self):
        return self.hp > 0

    def esta_herida(self):
        return 0 < self.hp < self.hp_base

    def recibir_dano(self, dano, estrategia=None):
        """Resta el daño del HP (mínimo 1) y devuelve los HP que la unidad perdió de verdad."""
        perdido = min(self.hp, max(1, dano))
        self.hp -= perdido
        return perdido

    @classmethod
    def calcular_ataque(cls, bono_pct):
        """ATK de una unidad con los bonos porcentuales de su legión (Legatus, formación…)."""
        return cls.atk_base * (100 + bono_pct) / 100

    @classmethod
    def calcular_defensa(cls, bono_pct):
        """DEF de una unidad con los bonos porcentuales de su legión."""
        return cls.def_base * (100 + bono_pct) / 100

    @classmethod
    def objetivos(cls, enemigos, estrategia=None):
        """Tipos de unidad enemiga que este tipo puede atacar. enemigos: {tipo: vivos}."""
        return ()

    @classmethod
    def ataque(cls, golpe, tipo_objetivo):
        """Daño de un golpe contra un tipo de unidad, con la habilidad especial del atacante."""
        bono = cls.bonos_contra.get(tipo_objetivo, 0)
        return dividir_redondeando(golpe * (100 + bono), 100)


class Legionario(UnidadMilitar, tipo="legionario"):
    __slots__ = ()
    habilidad = "Ignora 20% del daño en formaciones cerradas (Triplex Acies y Orbis)."
    REDUCCION_DANO = 20  # %

    @classmethod
    def objetivos(cls, enemigos, estrategia=None):
        return objetivos_cuerpo_a_cuerpo(enemigos)

    def recibir_dano(self, dano, estrategia=None):
        if estrategia is not None and estrategia.cerrada:
            dano = dividir_redondeando(dano * (100 - self.REDUCCION_DANO), 100)
        return super().recibir_dano(dano)


class Caballeria(UnidadMilitar, tipo="caballeria"):
    __slots__ = ()
    habilidad = "Su carga causa 20% de daño adicional a los legionarios."
    CARGA = 20  # % extra contra legionarios
    bonos_contra = {"legionario": CARGA}

    @classmethod
    def objetivos(cls, enemigos, estrategia=None):
        tipos = objetivos_cuerpo_a_cuerpo(enemigos)
        if estrategia is not None and estrategia.caballeria_ataca_esclavos and "esclavo" not in tipos:
            tipos += ("esclavo",)
        return tipos


class Ballesta(UnidadMilitar, tipo="ballesta"):
    __slots__ = ()
    habilidad = "Causa 50% de daño extra a la caballería y puede atacar a cualquier unidad."
    CONTRA_CABALLERIA = 50  # %
    bonos_contra = {"caballeria": CONTRA_CABALLERIA}

    @classmethod
    def objetivos(cls, enemigos, estrategia=None):
        return UNIDADES


class Ingeniero(UnidadMilitar, tipo="ingeniero"):
    __slots__ = ()
    habilidad = "Por cada 10: +1% a la defensa global y +2% de daño de artillería."
    puede_atacar = False
    POR_BLOQUE = 10
    DEF_POR_BLOQUE = 1        # % de DEF global
    ARTILLERIA_POR_BLOQUE = 2  # % de daño de ballestas

    @classmethod
    def aplicar_bono(cls, cantidad):
        """Bonos que aportan los ingenieros vivos: (% DEF global, % daño de ballestas)."""
        bloques = cantidad // cls.POR_BLOQUE
        return bloques * cls.DEF_POR_BLOQUE, bloques * cls.ARTILLERIA_POR_BLOQUE


class EsclavoAuxiliar(UnidadMilitar, tipo="esclavo"):
    __slots__ = ()
    habilidad = "Por cada 50: reduce 15% el mantenimiento de la legión."
    puede_atacar = False
    convertible = True
    POR_BLOQUE = 50
    DESCUENTO_POR_BLOQUE = 15  # % de mantenimiento
    # Decisión de diseño: el descuento llega como máximo a 90%, para que una legión con
    # tropas siempre pague algún sueldo y el término por falta de pago siga siendo posible.
    DESCUENTO_MAXIMO = 90
    DESTINOS = ("legionario", "caballeria")

    @classmethod
    def descuento_mantenimiento(cls, cantidad):
        """% de descuento de los sueldos: 15% por cada 50 esclavos, hasta 90%."""
        return min(cls.DESCUENTO_MAXIMO, cantidad // cls.POR_BLOQUE * cls.DESCUENTO_POR_BLOQUE)

    def convertir(self, destino):
        """El esclavo se convierte en una unidad nueva, con el HP completo de su nuevo tipo."""
        if destino not in self.DESTINOS:
            raise ValueError("Los esclavos solo se convierten en legionarios o caballería.")
        return CLASES[destino]()


CLASES = {clase.tipo: clase for clase in (Legionario, Caballeria, Ballesta, Ingeniero, EsclavoAuxiliar)}


def crear_unidad(tipo, hp=None):
    return CLASES[tipo](hp)
