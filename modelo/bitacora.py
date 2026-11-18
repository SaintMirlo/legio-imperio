"""Bitácora de campaña: registro cronológico de cada suceso (RU008).

Cada evento indica su tipo, el enfrentamiento, el turno y la etapa en que ocurrió, para que
el visor pueda filtrarlos.
"""
from dataclasses import dataclass

from modelo import serializacion as s
from modelo.catalogos import ETAPAS, TIPOS_EVENTO
from modelo.textos import ahora


@dataclass(frozen=True)
class EventoBatalla:
    numero: int
    instante: str
    tipo: str
    texto: str
    turno: int = 0                 # 0: fuera de un turno de combate
    etapa: int | None = None       # 0 preparación, 1 y 2 etapas, 3 reagrupación
    enfrentamiento: int | None = None

    @property
    def tipo_nombre(self):
        return TIPOS_EVENTO[self.tipo]

    @property
    def etapa_nombre(self):
        return ETAPAS[self.etapa]

    def a_dict(self):
        return {
            "numero": self.numero, "instante": self.instante, "tipo": self.tipo, "texto": self.texto,
            "turno": self.turno, "etapa": self.etapa, "enfrentamiento": self.enfrentamiento,
        }

    @classmethod
    def desde_dict(cls, datos):
        etapa = s.entero(datos, "etapa", nulo=True)
        s.exigir(etapa in ETAPAS, "etapa desconocida")
        return cls(
            numero=s.entero(datos, "numero", 1),
            instante=s.instante(datos, "instante"),
            tipo=s.texto(datos, "tipo", opciones=TIPOS_EVENTO),
            texto=s.texto(datos, "texto"),
            turno=s.entero(datos, "turno", 0),
            etapa=etapa,
            enfrentamiento=s.entero(datos, "enfrentamiento", 1, nulo=True),
        )


class Bitacora:
    def __init__(self, eventos=None):
        self.eventos = list(eventos or [])

    def __len__(self):
        return len(self.eventos)

    def registrar_suceso(self, tipo, texto, *, turno=0, etapa=None, enfrentamiento=None):
        if tipo not in TIPOS_EVENTO:
            raise ValueError(f"Tipo de evento desconocido: {tipo}")
        evento = EventoBatalla(len(self.eventos) + 1, ahora(), tipo, texto, turno, etapa, enfrentamiento)
        self.eventos.append(evento)
        return evento

    def obtener_historial(self, enfrentamiento=None, turno=None, tipo=None, texto=None, desde=0):
        """Eventos en orden cronológico, filtrados por enfrentamiento, turno, tipo o texto.

        desde: solo los eventos con número mayor (para pedir lo nuevo de la consola).
        """
        buscado = (texto or "").casefold()
        return [
            evento for evento in self.eventos
            if evento.numero > desde
            and (enfrentamiento is None or evento.enfrentamiento == enfrentamiento)
            and (turno is None or evento.turno == turno)
            and (tipo is None or evento.tipo == tipo)
            and (not buscado or buscado in evento.texto.casefold())
        ]

    def a_lista(self):
        return [evento.a_dict() for evento in self.eventos]

    @classmethod
    def desde_lista(cls, datos):
        s.exigir(isinstance(datos, list), "bitacora debe ser una lista")
        eventos = [EventoBatalla.desde_dict(evento) for evento in datos]
        s.exigir([e.numero for e in eventos] == list(range(1, len(eventos) + 1)),
                 "los eventos de la bitácora deben estar numerados en orden")
        return cls(eventos)
