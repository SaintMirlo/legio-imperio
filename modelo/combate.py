"""Enfrentamiento por turnos entre dos legiones (sección 4 del enunciado).

Estructura (diagrama de clases): un Enfrentamiento tiene uno o más TurnoCombate y cada turno
tiene dos EtapaCombate. MotorCombate aplica las fórmulas de una etapa:

1. Daño = ATK_TOTAL del atacante − DEF_TOTAL del defensor. Si no es positivo, la defensa
   resiste. Si el defensor forma en Cuneus, recibe +50% de daño.
2. El daño se reparte entre los tipos que atacan (legionarios, caballería y ballestas) según
   cuántos son. Cuneus, la sinergia de Triplex Acies y los ingenieros aumentan la parte de
   su tipo. Un tipo sin objetivos válidos no recibe parte.
3. Cada tipo gasta su parte golpe a golpe, en el orden ballestas → caballería → legionarios.
   Cada golpe elige al azar una unidad enemiga válida (todas con la misma probabilidad) y
   vale ATK − DEF de ambas unidades, como mínimo 1. Después se aplican las habilidades
   especiales (carga, daño contra caballería, 20% que ignora el legionario en formación
   cerrada). Una unidad con HP 0 muere y deja de contar de inmediato.

Los atributos se calculan al inicio de cada etapa. El azar usa una semilla por
enfrentamiento, turno y etapa: una partida guardada y recuperada da el mismo resultado.
"""
import random
from collections import Counter
from dataclasses import dataclass, field

from modelo import serializacion as s
from modelo.catalogos import TURNOS_MAXIMOS, UNIDADES
from modelo.errores import ReglaInvalida, texto_requerido
from modelo.estrategias import ESTRATEGIAS_TACTICAS, FORMACION_INICIAL, obtener_estrategia
from modelo.textos import ahora, centesimas, decimal, dividir_redondeando, miles, tropas_en_texto
from modelo.unidades import CLASES, EsclavoAuxiliar

LADOS = ("a", "b")  # a: legión atacante en la etapa 1; b: legión defensora en la etapa 1
EN_CURSO, FINALIZADA, ABANDONADA = "en_curso", "finalizada", "abandonada"
ESTADOS = {EN_CURSO: "En curso", FINALIZADA: "Finalizado", ABANDONADA: "Abandonado"}
PREPARACION, ETAPA_1, ETAPA_2, CERRADO = "preparacion", "etapa_1", "etapa_2", "cerrado"
FASES = {
    PREPARACION: "Preparación",
    ETAPA_1: "Etapa 1 resuelta",
    ETAPA_2: "Etapa 2 resuelta",
    CERRADO: "Turno cerrado",
}
ETAPAS_POR_FASE = {PREPARACION: 0, ETAPA_1: 1, ETAPA_2: 2, CERRADO: 2}
ORDEN_ATAQUE = ("ballesta", "caballeria", "legionario")
SUJETO = {  # sujeto y verbos de la bitácora para cada tipo que ataca
    "legionario": ("Los legionarios", "reparten", "abaten a", "encuentran"),
    "caballeria": ("La caballería", "reparte", "abate a", "encuentra"),
    "ballesta": ("Las ballestas", "reparten", "abaten a", "encuentran"),
}


class ConsolaDesactualizada(ReglaInvalida):
    """La consola pidió avanzar desde un paso que ya se ejecutó (doble clic o dos pestañas)."""


def otro_lado(lado):
    return "b" if lado == "a" else "a"


