"""Legión: contingente de unidades al mando de un Legatus, con presupuesto propio.

Métodos del diagrama de clases: agregar_unidad, remover_unidad, calcular_atributos y
pagar_mantenimiento. La legión también valida sus contratos y la conversión de esclavos,
porque ambas reglas dependen de su presupuesto.
"""
from collections import Counter
from dataclasses import dataclass

from modelo import serializacion as s
from modelo.catalogos import INTEGRANTES_MAXIMOS, PRESUPUESTO_MAXIMO, UNIDAD, UNIDADES
from modelo.errores import ReglaInvalida, entero_en_rango, texto_requerido
from modelo.estrategias import Modificadores
from modelo.legatus import Legatus
from modelo.textos import ahora, cantidad_tropa, dividir_redondeando, enumerar, miles, signo
from modelo.unidades import CLASES, EsclavoAuxiliar, Ingeniero

ATACANTES = ("legionario", "caballeria", "ballesta")  # los tipos que pueden atacar


def normalizar_cantidades(cantidades, tipos=UNIDADES):
    """{'legionario': 10} -> {'legionario': 10, 'caballeria': 0, ...}, validando cada cifra."""
    if not isinstance(cantidades, dict) or set(cantidades) - set(tipos):
        raise ReglaInvalida("Indica cantidades solo para los tipos de unidad del catálogo.")
    return {
        tipo: entero_en_rango(cantidades.get(tipo, 0), f"la cantidad de {UNIDAD[tipo]['plural'].lower()}",
                              0, INTEGRANTES_MAXIMOS)
        for tipo in tipos
    }


@dataclass(frozen=True)
class Atributos:
    """ATK y DEF de una legión con todos sus bonos, fijos durante una etapa de combate.

    Los totales se guardan en centésimas (enteros) para que el daño no dependa de errores
    de coma flotante: 25 ATK con +10% son 2.750 centésimas.
    """
    estrategia: object       # EstrategiaTactica o None (fuera de combate)
    conteo: dict             # unidades vivas por tipo
    pct_atk: int             # % de ATK total: Legatus + formación
    pct_def: int             # % de DEF total: Legatus + formación + sinergia + ingenieros
    desglose_atk: tuple      # (("Legatus", 10), ("Triplex Acies", 10))
    desglose_def: tuple
    dano_tipo: dict          # % de daño extra que reparte cada tipo atacante
    dano_recibido: int       # % de daño extra que recibe la legión (Cuneus)
    no_atacan: frozenset     # tipos que no atacan ni suman ATK (caballería en Orbis)
    inmunes: frozenset       # tipos que no reciben daño (ballestas e ingenieros en Orbis)
    sinergias: tuple         # efectos activos, en palabras
    atk_x100: int
    def_x100: int

    @property
    def atk_total(self):
        return self.atk_x100 / 100

    @property
    def def_total(self):
        return self.def_x100 / 100

    def ataca(self, tipo):
        return CLASES[tipo].puede_atacar and tipo not in self.no_atacan

    def atk_unidad(self, tipo):
        return CLASES[tipo].calcular_ataque(self.pct_atk)

    def def_unidad(self, tipo):
        return CLASES[tipo].calcular_defensa(self.pct_def)

    def atk_tipo(self, tipo):
        """ATK que aporta todo el grupo de ese tipo (0 si en esta formación no ataca)."""
        if tipo in self.no_atacan:
            return 0.0
        return self.conteo[tipo] * CLASES[tipo].atk_base * (100 + self.pct_atk) / 100

    def def_tipo(self, tipo):
        return self.conteo[tipo] * CLASES[tipo].def_base * (100 + self.pct_def) / 100


@dataclass(frozen=True)
class FilaFuerza:
    """Fila de la tabla dinámica de una legión: un tipo de unidad con sus estadísticas."""
    tipo: str
    vivos: int
    heridos: int
    hp: int
    hp_maximo: int
    atk_unidad: float
    def_unidad: float
    atk_total: float
    def_total: float
    sueldo: int       # mantenimiento base del grupo, antes de bonos y descuentos
    ataca: bool
    inmune: bool

    @property
    def nombre(self):
        return UNIDAD[self.tipo]["nombre"]


