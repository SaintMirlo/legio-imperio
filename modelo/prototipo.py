"""Consultas y archivos del escenario fijo del Hito 2, independientes de Flask.

Este repositorio permite cambiar la fuente de datos sin reescribir las rutas.
No calcula combates, no guarda formularios ni implementa la base de datos del Hito 3.
"""
from copy import deepcopy
from datetime import datetime, timezone

from modelo import datos_prototipo as datos
from modelo.catalogos import UNIDADES


class ArchivoCampanaInvalido(ValueError):
    """El JSON no tiene la estructura de un archivo de campaña compatible."""


class RepositorioPrototipo:
    def __init__(self):
        self._datos = deepcopy({
            "campana": datos.CAMPANA,
            "recientes": datos.CAMPANAS_RECIENTES,
            "legiones": datos.LEGIONES,
            "batalla": datos.BATALLA,
            "pasos": datos.PASOS,
            "validaciones": datos.VALIDACIONES_ENFRENTAMIENTO,
            "reagrupacion": datos.REAGRUPACION,
            "refuerzos": datos.REFUERZOS,
            "resultado": datos.RESULTADO,
            "eventos": datos.EVENTOS,
        })

    def campana(self):
        return deepcopy(self._datos["campana"])

    def recientes(self):
        return deepcopy(self._datos["recientes"])

    def legion(self, id_legion):
        return deepcopy(self._datos["legiones"][id_legion])

    def contexto_campana(self):
        return {clave: deepcopy(self._datos[clave]) for clave in ("campana", "legiones")}

    def contexto_batalla(self):
        return self.contexto_campana() | {"batalla": deepcopy(self._datos["batalla"])}

    def paso(self, numero):
        if type(numero) is not int or not 0 <= numero < self.cantidad_pasos:
            raise IndexError("Paso inexistente en el recorrido del prototipo")
        return deepcopy(self._datos["pasos"][numero])

    @property
    def cantidad_pasos(self):
        return len(self._datos["pasos"])

    def validaciones(self):
        return deepcopy(self._datos["validaciones"])

    def reagrupacion(self):
        return deepcopy(self._datos["reagrupacion"])

    def refuerzo(self, id_legion):
        return deepcopy(self._datos["refuerzos"]["legiones"][id_legion])

    def resultado(self):
        return deepcopy(self._datos["resultado"])

    def eventos(self, hasta=None, solo=None):
        eventos = self._datos["eventos"]
        if hasta is not None:
            eventos = [e for e in eventos if e["paso"] is not None and e["paso"] <= hasta]
        if solo is not None:
            eventos = [e for e in eventos if e["paso"] == solo]
        return deepcopy(eventos)

    def archivo_de_ejemplo(self):
        """Exporta la configuración inicial, sin mezclar tropas iniciales y turnos futuros."""
        return {
            "formato": "legio-imperium",
            "version": 1,
            "modo": "prototipo-hito-2",
            "guardada": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "campana": self._datos["campana"]["nombre"],
            "consules": deepcopy(self._datos["campana"]["consules"]),
            "legiones": [
                {clave: deepcopy(legion[clave]) for clave in
                 ("id", "nombre", "consul", "legatus", "presupuesto", "tropas")}
                for legion in self._datos["legiones"].values()
            ],
            "batalla": None,
            "bitacora": [
                {clave: e[clave] for clave in ("instante", "turno", "etapa", "tipo", "texto")}
                for e in self._datos["eventos"] if e["turno"] == 0
            ],
        }


def validar_archivo_campana(contenido):
    """Comprueba el formato, nunca deserializa objetos ni restaura una simulación."""
    def exigir(condicion):
        if not condicion:
            raise ArchivoCampanaInvalido(
                "El archivo no tiene una estructura de campaña compatible con Legio Imperium."
            )

    def texto(valor):
        return isinstance(valor, str) and bool(valor.strip())

    def entero(valor):
        return type(valor) is int and valor >= 0

    exigir(isinstance(contenido, dict))
    exigir(contenido.get("formato") == "legio-imperium")
    exigir(type(contenido.get("version")) is int and contenido["version"] == 1)
    exigir(texto(contenido.get("campana")))
    legiones = contenido.get("legiones")
    exigir(isinstance(legiones, list) and bool(legiones))
    ids = set()
    for legion in legiones:
        exigir(isinstance(legion, dict))
        exigir(all(texto(legion.get(c)) for c in ("id", "nombre", "consul")))
        exigir(legion["id"] not in ids)
        ids.add(legion["id"])
        exigir(entero(legion.get("presupuesto")))
        legatus = legion.get("legatus")
        exigir(isinstance(legatus, dict) and texto(legatus.get("nombre")))
        exigir(all(type(legatus.get(c)) is int for c in ("atk", "def", "costo")))
        tropas = legion.get("tropas")
        exigir(isinstance(tropas, dict) and set(tropas) == set(UNIDADES))
        exigir(all(entero(cantidad) for cantidad in tropas.values()))
    exigir(isinstance(contenido.get("consules"), list) and len(contenido["consules"]) == 2)
    duenos = {legion["id"]: legion["consul"] for legion in legiones}
    asignadas = []
    for consul in contenido["consules"]:
        exigir(isinstance(consul, dict) and texto(consul.get("nombre")))
        exigir(isinstance(consul.get("legiones"), list))
        exigir(all(texto(id_legion) and id_legion in ids for id_legion in consul["legiones"]))
        exigir(all(duenos[id_legion] == consul["nombre"] for id_legion in consul["legiones"]))
        asignadas.extend(consul["legiones"])
    exigir(len(asignadas) == len(set(asignadas)) and set(asignadas) == ids)
    exigir(isinstance(contenido.get("bitacora"), list))
    for evento in contenido["bitacora"]:
        exigir(isinstance(evento, dict))
        exigir(all(texto(evento.get(c)) for c in ("instante", "tipo", "texto")))
        exigir(entero(evento.get("turno")))
        exigir(evento.get("etapa") is None or (entero(evento["etapa"]) and evento["etapa"] <= 3))
    exigir("batalla" in contenido and (contenido["batalla"] is None or isinstance(contenido["batalla"], dict)))
    if contenido["batalla"] is not None:
        batalla = contenido["batalla"]
        exigir(texto(batalla.get("nombre")) and entero(batalla.get("turno")))
        exigir(entero(batalla.get("etapa")) and batalla["etapa"] <= 3)
    return contenido["campana"]