def repartir_proporcional(total, pesos):
    """Reparte un entero según pesos con el método del resto mayor: la suma es exacta.

    repartir_proporcional(600, {'legionario': 700, 'caballeria': 200, 'ballesta': 100})
    -> {'legionario': 420, 'caballeria': 120, 'ballesta': 60}
    """
    suma = sum(pesos.values())
    partes = {clave: total * peso // suma for clave, peso in pesos.items()}
    sobrante = total - sum(partes.values())
    # sorted es estable: ante restos iguales gana el que va primero en el orden de ataque.
    for clave in sorted(pesos, key=lambda c: -(total * pesos[c] % suma))[:sobrante]:
        partes[clave] += 1
    return partes


def conteo_parcial(datos, clave, tipos=UNIDADES):
    """{'legionario': 3} con solo los tipos que tienen cifra (bajas de una etapa)."""
    valor = s.mapa(datos, clave)
    s.exigir(set(valor) <= set(tipos), f"{clave} tiene un tipo de unidad desconocido")
    return {tipo: s.entero(valor, tipo, 1) for tipo in tipos if tipo in valor}


# --- Etapa de combate ---------------------------------------------------------------------

@dataclass
class AtaqueTipo:
    """Parte del daño de una etapa que reparte un tipo de unidad atacante."""
    tipo: str
    unidades: int      # atacantes vivos de este tipo al inicio de la etapa
    asignado: int      # parte del daño según su proporción
    bono: int          # % extra de su tipo (Cuneus, sinergia de Triplex, ingenieros)
    presupuesto: int   # daño que reparte, con el bono
    golpes: int = 0
    hp_quitado: int = 0
    bajas: dict = field(default_factory=dict)
    sobrante: int = 0  # daño que no encontró objetivos válidos

    def a_dict(self):
        return {
            "tipo": self.tipo, "unidades": self.unidades, "asignado": self.asignado, "bono": self.bono,
            "presupuesto": self.presupuesto, "golpes": self.golpes, "hp_quitado": self.hp_quitado,
            "bajas": dict(self.bajas), "sobrante": self.sobrante,
        }

    @classmethod
    def desde_dict(cls, datos):
        return cls(
            tipo=s.texto(datos, "tipo", opciones=ORDEN_ATAQUE), unidades=s.entero(datos, "unidades", 1),
            asignado=s.entero(datos, "asignado", 0), bono=s.entero(datos, "bono", 0),
            presupuesto=s.entero(datos, "presupuesto", 0), golpes=s.entero(datos, "golpes", 0),
            hp_quitado=s.entero(datos, "hp_quitado", 0), bajas=conteo_parcial(datos, "bajas"),
            sobrante=s.entero(datos, "sobrante", 0),
        )


class MotorCombate:
    """Fórmulas de una etapa. No guarda estado: recibe legiones y atributos y los aplica."""

    @staticmethod
    def dano_total(atr_atacante, atr_defensor):
        """(daño base, daño final): ATK_TOTAL − DEF_TOTAL, con +50% si el defensor usa Cuneus."""
        diferencia = atr_atacante.atk_x100 - atr_defensor.def_x100
        if diferencia <= 0:
            return 0, 0
        base = dividir_redondeando(diferencia, 100)
        return base, dividir_redondeando(base * (100 + atr_defensor.dano_recibido), 100)

    @staticmethod
    def objetivos(tipo, atr_atacante, defensora, atr_defensor):
        """Tipos enemigos con unidades vivas que este tipo puede golpear ahora mismo."""
        vivos = defensora.contar()
        tipos = CLASES[tipo].objetivos(vivos, atr_atacante.estrategia)
        return tuple(t for t in tipos if vivos[t] and t not in atr_defensor.inmunes)

    @classmethod
    def repartir(cls, dano, atr_atacante, defensora, atr_defensor):
        """Divide el daño entre los tipos que atacan según su proporción en el ejército."""
        if dano <= 0:
            return []
        pesos = {
            tipo: atr_atacante.conteo[tipo] for tipo in ORDEN_ATAQUE
            if atr_atacante.ataca(tipo) and atr_atacante.conteo[tipo] > 0
            and cls.objetivos(tipo, atr_atacante, defensora, atr_defensor)
        }
        if not pesos:
            return []
        ataques = []
        for tipo, asignado in repartir_proporcional(dano, pesos).items():
            bono = atr_atacante.dano_tipo.get(tipo, 0)
            ataques.append(AtaqueTipo(tipo, pesos[tipo], asignado, bono,
                                      dividir_redondeando(asignado * (100 + bono), 100)))
        return ataques

    @staticmethod
    def golpe(tipo_atacante, tipo_objetivo, atr_atacante, atr_defensor):
        """ATK de la unidad atacante − DEF de la unidad golpeada, con bonos; como mínimo 1."""
        diferencia = (CLASES[tipo_atacante].atk_base * (100 + atr_atacante.pct_atk)
                      - CLASES[tipo_objetivo].def_base * (100 + atr_defensor.pct_def))
        return max(1, dividir_redondeando(diferencia, 100)) if diferencia > 0 else 1

    @classmethod
    def descargar(cls, ataque, atr_atacante, defensora, atr_defensor, rng):
        """Gasta la parte de daño de un tipo golpe a golpe sobre objetivos al azar."""
        clase = CLASES[ataque.tipo]
        estrategia_defensor = atr_defensor.estrategia
        golpes = {tipo: cls.golpe(ataque.tipo, tipo, atr_atacante, atr_defensor) for tipo in UNIDADES}
        restante = ataque.presupuesto
        tipos = cls.objetivos(ataque.tipo, atr_atacante, defensora, atr_defensor)
        while restante > 0 and tipos:
            tipo_objetivo, indice = defensora.elegir_objetivo(tipos, rng)
            golpe = min(golpes[tipo_objetivo], restante)
            restante -= golpe
            unidad = defensora.unidad(tipo_objetivo, indice)
            ataque.hp_quitado += unidad.recibir_dano(clase.ataque(golpe, tipo_objetivo), estrategia_defensor)
            ataque.golpes += 1
            if not unidad.esta_viva():
                defensora.remover_unidad(tipo_objetivo, indice)
                ataque.bajas[tipo_objetivo] = ataque.bajas.get(tipo_objetivo, 0) + 1
                # Una baja puede cambiar los objetivos válidos (p. ej., cae el último legionario).
                tipos = cls.objetivos(ataque.tipo, atr_atacante, defensora, atr_defensor)
        ataque.sobrante = restante

    @classmethod
    def resolver(cls, etapa, defensora, atr_atacante, atr_defensor, rng):
        etapa.atk_x100, etapa.def_x100 = atr_atacante.atk_x100, atr_defensor.def_x100
        etapa.dano_base, etapa.dano = cls.dano_total(atr_atacante, atr_defensor)
        etapa.ataques = cls.repartir(etapa.dano, atr_atacante, defensora, atr_defensor)
        bajas = Counter()
        for ataque in etapa.ataques:
            cls.descargar(ataque, atr_atacante, defensora, atr_defensor, rng)
            bajas.update(ataque.bajas)
        etapa.bajas = {tipo: bajas[tipo] for tipo in UNIDADES if bajas[tipo]}
        etapa.hp_perdido = sum(ataque.hp_quitado for ataque in etapa.ataques)


@dataclass
class EtapaCombate:
    numero: int        # 1 o 2
    atacante: str      # rolAtacante: lado que ataca en esta etapa
    atk_x100: int = 0  # ATK_TOTAL del atacante, en centésimas
    def_x100: int = 0  # DEF_TOTAL del defensor, en centésimas
    dano_base: int = 0
    dano: int = 0
    ataques: list = field(default_factory=list)
    bajas: dict = field(default_factory=dict)  # bajas del defensor por tipo
    hp_perdido: int = 0

    @property
    def defensor(self):
        return otro_lado(self.atacante)

    @property
    def total_bajas(self):
        return sum(self.bajas.values())

    def calcular_dano(self, defensora, atr_atacante, atr_defensor, rng):
        """Aplica el daño de la etapa a la legión defensora (ver MotorCombate)."""
        MotorCombate.resolver(self, defensora, atr_atacante, atr_defensor, rng)

    def registrar_bajas(self, bitacora, nombres, restantes, turno, enfrentamiento):
        """Anota en la bitácora el daño, los golpes de cada tipo y las bajas del defensor."""
        def anotar(tipo, texto):
            bitacora.registrar_suceso(tipo, texto, turno=turno, etapa=self.numero, enfrentamiento=enfrentamiento)

        atacante, defensor = nombres[self.atacante], nombres[self.defensor]
        cifras = f"ATK total {centesimas(self.atk_x100)} contra DEF total {centesimas(self.def_x100)}"
        if not self.dano:
            anotar("combate", f"Etapa {self.numero}: {atacante} ataca a {defensor}. {cifras}: "
                              "la defensa resiste y no hay daño.")
            return
        cuneus = f" (+50% porque {defensor} forma en Cuneus)" if self.dano != self.dano_base else ""
        anotar("combate", f"Etapa {self.numero}: {atacante} ataca a {defensor}. {cifras}: "
                          f"{miles(self.dano)} de daño{cuneus}.")
        if not self.ataques:
            anotar("combate", f"Ninguna tropa de {atacante} alcanza un objetivo válido: el daño se pierde.")
            return
        atacantes = sum(ataque.unidades for ataque in self.ataques)
        for ataque in self.ataques:
            if not ataque.presupuesto:  # con poco daño, a un tipo minoritario puede tocarle 0
                continue
            sujeto, reparte, abate, encuentra = SUJETO[ataque.tipo]
            if not ataque.golpes:  # otros tipos ya abatieron a todos sus objetivos
                anotar("combate", f"{sujeto} no {encuentra} objetivos válidos: sus {miles(ataque.presupuesto)} "
                                  "de daño se pierden.")
                continue
            bono = f" (con +{ataque.bono}%)" if ataque.bono else ""
            golpes = f"{miles(ataque.golpes)} golpe{'' if ataque.golpes == 1 else 's'}"
            bajas = f" y {abate} {tropas_en_texto(ataque.bajas)}" if ataque.bajas else ", sin bajas"
            sobrante = (f"; {miles(ataque.sobrante)} de daño no encuentran objetivo"
                        if ataque.sobrante else "")
            anotar("combate", f"{sujeto} ({decimal(ataque.unidades * 100 / atacantes)}% de las tropas que "
                              f"atacan) {reparte} {miles(ataque.presupuesto)} de daño{bono} en {golpes}"
                              f"{bajas}{sobrante}.")
        if self.bajas:
            anotar("bajas", f"{defensor} pierde {miles(self.total_bajas)} "
                            f"{'unidad' if self.total_bajas == 1 else 'unidades'} "
                            f"({tropas_en_texto(self.bajas)}) y {miles(self.hp_perdido)} HP. "
                            f"Le quedan {miles(restantes)} integrantes.")
        else:
            anotar("bajas", f"{defensor} no sufre bajas, pero pierde {miles(self.hp_perdido)} HP.")

    def a_dict(self):
        return {
            "numero": self.numero, "atacante": self.atacante,
            "atk_x100": self.atk_x100, "def_x100": self.def_x100,
            "dano_base": self.dano_base, "dano": self.dano,
            "ataques": [ataque.a_dict() for ataque in self.ataques],
            "bajas": dict(self.bajas), "hp_perdido": self.hp_perdido,
        }

    @classmethod
    def desde_dict(cls, datos):
        numero = s.entero(datos, "numero", 1, 2)
        atacante = s.texto(datos, "atacante", opciones=LADOS)
        s.exigir(atacante == ("a" if numero == 1 else "b"), "la etapa 1 la ataca a y la etapa 2, b")
        return cls(
            numero=numero, atacante=atacante,
            atk_x100=s.entero(datos, "atk_x100", 0), def_x100=s.entero(datos, "def_x100", 0),
            dano_base=s.entero(datos, "dano_base", 0), dano=s.entero(datos, "dano", 0),
            ataques=[AtaqueTipo.desde_dict(a) for a in s.lista(datos, "ataques")],
            bajas=conteo_parcial(datos, "bajas"), hp_perdido=s.entero(datos, "hp_perdido", 0),
        )


# --- Turno ----------------------------------------------------------------------------------

@dataclass
class TurnoCombate:
    numero: int
    fase: str = PREPARACION  # estado del turno
    formaciones: dict = field(default_factory=lambda: dict.fromkeys(LADOS, FORMACION_INICIAL))
    etapas: list = field(default_factory=list)
    sueldos: dict = field(default_factory=dict)  # {lado: {"total": 4230, "pagado": True}}

    def estrategia(self, lado):
        return obtener_estrategia(self.formaciones[lado])

    def calcular_atributos(self, legiones):
        """Atributos de ambas legiones con la formación de este turno y sus tropas actuales."""
        return {lado: legiones[lado].calcular_atributos(self.estrategia(lado)) for lado in LADOS}

    def ejecutar(self, legiones, semilla):
        """Resuelve la etapa siguiente: en la 1 ataca a; en la 2 se invierten los roles."""
        numero = len(self.etapas) + 1
        etapa = EtapaCombate(numero, "a" if numero == 1 else "b")
        for legion in legiones.values():
            legion.ordenar_unidades()  # orden fijo: el sorteo no depende de lo ocurrido en memoria
        atributos = self.calcular_atributos(legiones)  # se recalculan al inicio de cada etapa
        rng = random.Random(f"{semilla}:{self.numero}:{numero}")
        etapa.calcular_dano(legiones[etapa.defensor], atributos[etapa.atacante], atributos[etapa.defensor], rng)
        self.etapas.append(etapa)
        self.fase = ETAPA_1 if numero == 1 else ETAPA_2
        return etapa

    def cobrar_mantenimiento(self, legiones):
        """Cada legión paga los sueldos de sus tropas. Devuelve {lado: (Mantenimiento, pagado)}."""
        cobros = {lado: legiones[lado].pagar_mantenimiento() for lado in LADOS}
        self.sueldos = {lado: {"total": m.total, "pagado": pagado} for lado, (m, pagado) in cobros.items()}
        self.fase = CERRADO
        return cobros

    def a_dict(self):
        return {
            "numero": self.numero, "fase": self.fase, "formaciones": dict(self.formaciones),
            "etapas": [etapa.a_dict() for etapa in self.etapas],
            "sueldos": {lado: dict(cobro) for lado, cobro in self.sueldos.items()},
        }

    @classmethod
    def desde_dict(cls, datos):
        fase = s.texto(datos, "fase", opciones=FASES)
        formaciones = s.mapa(datos, "formaciones")
        s.exigir(set(formaciones) == set(LADOS), "formaciones debe indicar ambos lados")
        sueldos = s.mapa(datos, "sueldos")
        s.exigir(set(sueldos) <= set(LADOS), "sueldos tiene un lado desconocido")
        etapas = [EtapaCombate.desde_dict(e) for e in s.lista(datos, "etapas")]
        s.exigir([e.numero for e in etapas] == list(range(1, ETAPAS_POR_FASE[fase] + 1)),
                 "las etapas no corresponden a la fase del turno")
        return cls(
            numero=s.entero(datos, "numero", 1, TURNOS_MAXIMOS), fase=fase,
            formaciones={lado: s.texto(formaciones, lado, opciones=ESTRATEGIAS_TACTICAS) for lado in LADOS},
            etapas=etapas,
            sueldos={lado: {"total": s.entero(s.mapa(sueldos, lado), "total", 0),
                            "pagado": s.booleano(s.mapa(sueldos, lado), "pagado")} for lado in sueldos},
        )


# --- Participantes y enfrentamiento ---------------------------------------------------------

def tropas_en_cero():
    return dict.fromkeys(UNIDADES, 0)


@dataclass
class Participante:
    """Una legión dentro de un enfrentamiento, con sus cifras de ese enfrentamiento."""
    legion_id: int
    nombre: str          # nombre de la legión al iniciar (la bitácora conserva el original)
    legatus: str         # descripción del Legatus al iniciar
    formacion: str
    tropas_iniciales: dict
    hp_inicial: int
    presupuesto_inicial: int
    bajas: dict = field(default_factory=tropas_en_cero)
    hp_perdido: int = 0
    contratados: dict = field(default_factory=tropas_en_cero)
    convertidos: dict = field(default_factory=lambda: dict.fromkeys(EsclavoAuxiliar.DESTINOS, 0))
    gastos: int = 0      # refuerzos y conversiones
    sueldos: int = 0     # mantenimiento pagado
    tropas_finales: dict | None = None
    presupuesto_final: int | None = None

    @classmethod
    def desde_legion(cls, legion):
        return cls(
            legion_id=legion.id, nombre=legion.nombre, legatus=legion.legatus.describir(),
            formacion=FORMACION_INICIAL, tropas_iniciales=legion.contar(),
            hp_inicial=legion.hp_actual(), presupuesto_inicial=legion.presupuesto,
        )

    @property
    def total_bajas(self):
        return sum(self.bajas.values())

    def a_dict(self):
        return {
            "legion_id": self.legion_id, "nombre": self.nombre, "legatus": self.legatus,
            "formacion": self.formacion, "tropas_iniciales": dict(self.tropas_iniciales),
            "hp_inicial": self.hp_inicial, "presupuesto_inicial": self.presupuesto_inicial,
            "bajas": dict(self.bajas), "hp_perdido": self.hp_perdido,
            "contratados": dict(self.contratados), "convertidos": dict(self.convertidos),
            "gastos": self.gastos, "sueldos": self.sueldos,
            "tropas_finales": None if self.tropas_finales is None else dict(self.tropas_finales),
            "presupuesto_final": self.presupuesto_final,
        }

    @classmethod
    def desde_dict(cls, datos):
        return cls(
            legion_id=s.entero(datos, "legion_id", 1), nombre=s.texto(datos, "nombre"),
            legatus=s.texto(datos, "legatus"),
            formacion=s.texto(datos, "formacion", opciones=ESTRATEGIAS_TACTICAS),
            tropas_iniciales=s.tropas(datos, "tropas_iniciales"), hp_inicial=s.entero(datos, "hp_inicial", 0),
            presupuesto_inicial=s.entero(datos, "presupuesto_inicial", 0),
            bajas=s.tropas(datos, "bajas"), hp_perdido=s.entero(datos, "hp_perdido", 0),
            contratados=s.tropas(datos, "contratados"),
            convertidos=s.tropas(datos, "convertidos", tipos=EsclavoAuxiliar.DESTINOS),
            gastos=s.entero(datos, "gastos", 0), sueldos=s.entero(datos, "sueldos", 0),
            tropas_finales=None if datos.get("tropas_finales") is None else s.tropas(datos, "tropas_finales"),
            presupuesto_final=s.entero(datos, "presupuesto_final", 0, nulo=True),
        )


class Enfrentamiento:
    def __init__(self, id, nombre, participantes, semilla, *, estado=EN_CURSO, turnos=None,
                 ganador=None, motivo=None, pasos=0, creado=None, actualizado=None):
        self.id = id
        self.nombre = nombre
        self.participantes = participantes  # {"a": Participante, "b": Participante}
        self.semilla = semilla
        self.estado = estado
        self.turnos = turnos or [TurnoCombate(1)]
        self.ganador = ganador  # "a", "b" o None (empate o abandono)
        self.motivo = motivo
        self.pasos = pasos      # pasos ejecutados: evita que un doble clic avance dos veces
        self.creado = creado or ahora()
        self.actualizado = actualizado or self.creado

    def __repr__(self):
        return f"Enfrentamiento({self.nombre!r}, turno {self.turno_numero}, {self.estado})"

    @classmethod
    def iniciar(cls, id, nombre, legion_a, legion_b, bitacora, semilla=None):
        """Abre el turno 1: ambas legiones en Triplex Acies; a ataca primero y b defiende."""
        nombre = texto_requerido(nombre, "el nombre del enfrentamiento")
        if semilla is None:
            semilla = random.SystemRandom().randrange(1, 2 ** 31)
        participantes = {"a": Participante.desde_legion(legion_a), "b": Participante.desde_legion(legion_b)}
        enfrentamiento = cls(id, nombre, participantes, semilla)
        bitacora.registrar_suceso(
            "sistema",
            f"Comienza el enfrentamiento «{nombre}»: {legion_a.nombre} ataca y {legion_b.nombre} defiende. "
            "En el primer turno ambas legiones forman en Triplex Acies.",
            turno=1, etapa=0, enfrentamiento=id,
        )
        return enfrentamiento

    # --- Consultas ----------------------------------------------------------------------

    @property
    def turno_actual(self):
        return self.turnos[-1]

    @property
    def turno_numero(self):
        return self.turno_actual.numero

    @property
    def en_curso(self):
        return self.estado == EN_CURSO

    def nombres(self):
        return {lado: participante.nombre for lado, participante in self.participantes.items()}

    def lado_de(self, id_legion):
        return next((lado for lado, p in self.participantes.items() if p.legion_id == id_legion), None)

    def ultima_etapa(self):
        for turno in reversed(self.turnos):
            if turno.etapas:
                return turno, turno.etapas[-1]
        return None, None

    # --- Acciones -----------------------------------------------------------------------

    def _exigir_en_curso(self):
        if not self.en_curso:
            raise ReglaInvalida(f"El enfrentamiento «{self.nombre}» ya terminó.")

    def avanzar(self, legiones, bitacora, decisiones=None):
        """Paso a paso: etapa 1 → etapa 2 → sueldos y cierre del turno → turno siguiente.

        decisiones (solo en la preparación): {lado: {"formacion": clave,
        "convertir": {"legionario": n, "caballeria": m}}}.
        """
        self._exigir_en_curso()
        turno = self.turno_actual
        if turno.fase == PREPARACION:
            self._aplicar_decisiones(turno, legiones, bitacora, decisiones or {})
            self._resolver_etapa(turno, legiones, bitacora)
        elif turno.fase == ETAPA_1:
            self._resolver_etapa(turno, legiones, bitacora)
        else:
            self._cerrar_turno(turno, legiones, bitacora)
        self.pasos += 1
        self.actualizado = ahora()

    def _aplicar_decisiones(self, turno, legiones, bitacora, decisiones):
        """Valida primero las decisiones de ambas legiones y luego las aplica todas juntas."""
        if set(decisiones) - set(LADOS):
            raise ReglaInvalida("Las decisiones deben indicar la legión a o b.")
        planes = {}
        for lado in LADOS:
            decision = decisiones.get(lado) or {}
            if not isinstance(decision, dict):
                raise ReglaInvalida("Las decisiones del turno no tienen el formato esperado.")
            legion = legiones[lado]
            formacion = decision.get("formacion") or turno.formaciones[lado]
            convertir = decision.get("convertir") or {}
            estrategia = obtener_estrategia(formacion)
            if turno.numero == 1:
                if formacion != FORMACION_INICIAL:
                    raise ReglaInvalida("En el primer turno ambas legiones forman en Triplex Acies.")
                if any(convertir.values()):
                    raise ReglaInvalida("Los esclavos se convierten en la reagrupación, a partir del turno 2.")
            cantidades, costo = legion.validar_conversion(convertir)
            conteo = legion.contar()
            conteo["esclavo"] -= sum(cantidades.values())
            for destino, cantidad in cantidades.items():
                conteo[destino] += cantidad
            motivo = estrategia.validar_composicion(conteo)
            if motivo:
                raise ReglaInvalida(f"{legion.nombre} no puede formar en {estrategia.nombre}: {motivo}.")
            planes[lado] = (estrategia, cantidades, costo)

        for lado, (estrategia, cantidades, costo) in planes.items():
            legion = legiones[lado]
            participante = self.participantes[lado]
            if costo:
                legion.convertir_esclavos(cantidades)
                for destino, cantidad in cantidades.items():
                    participante.convertidos[destino] += cantidad
                participante.gastos += costo
                bitacora.registrar_suceso(
                    "conversion",
                    f"{legion.nombre} convierte {tropas_en_texto(cantidades)} a partir de sus esclavos "
                    f"por {miles(costo)} denarios. Le quedan {miles(legion.presupuesto)}.",
                    turno=turno.numero, etapa=0, enfrentamiento=self.id,
                )
            turno.formaciones[lado] = estrategia.clave
            participante.formacion = estrategia.clave
            bitacora.registrar_suceso("estrategia", estrategia.anunciar(legion.nombre, legion.contar()),
                                      turno=turno.numero, etapa=0, enfrentamiento=self.id)

    def _resolver_etapa(self, turno, legiones, bitacora):
        etapa = turno.ejecutar(legiones, self.semilla)
        participante = self.participantes[etapa.defensor]
        for tipo, cantidad in etapa.bajas.items():
            participante.bajas[tipo] += cantidad
        participante.hp_perdido += etapa.hp_perdido
        etapa.registrar_bajas(bitacora, self.nombres(), legiones[etapa.defensor].integrantes(),
                              turno.numero, self.id)
        self.comprobar_fin(legiones, bitacora, etapa=etapa.numero)

    def _cerrar_turno(self, turno, legiones, bitacora):
        impagos = []
        for lado, (mantenimiento, pagado) in turno.cobrar_mantenimiento(legiones).items():
            legion = legiones[lado]
            if pagado:
                self.participantes[lado].sueldos += mantenimiento.total
                texto = (f"{legion.nombre} paga {miles(mantenimiento.total)} denarios de sueldos "
                         f"({mantenimiento.detalle()}). Le quedan {miles(legion.presupuesto)}.")
            else:
                impagos.append(lado)
                texto = (f"{legion.nombre} no puede pagar {miles(mantenimiento.total)} denarios de sueldos: "
                         f"solo tiene {miles(legion.presupuesto)}.")
            bitacora.registrar_suceso("economia", texto, turno=turno.numero, etapa=3, enfrentamiento=self.id)
        if self.comprobar_fin(legiones, bitacora, impagos=impagos, etapa=3):
            return
        if turno.numero >= TURNOS_MAXIMOS:
            self._finalizar(legiones, bitacora, None,
                            f"Se cumplieron {TURNOS_MAXIMOS} turnos sin que ninguna legión cayera.", etapa=3)
            return
        self.cambiar_turno(legiones, bitacora)

    def comprobar_fin(self, legiones, bitacora, impagos=(), etapa=None):
        """Termina el combate si una legión se quedó sin integrantes que no sean esclavos
        o no pudo pagar los sueldos. Devuelve True si terminó."""
        nombres = self.nombres()
        caidos = [lado for lado in LADOS if not legiones[lado].tiene_combatientes()]
        if len(caidos) == 2:
            self._finalizar(legiones, bitacora, None,
                            "Ambas legiones se quedaron sin integrantes que no sean esclavos.", etapa)
        elif caidos:
            self._finalizar(legiones, bitacora, otro_lado(caidos[0]),
                            f"{nombres[caidos[0]]} se quedó sin integrantes que no sean esclavos.", etapa)
        elif len(impagos) == 2:
            self._finalizar(legiones, bitacora, None, "Ninguna legión pudo pagar los sueldos de sus soldados.", etapa)
        elif impagos:
            self._finalizar(legiones, bitacora, otro_lado(impagos[0]),
                            f"{nombres[impagos[0]]} no pudo pagar los sueldos de sus soldados.", etapa)
        return not self.en_curso

    def _finalizar(self, legiones, bitacora, ganador, motivo, etapa=None, estado=FINALIZADA):
        self.estado, self.ganador, self.motivo = estado, ganador, motivo
        for lado, participante in self.participantes.items():
            participante.tropas_finales = legiones[lado].contar()
            participante.presupuesto_final = legiones[lado].presupuesto
        if estado == ABANDONADA:
            texto = f"Se abandona el enfrentamiento «{self.nombre}» en el turno {self.turno_numero}: no hay vencedor."
        else:
            resultado = f"vence {self.participantes[ganador].nombre}" if ganador else "empate"
            texto = f"Fin del enfrentamiento «{self.nombre}»: {resultado}. {motivo}"
        bitacora.registrar_suceso("fin", texto, turno=self.turno_numero, etapa=etapa, enfrentamiento=self.id)

    def cambiar_turno(self, legiones, bitacora):
        """Abre el turno siguiente en preparación (reagrupación), con las formaciones del
        turno anterior si la composición actual todavía las permite."""
        nuevo = TurnoCombate(self.turno_numero + 1, formaciones=dict(self.turno_actual.formaciones))
        self.turnos.append(nuevo)
        bitacora.registrar_suceso(
            "sistema", f"Comienza el turno {nuevo.numero}: reagrupación, conversión de esclavos y "
                       "elección de formaciones.",
            turno=nuevo.numero, etapa=0, enfrentamiento=self.id,
        )
        for lado in LADOS:
            estrategia = nuevo.estrategia(lado)
            motivo = estrategia.validar_composicion(legiones[lado].contar())
            if motivo:
                nuevo.formaciones[lado] = self.participantes[lado].formacion = FORMACION_INICIAL
                bitacora.registrar_suceso(
                    "estrategia", f"{legiones[lado].nombre} ya no puede formar en {estrategia.nombre} "
                                  f"({motivo}): vuelve a Triplex Acies.",
                    turno=nuevo.numero, etapa=0, enfrentamiento=self.id,
                )

    def contratar_refuerzos(self, lado, legion, cantidades, bitacora):
        """Contratar tropas durante el combate solo es posible en la preparación de un turno."""
        self._exigir_en_curso()
        if self.turno_actual.fase != PREPARACION:
            raise ReglaInvalida("Los refuerzos se contratan en la preparación del turno, antes de la etapa 1.")
        cantidades, costo = legion.contratar(cantidades)
        participante = self.participantes[lado]
        for tipo, cantidad in cantidades.items():
            participante.contratados[tipo] += cantidad
        participante.gastos += costo
        bitacora.registrar_suceso(
            "contrato", f"{legion.nombre} contrata refuerzos: {tropas_en_texto(cantidades)} por "
                        f"{miles(costo)} denarios. Le quedan {miles(legion.presupuesto)}.",
            turno=self.turno_numero, etapa=0, enfrentamiento=self.id,
        )
        self.actualizado = ahora()
        return cantidades, costo

    def abandonar(self, legiones, bitacora):
        self._exigir_en_curso()
        self._finalizar(legiones, bitacora, None, f"Se abandonó en el turno {self.turno_numero}.",
                        estado=ABANDONADA)
        self.actualizado = ahora()

    # --- Persistencia -------------------------------------------------------------------

    def a_dict(self):
        return {
            "id": self.id, "nombre": self.nombre, "estado": self.estado, "semilla": self.semilla,
            "pasos": self.pasos, "ganador": self.ganador, "motivo": self.motivo,
            "creado": self.creado, "actualizado": self.actualizado,
            "participantes": {lado: p.a_dict() for lado, p in self.participantes.items()},
            "turnos": [turno.a_dict() for turno in self.turnos],
        }

    @classmethod
    def desde_dict(cls, datos):
        estado = s.texto(datos, "estado", opciones=ESTADOS)
        ganador = s.texto(datos, "ganador", nulo=True, opciones=LADOS)
        s.exigir(ganador is None or estado == FINALIZADA, "solo un enfrentamiento finalizado tiene ganador")
        participantes = s.mapa(datos, "participantes")
        s.exigir(set(participantes) == set(LADOS), "participantes debe tener los lados a y b")
        participantes = {lado: Participante.desde_dict(s.mapa(participantes, lado)) for lado in LADOS}
        s.exigir(participantes["a"].legion_id != participantes["b"].legion_id,
                 "una legión no puede enfrentarse a sí misma")
        turnos = [TurnoCombate.desde_dict(t) for t in s.lista(datos, "turnos")]
        s.exigir([t.numero for t in turnos] == list(range(1, len(turnos) + 1)), "los turnos deben ir en orden")
        s.exigir(all(t.fase == CERRADO for t in turnos[:-1]), "solo el último turno puede estar abierto")
        s.exigir(estado != EN_CURSO or turnos[-1].fase != CERRADO, "un combate en curso tiene un turno abierto")
        return cls(
            id=s.entero(datos, "id", 1), nombre=s.texto(datos, "nombre"), participantes=participantes,
            semilla=s.entero(datos, "semilla", 0), estado=estado, turnos=turnos, ganador=ganador,
            motivo=s.texto(datos, "motivo", nulo=True), pasos=s.entero(datos, "pasos", 0),
            creado=s.instante(datos, "creado"), actualizado=s.instante(datos, "actualizado"),
        )
