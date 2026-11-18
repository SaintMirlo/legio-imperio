"""Campaña: el Senado (dos cónsules), sus legiones, sus enfrentamientos y la bitácora.

Es la raíz del modelo. Los controladores le piden cada acción y ella valida las reglas que
involucran a varias legiones: nombres únicos, un solo enfrentamiento a la vez y legiones
bloqueadas mientras combaten. Se guarda y se carga completa (GestorPersistencia y archivos).
"""
import re
import uuid

from modelo import serializacion as s
from modelo.bitacora import Bitacora
from modelo.catalogos import LEGIONES_MAXIMAS, PRESUPUESTO_MAXIMO
from modelo.combate import LADOS, ConsolaDesactualizada, Enfrentamiento, MotorCombate
from modelo.errores import ReglaInvalida, entero_en_rango, texto_requerido
from modelo.estrategias import FORMACION_INICIAL, obtener_estrategia
from modelo.legatus import Legatus
from modelo.legion import Legion
from modelo.textos import ahora, enumerar, miles, tropas_en_texto

ESTADOS_CAMPANA = {"configuracion": "En preparación", "en_combate": "En combate"}


class Campana:
    def __init__(self, id, nombre, consules, *, creada=None, actualizada=None, legiones=(),
                 enfrentamientos=(), bitacora=None, siguiente_legion=1, siguiente_enfrentamiento=1):
        self.id = id
        self.nombre = nombre
        self.consules = list(consules)  # [cónsul 1, cónsul 2]
        self.creada = creada or ahora()
        self.actualizada = actualizada or self.creada
        self.legiones = {legion.id: legion for legion in sorted(legiones, key=lambda l: l.id)}
        self.enfrentamientos = sorted(enfrentamientos, key=lambda e: e.id)
        self.bitacora = bitacora or Bitacora()
        self.siguiente_legion = siguiente_legion
        self.siguiente_enfrentamiento = siguiente_enfrentamiento

    def __repr__(self):
        return f"Campana({self.nombre!r}, {len(self.legiones)} legiones)"

    @classmethod
    def iniciar(cls, nombre, consul_1, consul_2):
        nombre = texto_requerido(nombre, "el nombre de la campaña")
        consules = [texto_requerido(consul_1, "el nombre del primer cónsul"),
                    texto_requerido(consul_2, "el nombre del segundo cónsul")]
        if consules[0].casefold() == consules[1].casefold():
            raise ReglaInvalida("El Senado nombra dos cónsules distintos: escribe dos nombres diferentes.")
        campana = cls(uuid.uuid4().hex, nombre, consules)
        campana.bitacora.registrar_suceso(
            "sistema", f"Comienza la campaña «{nombre}». El Senado nombra cónsules a {consules[0]} y {consules[1]}.")
        return campana

    def guardar(self, gestor):
        gestor.guardar_campana(self)

    @staticmethod
    def cargar(gestor, id_campana):
        return gestor.cargar_campana(id_campana)

    def tocar(self):
        self.actualizada = ahora()

    # --- Consultas ----------------------------------------------------------------------

    @property
    def estado(self):
        """EstadoCampaña: «en_combate» mientras haya un enfrentamiento en curso."""
        return "en_combate" if self.enfrentamiento_activo() else "configuracion"

    def consul_nombre(self, numero):
        return self.consules[numero - 1]

    def legion(self, id_legion):
        """Legión por id; KeyError si no existe."""
        return self.legiones[id_legion]

    def legiones_de_consul(self, numero):
        return [legion for legion in self.legiones.values() if legion.consul == numero]

    def enfrentamiento(self, id_enfrentamiento):
        for enfrentamiento in self.enfrentamientos:
            if enfrentamiento.id == id_enfrentamiento:
                return enfrentamiento
        raise KeyError(id_enfrentamiento)

    def enfrentamiento_activo(self):
        return next((e for e in self.enfrentamientos if e.en_curso), None)

    def ultimo_enfrentamiento(self):
        return self.enfrentamientos[-1] if self.enfrentamientos else None

    def en_combate(self, legion):
        activo = self.enfrentamiento_activo()
        return activo is not None and activo.lado_de(legion.id) is not None

    def legiones_en(self, enfrentamiento):
        """{lado: Legion} de un enfrentamiento en curso."""
        return {lado: self.legiones[p.legion_id] for lado, p in enfrentamiento.participantes.items()}

    def resumen(self):
        """Indicadores del panel de campaña."""
        legiones = list(self.legiones.values())
        return {
            "legiones": len(legiones),
            "listas": sum(1 for legion in legiones if legion.esta_lista()),
            "soldados": sum(legion.integrantes() for legion in legiones),
            "denarios": sum(legion.presupuesto for legion in legiones),
        }

    # --- Legiones -----------------------------------------------------------------------

    def _validar_nombre_legion(self, nombre, excepto=None):
        for legion in self.legiones.values():
            if legion.id != excepto and legion.nombre.casefold() == nombre.casefold():
                raise ReglaInvalida(f"Ya existe una legión llamada «{legion.nombre}» en esta campaña.")

    @staticmethod
    def _validar_consul(consul):
        if consul not in (1, 2):
            raise ReglaInvalida("Elige uno de los dos cónsules de la campaña.")

    def _exigir_fuera_de_combate(self, legion, accion):
        if self.en_combate(legion):
            raise ReglaInvalida(f"{legion.nombre} está en combate: no se puede {accion} hasta que termine "
                                "el enfrentamiento.")

    def crear_legion(self, nombre, consul, legatus_nombre, bono_atk, bono_def, presupuesto):
        """CU001 y CU002: crea la legión con su Legatus y el presupuesto que define el usuario."""
        if len(self.legiones) >= LEGIONES_MAXIMAS:
            raise ReglaInvalida(f"Una campaña admite hasta {LEGIONES_MAXIMAS} legiones.")
        nombre = texto_requerido(nombre, "el nombre de la legión")
        self._validar_nombre_legion(nombre)
        self._validar_consul(consul)
        legatus = Legatus(legatus_nombre, bono_atk, bono_def)
        presupuesto = entero_en_rango(presupuesto, "el presupuesto", 1, PRESUPUESTO_MAXIMO)
        legion = Legion(nombre, consul, legatus, presupuesto, id=self.siguiente_legion)
        self.legiones[legion.id] = legion
        self.siguiente_legion += 1
        self.bitacora.registrar_suceso(
            "legion", f"El cónsul {self.consul_nombre(consul)} nombra a {legatus.describir()} Legatus de "
                      f"la nueva {nombre}, con {miles(presupuesto)} denarios de presupuesto.")
        self.tocar()
        return legion

    def configurar_legion(self, id_legion, nombre, consul, legatus_nombre, bono_atk, bono_def, presupuesto):
        """Cambia nombre, cónsul, Legatus o presupuesto disponible. Devuelve True si hubo cambios."""
        legion = self.legion(id_legion)
        self._exigir_fuera_de_combate(legion, "modificar")
        nombre = texto_requerido(nombre, "el nombre de la legión")
        self._validar_nombre_legion(nombre, excepto=legion.id)
        self._validar_consul(consul)
        legatus = Legatus(legatus_nombre, bono_atk, bono_def)
        presupuesto = entero_en_rango(presupuesto, "el presupuesto", 0, PRESUPUESTO_MAXIMO)

        cambios = []
        if nombre != legion.nombre:
            cambios.append(f"pasa a llamarse {nombre}")
        if consul != legion.consul:
            cambios.append(f"queda bajo el cónsul {self.consul_nombre(consul)}")
        if legatus.a_dict() != legion.legatus.a_dict():
            cambios.append(f"tiene como Legatus a {legatus.describir()}")
        if presupuesto != legion.presupuesto:
            cambios.append(f"su presupuesto pasa de {miles(legion.presupuesto)} a {miles(presupuesto)} denarios")
        if not cambios:
            return False
        anterior = legion.nombre
        legion.nombre, legion.consul, legion.legatus = nombre, consul, legatus
        legion.asignado += presupuesto - legion.presupuesto
        legion.presupuesto = presupuesto
        self.bitacora.registrar_suceso("legion", f"{anterior} {enumerar(cambios)}.")
        self.tocar()
        return True

    def eliminar_legion(self, id_legion):
        legion = self.legion(id_legion)
        self._exigir_fuera_de_combate(legion, "disolver")
        del self.legiones[id_legion]
        self.bitacora.registrar_suceso(
            "legion", f"Se disuelve la {legion.nombre} ({tropas_en_texto(legion.contar(), vacio='sin tropas')}).")
        self.tocar()
        return legion

    def contratar_tropas(self, id_legion, cantidades):
        """CU003: contrata unidades del catálogo con el presupuesto de la legión."""
        legion = self.legion(id_legion)
        if self.en_combate(legion):
            raise ReglaInvalida(f"{legion.nombre} está en combate: contrata refuerzos desde la consola, "
                                "en la preparación de un turno.")
        cantidades, costo = legion.contratar(cantidades)
        self.bitacora.registrar_suceso(
            "contrato", f"{legion.nombre} contrata {tropas_en_texto(cantidades)} por {miles(costo)} denarios. "
                        f"Le quedan {miles(legion.presupuesto)}.")
        self.tocar()
        return cantidades, costo

    # --- Enfrentamientos ----------------------------------------------------------------

    def validar_enfrentamiento(self, id_a, id_b):
        """CU005: [(nivel, texto)] con nivel «error» (impide iniciar), «aviso» u «ok»."""
        activo = self.enfrentamiento_activo()
        if activo:
            return [("error", f"Ya hay un enfrentamiento en curso («{activo.nombre}»): termínalo o "
                              "abandónalo antes de iniciar otro.")]
        if len(self.legiones) < 2:
            return [("error", "Crea al menos dos legiones con tropas para iniciar un enfrentamiento.")]
        legiones = [self.legiones.get(id_a), self.legiones.get(id_b)]
        if None in legiones:
            return [("error", "Elige la legión atacante y la legión defensora.")]
        if id_a == id_b:
            return [("error", "Una legión no puede enfrentarse a sí misma: elige dos legiones distintas.")]
        mensajes = []
        triplex = obtener_estrategia(FORMACION_INICIAL)
        for legion in legiones:
            if not legion.esta_lista():
                mensajes.append(("error", f"{legion.nombre} no tiene legionarios, caballería ni ballestas: "
                                          "contrata tropas que puedan atacar."))
                continue
            sueldos = legion.calcular_mantenimiento().total
            if sueldos > legion.presupuesto:
                mensajes.append(("aviso", f"{legion.nombre} no alcanza a pagar los sueldos del primer turno "
                                          f"({miles(sueldos)} denarios; tiene {miles(legion.presupuesto)}): "
                                          "perderá al cerrar el turno 1."))
            else:
                mensajes.append(("ok", f"{legion.nombre} está lista: paga {miles(sueldos)} denarios de sueldos "
                                       "por turno."))
            conteo = legion.contar()
            if triplex.sinergia_activa(conteo):
                mensajes.append(("ok", f"{legion.nombre} activa la sinergia de Triplex Acies (≥50% legionarios)."))
            else:
                mensajes.append(("aviso", f"{legion.nombre} no activa la sinergia de Triplex Acies: tiene menos "
                                          "de 50% de legionarios."))
        return mensajes

    def comparar(self, id_a, id_b):
        """Vista previa del primer turno (ambas en Triplex Acies): atributos y daño esperado."""
        triplex = obtener_estrategia(FORMACION_INICIAL)
        legiones = {"a": self.legiones.get(id_a), "b": self.legiones.get(id_b)}
        atributos = {lado: legion.calcular_atributos(triplex) for lado, legion in legiones.items() if legion}
        dano = {}
        if len(atributos) == 2 and id_a != id_b:
            dano = {1: MotorCombate.dano_total(atributos["a"], atributos["b"])[1],
                    2: MotorCombate.dano_total(atributos["b"], atributos["a"])[1]}
        return {"legiones": legiones, "atributos": atributos, "dano": dano,
                "mensajes": self.validar_enfrentamiento(id_a, id_b)}

    def iniciar_enfrentamiento(self, nombre, id_a, id_b, semilla=None):
        """CU005: id_a es la legión atacante del primer turno e id_b la defensora."""
        errores = [texto for nivel, texto in self.validar_enfrentamiento(id_a, id_b) if nivel == "error"]
        if errores:
            raise ReglaInvalida(errores[0])
        enfrentamiento = Enfrentamiento.iniciar(self.siguiente_enfrentamiento, nombre, self.legiones[id_a],
                                                self.legiones[id_b], self.bitacora, semilla)
        self.enfrentamientos.append(enfrentamiento)
        self.siguiente_enfrentamiento += 1
        self.tocar()
        return enfrentamiento

    def _exigir_activo(self):
        enfrentamiento = self.enfrentamiento_activo()
        if enfrentamiento is None:
            raise ReglaInvalida("No hay un enfrentamiento en curso.")
        return enfrentamiento

    def avanzar_combate(self, decisiones=None, paso=None):
        """CU006 a CU011: ejecuta el siguiente paso del enfrentamiento en curso.

        paso: los pasos que la consola tenía a la vista; si no coincide, no se avanza.
        """
        enfrentamiento = self._exigir_activo()
        if paso is not None and paso != enfrentamiento.pasos:
            raise ConsolaDesactualizada("La consola mostraba un paso anterior: se actualizó sin avanzar.")
        enfrentamiento.avanzar(self.legiones_en(enfrentamiento), self.bitacora, decisiones)
        self.tocar()
        return enfrentamiento

    def contratar_refuerzos(self, lado, cantidades):
        enfrentamiento = self._exigir_activo()
        if lado not in LADOS:
            raise ReglaInvalida("Elige la legión que recibe los refuerzos.")
        legion = self.legiones[enfrentamiento.participantes[lado].legion_id]
        resultado = enfrentamiento.contratar_refuerzos(lado, legion, cantidades, self.bitacora)
        self.tocar()
        return resultado

    def abandonar_combate(self):
        enfrentamiento = self._exigir_activo()
        enfrentamiento.abandonar(self.legiones_en(enfrentamiento), self.bitacora)
        self.tocar()
        return enfrentamiento

    # --- Persistencia -------------------------------------------------------------------

    def a_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "consules": list(self.consules),
            "creada": self.creada,
            "actualizada": self.actualizada,
            "siguiente_legion": self.siguiente_legion,
            "siguiente_enfrentamiento": self.siguiente_enfrentamiento,
            "legiones": [legion.a_dict() for legion in self.legiones.values()],
            "enfrentamientos": [e.a_dict() for e in self.enfrentamientos],
            "bitacora": self.bitacora.a_lista(),
        }

    @classmethod
    def desde_dict(cls, datos):
        """Reconstruye la campaña validando cada dato y las referencias entre objetos."""
        datos = s.mapa(datos)
        id_campana = s.texto(datos, "id")
        s.exigir(re.fullmatch(r"[0-9a-f]{32}", id_campana), "id de campaña inválido")
        consules = s.lista(datos, "consules")
        s.exigir(len(consules) == 2, "la campaña debe tener dos cónsules")
        consules = [texto_requerido(consul, "el nombre del cónsul") for consul in consules]
        s.exigir(consules[0].casefold() != consules[1].casefold(), "los cónsules deben ser distintos")
        siguiente_legion = s.entero(datos, "siguiente_legion", 1)
        siguiente_enfrentamiento = s.entero(datos, "siguiente_enfrentamiento", 1)

        legiones = [Legion.desde_dict(legion) for legion in s.lista(datos, "legiones")]
        ids = [legion.id for legion in legiones]
        s.exigir(len(legiones) <= LEGIONES_MAXIMAS, "demasiadas legiones")
        s.exigir(len(set(ids)) == len(ids) and all(i < siguiente_legion for i in ids), "ids de legión inválidos")
        nombres = [legion.nombre.casefold() for legion in legiones]
        s.exigir(len(set(nombres)) == len(nombres), "hay dos legiones con el mismo nombre")

        enfrentamientos = [Enfrentamiento.desde_dict(e) for e in s.lista(datos, "enfrentamientos")]
        ids_enfrentamiento = [e.id for e in enfrentamientos]
        s.exigir(len(set(ids_enfrentamiento)) == len(ids_enfrentamiento)
                 and all(i < siguiente_enfrentamiento for i in ids_enfrentamiento), "ids de enfrentamiento inválidos")
        activos = [e for e in enfrentamientos if e.en_curso]
        s.exigir(len(activos) <= 1, "solo puede haber un enfrentamiento en curso")
        for activo in activos:
            s.exigir(all(p.legion_id in ids for p in activo.participantes.values()),
                     "el enfrentamiento en curso nombra una legión que no existe")

        bitacora = Bitacora.desde_lista(datos.get("bitacora"))
        s.exigir(all(e.enfrentamiento is None or e.enfrentamiento in ids_enfrentamiento for e in bitacora.eventos),
                 "la bitácora nombra un enfrentamiento que no existe")
        return cls(
            id_campana, texto_requerido(s.texto(datos, "nombre"), "el nombre de la campaña"), consules,
            creada=s.instante(datos, "creada"), actualizada=s.instante(datos, "actualizada"),
            legiones=legiones, enfrentamientos=enfrentamientos, bitacora=bitacora,
            siguiente_legion=siguiente_legion, siguiente_enfrentamiento=siguiente_enfrentamiento,
        )