@dataclass(frozen=True)
class Mantenimiento:
    """Sueldos de un turno: base del catálogo, %Costo del Legatus y descuento por esclavos."""
    base: int
    pct_legatus: int
    esclavos: int
    pct_descuento: int
    total: int

    @property
    def con_legatus(self):
        return dividir_redondeando(self.base * (100 + self.pct_legatus), 100)

    @property
    def ajuste_legatus(self):
        return self.con_legatus - self.base

    @property
    def descuento(self):
        return self.con_legatus - self.total

    def detalle(self):
        """'base 5.000, +15% por el Legatus y −30% por 100 esclavos'."""
        partes = [f"base {miles(self.base)}"]
        if self.pct_legatus:
            partes.append(f"{signo(self.pct_legatus)} por el Legatus")
        if self.pct_descuento:
            partes.append(f"−{self.pct_descuento}% por {cantidad_tropa('esclavo', self.esclavos)}")
        return enumerar(partes)


def agrupar_por_hp(unidades):
    """[Legionario(20), Legionario(12), Legionario(20)] -> [[20, 2], [12, 1]]."""
    conteo = Counter(unidad.hp for unidad in unidades)
    return [[hp, cantidad] for hp, cantidad in sorted(conteo.items(), reverse=True)]


class Legion:
    def __init__(self, nombre, consul, legatus, presupuesto, *, id=None, asignado=None, creada=None):
        self.id = id
        self.nombre = texto_requerido(nombre, "el nombre de la legión")
        self.consul = consul  # 1 o 2: el cónsul que nombró a su Legatus
        if not isinstance(legatus, Legatus):
            raise TypeError("legatus debe ser un Legatus")
        self.legatus = legatus
        self.presupuesto = entero_en_rango(presupuesto, "el presupuesto", 0, PRESUPUESTO_MAXIMO)
        self.asignado = presupuesto if asignado is None else asignado  # fondos recibidos en total
        self.creada = creada or ahora()
        self.unidades = {tipo: [] for tipo in UNIDADES}

    def __repr__(self):
        return f"Legion({self.nombre!r}, {self.integrantes()} integrantes)"

    # --- Composición -------------------------------------------------------------------

    def contar(self):
        return {tipo: len(lista) for tipo, lista in self.unidades.items()}

    def integrantes(self):
        return sum(len(lista) for lista in self.unidades.values())

    def esta_lista(self):
        """Lista para combatir: tiene al menos un legionario, jinete o ballesta que ataque."""
        return any(self.unidades[tipo] for tipo in ATACANTES)

    def tiene_combatientes(self):
        """El combate sigue mientras la legión tenga integrantes que no sean esclavos."""
        return any(lista for tipo, lista in self.unidades.items() if tipo != "esclavo")

    def hp_actual(self, tipo=None):
        tipos = UNIDADES if tipo is None else (tipo,)
        return sum(unidad.hp for t in tipos for unidad in self.unidades[t])

    def hp_maximo(self, tipo=None):
        tipos = UNIDADES if tipo is None else (tipo,)
        return sum(len(self.unidades[t]) * CLASES[t].hp_base for t in tipos)

    def heridos(self, tipo):
        return sum(1 for unidad in self.unidades[tipo] if unidad.esta_herida())

    def agregar_unidad(self, unidad):
        self.unidades[unidad.tipo].append(unidad)

    def remover_unidad(self, tipo, indice):
        """Quita una unidad (la última ocupa su lugar: el orden no importa y es O(1))."""
        lista = self.unidades[tipo]
        unidad = lista[indice]
        ultima = lista.pop()
        if indice < len(lista):
            lista[indice] = ultima
        return unidad

    def unidad(self, tipo, indice):
        return self.unidades[tipo][indice]

    def ordenar_unidades(self):
        """Ordena cada tipo de mayor a menor HP, el mismo orden en que se cargan de la base de datos.

        El objetivo de cada golpe se sortea por posición en la lista. Con un orden fijo al inicio
        de cada etapa, una campaña recuperada sigue igual que la que continuó en memoria.
        """
        for lista in self.unidades.values():
            lista.sort(key=lambda unidad: unidad.hp, reverse=True)

    def elegir_objetivo(self, tipos, rng):
        """Elige al azar una unidad viva de esos tipos; todas tienen la misma probabilidad."""
        total = sum(len(self.unidades[tipo]) for tipo in tipos)
        if not total:
            return None
        sorteo = rng.randrange(total)
        for tipo in tipos:
            cantidad = len(self.unidades[tipo])
            if sorteo < cantidad:
                return tipo, sorteo
            sorteo -= cantidad
        return None  # inalcanzable

    # --- Contratación -------------------------------------------------------------------

    @staticmethod
    def costo_contrato(cantidades):
        """Costo de contratar: precio del catálogo por unidad. El Legatus no lo modifica."""
        return sum(cantidad * UNIDAD[tipo]["costo"] for tipo, cantidad in cantidades.items())

    def validar_contrato(self, cantidades):
        """Devuelve (cantidades completas, costo) o lanza ReglaInvalida con el motivo."""
        cantidades = normalizar_cantidades(cantidades)
        nuevas = sum(cantidades.values())
        if nuevas == 0:
            raise ReglaInvalida("Indica cuántas unidades quieres contratar.")
        if self.integrantes() + nuevas > INTEGRANTES_MAXIMOS:
            raise ReglaInvalida(
                f"Una legión admite hasta {miles(INTEGRANTES_MAXIMOS)} integrantes: {self.nombre} tiene "
                f"{miles(self.integrantes())} y el contrato suma {miles(nuevas)}."
            )
        costo = self.costo_contrato(cantidades)
        if costo > self.presupuesto:
            raise ReglaInvalida(
                f"Presupuesto insuficiente: el contrato cuesta {miles(costo)} denarios y "
                f"{self.nombre} tiene {miles(self.presupuesto)}."
            )
        return cantidades, costo

    def contratar(self, cantidades):
        """Paga el contrato y suma las unidades con su HP completo. Devuelve (cantidades, costo)."""
        cantidades, costo = self.validar_contrato(cantidades)
        for tipo, cantidad in cantidades.items():
            clase = CLASES[tipo]
            for _ in range(cantidad):
                self.agregar_unidad(clase())
        self.presupuesto -= costo
        return cantidades, costo

    def simular_contrato(self, cantidades):
        """Vista previa de un contrato sin modificar la legión (para el formulario en vivo)."""
        try:
            cantidades = normalizar_cantidades(cantidades)
        except ReglaInvalida as error:
            return {"valido": False, "mensaje": str(error)}
        conteo = self.contar()
        despues = {tipo: conteo[tipo] + cantidades[tipo] for tipo in UNIDADES}
        costo = self.costo_contrato(cantidades)
        atributos = self.calcular_atributos(conteo=despues)
        mensaje = None
        try:
            self.validar_contrato(cantidades)
        except ReglaInvalida as error:
            mensaje = str(error)
        return {
            "valido": mensaje is None,
            "mensaje": mensaje,
            "costo": costo,
            "presupuesto": self.presupuesto,
            "restante": self.presupuesto - costo,
            "integrantes": sum(despues.values()),
            "nuevas": sum(cantidades.values()),
            "atk": atributos.atk_total,
            "def": atributos.def_total,
            "mantenimiento": self.calcular_mantenimiento(despues).total,
            "subtotales": {tipo: cantidades[tipo] * UNIDAD[tipo]["costo"] for tipo in UNIDADES},
        }

    # --- Combate ------------------------------------------------------------------------

    def calcular_atributos(self, estrategia=None, conteo=None):
        """ATK y DEF de la legión con Legatus, formación, sinergias y bono de ingenieros.

        Todas las unidades vivas aportan su ATK y su DEF, salvo la caballería en Orbis, que
        no ataca. conteo permite calcular una composición hipotética (vista previa).
        """
        conteo = self.contar() if conteo is None else conteo
        mod = estrategia.aplicar_modificadores(conteo) if estrategia else Modificadores()
        def_ingenieros, artilleria = Ingeniero.aplicar_bono(conteo["ingeniero"])

        desglose_atk = [("Legatus", self.legatus.bono_atk)]
        desglose_def = [("Legatus", self.legatus.bono_def)]
        if estrategia:
            desglose_atk.append((estrategia.nombre, mod.atk))
            desglose_def.append((estrategia.nombre, mod.defensa))
        if mod.defensa_sinergia:
            desglose_def.append((f"Sinergia {estrategia.nombre}", mod.defensa_sinergia))
        if def_ingenieros:
            desglose_def.append(("Ingenieros", def_ingenieros))
        pct_atk = sum(pct for _, pct in desglose_atk)
        pct_def = sum(pct for _, pct in desglose_def)

        dano_tipo = dict(mod.dano_tipo)
        sinergias = list(mod.sinergias)
        if artilleria:
            dano_tipo["ballesta"] = dano_tipo.get("ballesta", 0) + artilleria
        if def_ingenieros:
            sinergias.append(
                f"{cantidad_tropa('ingeniero', conteo['ingeniero'])}: +{def_ingenieros}% DEF "
                f"y +{artilleria}% de daño de ballestas"
            )

        atk_x100 = sum(conteo[tipo] * CLASES[tipo].atk_base * (100 + pct_atk)
                       for tipo in UNIDADES if tipo not in mod.no_atacan)
        def_x100 = sum(conteo[tipo] * CLASES[tipo].def_base * (100 + pct_def) for tipo in UNIDADES)
        return Atributos(
            estrategia=estrategia, conteo=dict(conteo), pct_atk=pct_atk, pct_def=pct_def,
            desglose_atk=tuple(desglose_atk), desglose_def=tuple(desglose_def),
            dano_tipo=dano_tipo, dano_recibido=mod.dano_recibido,
            no_atacan=mod.no_atacan, inmunes=mod.inmunes, sinergias=tuple(sinergias),
            atk_x100=atk_x100, def_x100=def_x100,
        )

    def filas(self, atributos=None):
        """Tabla dinámica: vivos, heridos, HP, ATK, DEF y sueldo de cada tipo de unidad."""
        atributos = atributos or self.calcular_atributos()
        filas = []
        for tipo in UNIDADES:
            lista = self.unidades[tipo]
            clase = CLASES[tipo]
            filas.append(FilaFuerza(
                tipo=tipo, vivos=len(lista), heridos=self.heridos(tipo),
                hp=sum(unidad.hp for unidad in lista), hp_maximo=len(lista) * clase.hp_base,
                atk_unidad=atributos.atk_unidad(tipo), def_unidad=atributos.def_unidad(tipo),
                atk_total=atributos.atk_tipo(tipo), def_total=atributos.def_tipo(tipo),
                sueldo=len(lista) * clase.costo, ataca=atributos.ataca(tipo),
                inmune=tipo in atributos.inmunes,
            ))
        return filas

    def calcular_mantenimiento(self, conteo=None):
        """Sueldos por turno: costo de catálogo × (100 + %Costo) × (100 − descuento)."""
        conteo = self.contar() if conteo is None else conteo
        base = sum(conteo[tipo] * UNIDAD[tipo]["costo"] for tipo in UNIDADES)
        pct_legatus = self.legatus.bono_costo
        descuento = EsclavoAuxiliar.descuento_mantenimiento(conteo["esclavo"])
        total = dividir_redondeando(base * (100 + pct_legatus) * (100 - descuento), 10_000)
        return Mantenimiento(base, pct_legatus, conteo["esclavo"], descuento, total)

    def pagar_mantenimiento(self):
        """Paga los sueldos del turno si alcanza. Devuelve (Mantenimiento, pagado)."""
        mantenimiento = self.calcular_mantenimiento()
        if mantenimiento.total > self.presupuesto:
            return mantenimiento, False
        self.presupuesto -= mantenimiento.total
        return mantenimiento, True

    # --- Reagrupación -------------------------------------------------------------------

    def validar_conversion(self, cantidades):
        """Esclavos que pasan a legionarios o caballería pagando el precio de su nuevo tipo.

        Devuelve (cantidades, costo) o lanza ReglaInvalida.
        """
        cantidades = normalizar_cantidades(cantidades, EsclavoAuxiliar.DESTINOS)
        total = sum(cantidades.values())
        if total == 0:
            return cantidades, 0
        esclavos = len(self.unidades["esclavo"])
        if total > esclavos:
            raise ReglaInvalida(
                f"{self.nombre} quiere convertir {miles(total)} esclavos y solo tiene {miles(esclavos)}."
            )
        costo = self.costo_contrato(cantidades)
        if costo > self.presupuesto:
            raise ReglaInvalida(
                f"Convertir esos esclavos cuesta {miles(costo)} denarios y {self.nombre} "
                f"tiene {miles(self.presupuesto)}."
            )
        return cantidades, costo

    def convertir_esclavos(self, cantidades):
        """Convierte primero a los esclavos más heridos; las nuevas unidades llegan con HP completo.

        Devuelve (cantidades, costo, hp_esclavos), con el HP que tenían los esclavos convertidos.
        """
        cantidades, costo = self.validar_conversion(cantidades)
        total = sum(cantidades.values())
        if not total:
            return cantidades, 0, 0
        esclavos = self.unidades["esclavo"]
        esclavos.sort(key=lambda unidad: unidad.hp)
        convertidos, self.unidades["esclavo"] = esclavos[:total], esclavos[total:]
        inicio = 0
        for destino in EsclavoAuxiliar.DESTINOS:
            for esclavo in convertidos[inicio:inicio + cantidades[destino]]:
                self.agregar_unidad(esclavo.convertir(destino))
            inicio += cantidades[destino]
        self.presupuesto -= costo
        return cantidades, costo, sum(esclavo.hp for esclavo in convertidos)

    # --- Persistencia -------------------------------------------------------------------

    def a_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "consul": self.consul,
            "legatus": self.legatus.a_dict(),
            "presupuesto": self.presupuesto,
            "asignado": self.asignado,
            "creada": self.creada,
            # Las unidades se guardan agrupadas por HP: 480 legionarios sanos son una sola fila.
            "unidades": {tipo: agrupar_por_hp(lista) for tipo, lista in self.unidades.items()},
        }

    @classmethod
    def desde_dict(cls, datos):
        presupuesto = s.entero(datos, "presupuesto", 0, PRESUPUESTO_MAXIMO)
        legion = cls(
            s.texto(datos, "nombre"), s.entero(datos, "consul", 1, 2),
            Legatus.desde_dict(s.mapa(datos, "legatus")), presupuesto,
            id=s.entero(datos, "id", 1), asignado=s.entero(datos, "asignado", presupuesto, 10 ** 12),
            creada=s.instante(datos, "creada"),
        )
        grupos = s.mapa(datos, "unidades")
        s.exigir(set(grupos) == set(UNIDADES), "unidades debe indicar cada tipo de unidad")
        # Se revisan todas las cifras antes de crear objetos: un archivo alterado no puede
        # pedir millones de unidades.
        total = 0
        leidos = {}
        for tipo in UNIDADES:
            leidos[tipo] = []
            vistos = set()
            for grupo in s.lista(grupos, tipo):
                s.exigir(isinstance(grupo, list) and len(grupo) == 2, f"grupo de {tipo} inválido")
                hp, cantidad = grupo
                s.exigir(type(hp) is int and 1 <= hp <= UNIDAD[tipo]["hp"], f"HP de {tipo} fuera de rango")
                s.exigir(type(cantidad) is int and cantidad >= 1, f"cantidad de {tipo} inválida")
                s.exigir(hp not in vistos, f"HP de {tipo} repetido")
                vistos.add(hp)
                total += cantidad
                s.exigir(total <= INTEGRANTES_MAXIMOS, "la legión supera el máximo de integrantes")
                leidos[tipo].append((hp, cantidad))
        for tipo, lista in leidos.items():
            clase = CLASES[tipo]
            legion.unidades[tipo] = [clase(hp) for hp, cantidad in sorted(lista, reverse=True)
                                     for _ in range(cantidad)]
        return legion
