"""Nombres de los casos de uso y requisitos que citan las pantallas (trazabilidad con el informe).

Los casos de uso siguen el diagrama de casos de uso nuevo; los requisitos, el cuadro 5 del informe.
Al pasar el mouse por un código de la etiqueta de una pantalla se ve su nombre.
"""

CASOS_DE_USO = {
    "CU001": "Crear legiones",
    "CU002": "Asignar Legatus y presupuesto",
    "CU003": "Contratar tropas del catálogo",
    "CU004": "Revisar fuerzas y recursos",
    "CU005": "Preparar un enfrentamiento",
    "CU006": "Elegir la formación del turno",
    "CU007": "Desarrollar el combate de turnos",
    "CU008": "Calcular efectos de ataque y bajas",
    "CU009": "Cobrar mantenimiento de legiones",
    "CU010": "Anotar sucesos en la bitácora",
    "CU011": "Reorganizar el ejército",
    "CU012": "Examinar el registro de batalla",
    "CU013": "Guardar el progreso de campaña",
    "CU014": "Recuperar una campaña",
}

REQUISITOS = {
    "RU001": "Crear legiones",
    "RU002": "Contratar tropas",
    "RU003": "Revisar fuerzas",
    "RU004": "Preparar enfrentamiento",
    "RU005": "Elegir formación",
    "RU006": "Combate por turnos",
    "RU007": "Reorganizar el ejército",
    "RU008": "Bitácora de batalla",
    "RU009": "Guardar campaña",
    "RU010": "Recuperar campaña",
}


def registrar_trazabilidad(app):
    app.jinja_env.globals["trazabilidad"] = CASOS_DE_USO | REQUISITOS
