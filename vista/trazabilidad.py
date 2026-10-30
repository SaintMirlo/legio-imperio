"""Nombres de los casos de uso y requisitos que citan las pantallas (trazabilidad con el informe).

Los casos de uso siguen el diagrama de casos de uso; los requisitos, la sección 3 del informe.
Al pasar el mouse por un código de la etiqueta de una pantalla se ve su nombre.
"""

CASOS_DE_USO = {
    "CU001": "Crear y organizar legiones",
    "CU002": "Asignar Legatus y presupuesto",
    "CU003": "Contratar tropas del catálogo",
    "CU004": "Revisar fuerzas y recursos",
    "CU005": "Preparar un enfrentamiento",
    "CU006": "Elegir la formación del turno",
    "CU007": "Desarrollar el combate por turnos",
    "CU008": "Calcular efectos de ataque y bajas",
    "CU009": "Cobrar mantenimiento de legiones",
    "CU010": "Anotar sucesos en la bitácora",
    "CU011": "Reorganizar el ejército",
    "CU012": "Examinar el registro de batalla",
    "CU013": "Guardar el progreso de campaña",
    "CU014": "Recuperar una campaña",
}

REQUISITOS = {
    "RU001": "Crear y configurar legiones",
    "RU002": "Contratar tropas del catálogo",
    "RU003": "Calcular y consultar estadísticas de las legiones",
    "RU004": "Preparar enfrentamiento",
    "RU005": "Elegir la formación del turno",
    "RU006": "Desarrollar el combate por turnos",
    "RU007": "Reorganizar el ejército",
    "RU008": "Consultar la bitácora de batalla",
    "RU009": "Guardar el progreso de campaña",
    "RU010": "Recuperar una campaña guardada",
}


def registrar_trazabilidad(app):
    app.jinja_env.globals["trazabilidad"] = CASOS_DE_USO | REQUISITOS
