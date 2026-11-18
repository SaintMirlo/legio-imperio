"""Catálogos de referencia del enunciado oficial de 2026 (tablas 2 y 3) y límites del sistema.

Las clases del modelo leen de aquí sus valores base: si el enunciado cambia una cifra,
basta con corregirla en este archivo.
"""

UNIDADES = ("legionario", "caballeria", "ballesta", "ingeniero", "esclavo")

# Tabla 2 del enunciado: catálogo de unidades militares romanas.
CATALOGO = [
    {
        "clave": "legionario",
        "nombre": "Legionario",
        "plural": "Legionarios",
        "rol": "Infantería pesada disciplinada",
        "habilidad": "Ignora 20% del daño en formaciones cerradas (Triplex Acies y Orbis).",
        "hp": 20, "atk": 25, "def": 35, "costo": 5,
    },
    {
        "clave": "caballeria",
        "nombre": "Caballería",
        "plural": "Caballería",
        "rol": "Fuerza de choque y flanqueo",
        "habilidad": "Su carga causa 20% de daño adicional a los legionarios.",
        "hp": 50, "atk": 45, "def": 15, "costo": 12,
    },
    {
        "clave": "ballesta",
        "nombre": "Ballesta",
        "plural": "Ballestas",
        "rol": "Artillería a distancia",
        "habilidad": "Causa 50% de daño extra a la caballería y puede atacar a cualquier unidad.",
        "hp": 15, "atk": 60, "def": 5, "costo": 20,
    },
    {
        "clave": "ingeniero",
        "nombre": "Ingeniero",
        "plural": "Ingenieros",
        "rol": "Unidad técnica, no ataca",
        "habilidad": "Por cada 10: +1% a la defensa global y +2% de daño de artillería.",
        "hp": 2, "atk": 5, "def": 20, "costo": 10,
    },
    {
        "clave": "esclavo",
        "nombre": "Esclavo / Auxiliar",
        "plural": "Esclavos",
        "rol": "Logística y acarreo, no ataca",
        "habilidad": "Por cada 50: reduce 15% el mantenimiento de la legión. Se puede convertir en legionario o caballería.",
        "hp": 5, "atk": 2, "def": 5, "costo": 1,
    },
]
UNIDAD = {u["clave"]: u for u in CATALOGO}

# Tabla 3 del enunciado: estrategias tácticas.
ESTRATEGIAS = [
    {
        "clave": "triplex",
        "nombre": "Triplex Acies",
        "apodo": "Triple línea",
        "descripcion": "Formación ordenada con ataque y defensa balanceados.",
        "atk": 10, "def": 10,
        "sinergia": "Si ≥50% son legionarios: +35% DEF global y +15% de daño de ballestas.",
        "requisito": "Obligatoria en el primer turno.",
    },
    {
        "clave": "cuneus",
        "nombre": "Cuneus",
        "apodo": "Cuña",
        "descripcion": "Impacto frontal agresivo que requiere caballería.",
        "atk": 45, "def": -25,
        "sinergia": "+50% de daño de caballería, que también alcanza a los esclavos; la legión recibe +50% de daño.",
        "requisito": "Requiere caballería.",
    },
    {
        "clave": "orbis",
        "nombre": "Orbis",
        "apodo": "Círculo defensivo",
        "descripcion": "Formación de legionarios que favorece la defensa.",
        "atk": -35, "def": 60,
        "sinergia": "La caballería no ataca; ballestas e ingenieros no reciben daño.",
        "requisito": "Requiere legionarios.",
    },
]
ESTRATEGIA = {e["clave"]: e for e in ESTRATEGIAS}

# Límites del sistema (decisión de diseño, no del enunciado): evitan cifras absurdas
# y mantienen ágil la simulación, que sigue el HP de cada unidad por separado.
PRESUPUESTO_MAXIMO = 1_000_000
INTEGRANTES_MAXIMOS = 10_000
LEGIONES_MAXIMAS = 30
# Si tras este turno ninguna legión cayó ni quedó sin fondos, el combate termina en empate:
# evita enfrentamientos interminables cuando ninguna defensa cede.
TURNOS_MAXIMOS = 100

TIPOS_EVENTO = {
    "sistema": "Sistema",
    "legion": "Legión",
    "contrato": "Contrato",
    "estrategia": "Estrategia",
    "combate": "Combate",
    "bajas": "Bajas",
    "economia": "Economía",
    "conversion": "Conversión",
    "fin": "Fin",
}

# Momento de un turno en que ocurre cada suceso de la bitácora.
ETAPAS = {None: "—", 0: "Preparación", 1: "Etapa 1", 2: "Etapa 2", 3: "Reagrupación"}
