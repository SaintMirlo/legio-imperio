"""Archivos de campaña (RU009 y RU010): la campaña completa en un JSON que el usuario guarda
en su equipo y puede volver a cargar.

El archivo incluye legiones, Legatus, tropas con su HP, enfrentamientos con todos sus turnos
y la bitácora. Al cargarlo se valida cada dato antes de reconstruir los objetos.
"""
import json
import re
import unicodedata
from datetime import datetime

from modelo.campana import Campana
from modelo.errores import ArchivoCampanaInvalido
from modelo.textos import ahora

FORMATO = "legio-imperium"
VERSION = 2


def exportar_campana(campana):
    """Texto JSON del archivo de campaña."""
    contenido = {"formato": FORMATO, "version": VERSION, "guardada": ahora(), "campana": campana.a_dict()}
    return json.dumps(contenido, ensure_ascii=False, indent=2)


def importar_campana(contenido):
    """Campaña reconstruida desde el contenido del archivo (bytes o texto)."""
    try:
        if isinstance(contenido, bytes):
            contenido = contenido.decode("utf-8-sig")
        datos = json.loads(contenido)
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise ArchivoCampanaInvalido("El archivo no contiene un JSON válido.") from None
    if not isinstance(datos, dict) or datos.get("formato") != FORMATO:
        raise ArchivoCampanaInvalido("Ese archivo no es una campaña de Legio Imperium.")
    version = datos.get("version")
    if version == 1:
        raise ArchivoCampanaInvalido(
            "Ese archivo es del prototipo del Hito 2: solo trae datos de ejemplo y no contiene una partida "
            "que se pueda restaurar.")
    if version != VERSION:
        raise ArchivoCampanaInvalido("La versión del archivo no es compatible con esta versión de Legio Imperium.")
    try:
        return Campana.desde_dict(datos.get("campana"))
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as error:
        raise ArchivoCampanaInvalido(f"El archivo está dañado o fue modificado ({error}).") from None


def prefijo_archivo(nombre_campana):
    """'legio-imperium-guerra-civil' (sin tildes ni símbolos, apto para cualquier sistema)."""
    simple = unicodedata.normalize("NFKD", nombre_campana).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", simple.lower()).strip("-")[:40].strip("-") or "campana"
    return f"legio-imperium-{slug}"


def nombre_archivo(campana, instante=None):
    """'legio-imperium-guerra-civil-2026-11-17-1830.json'."""
    marca = (instante or datetime.now()).strftime("%Y-%m-%d-%H%M")
    return f"{prefijo_archivo(campana.nombre)}-{marca}.json"
