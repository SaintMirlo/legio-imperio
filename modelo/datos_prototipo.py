"""Datos fijos del prototipo navegable (Hito 2).

Las pantallas del Hito 2 no calculan nada: muestran estos valores escritos a mano.
En el Hito 3 este módulo se reemplaza por las clases del diagrama de clases
(Campaña, Legión, Legatus, UnidadMilitar, MotorCombate, Bitácora...) y la base de datos.

Las cifras siguen las reglas del enunciado para que la batalla de ejemplo sea creíble:
la Legio XIII Gemina gana en el turno 2 porque la Legio I Pompeiana ya no puede pagar
los sueldos de sus soldados.
"""

from modelo.catalogos import UNIDADES


def _tropas(legionarios, caballeria, ballestas, ingenieros, esclavos):
    return dict(zip(UNIDADES, (legionarios, caballeria, ballestas, ingenieros, esclavos)))


def _fuerzas(*filas):
    claves = ("tipo", "vivos", "hp", "atk", "def", "sueldo")
    return [dict(zip(claves, fila)) for fila in filas]


def _evento(hora, turno, etapa, tipo, texto, paso=None):
    """paso: desde qué paso de la consola de batalla se ve el evento (None = solo bitácora)."""
    return {
        "instante": f"29-10-2026 {hora}",
        "turno": turno,
        "etapa": etapa,
        "tipo": tipo,
        "texto": texto,
        "paso": paso,
    }


CAMPANA = {
    "nombre": "Guerra Civil — 49 a.C.",
    "archivo": "guerra-civil-49ac.json",
    "creada": "29-10-2026",
    "senado": "Senatus Populusque Romanus",
    "consules": [
        {"nombre": "Cayo Julio César", "legiones": ["xiii", "x"]},
        {"nombre": "Cneo Pompeyo Magno", "legiones": ["i", "ix"]},
    ],
}

CAMPANAS_RECIENTES = [
    {"nombre": "Guerra Civil — 49 a.C.", "detalle": "4 legiones · Batalla de Farsalia en el turno 2", "guardada": "29-10-2026 18:33"},
    {"nombre": "Conquista de las Galias", "detalle": "3 legiones · 5 batallas terminadas", "guardada": "22-10-2026 21:10"},
    {"nombre": "Prueba de formaciones", "detalle": "2 legiones · sin batallas", "guardada": "18-10-2026 16:45"},
]

# Estado de cada legión antes de la batalla. Fuera de combate solo cuentan los bonos
# del Legatus y de los ingenieros; las formaciones se aplican en la consola de batalla.
LEGIONES = {
    "xiii": {
        "id": "xiii",
        "nombre": "Legio XIII Gemina",
        "consul": "Cayo Julio César",
        "legatus": {"nombre": "Marco Antonio", "atk": 10, "def": 5, "costo": 15},
        "estado": "lista",
        "presupuesto_inicial": 20000,
        "presupuesto": 12050,
        "tropas": _tropas(500, 200, 120, 50, 150),
        "contrato": {"cantidades": _tropas(500, 200, 120, 50, 150), "unidades": 1020, "costo": 7950, "saldo": 12050},
        "fuerzas": _fuerzas(
            ("legionario", 500, 10000, 13750, 19250, 2500),
            ("caballeria", 200, 10000, 9900, 3300, 2400),
            ("ballesta", 120, 1800, 7920, 660, 2400),
            ("ingeniero", 50, 100, 275, 1100, 500),
            ("esclavo", 150, 750, 330, 825, 150),
        ),
        "totales": {"soldados": 1020, "hp": 22650, "atk": 32175, "def": 25135},
        "mantenimiento": {"base": 7950, "legatus": 1193, "esclavos": 150, "esclavos_pct": 45, "descuento": 4114, "total": 5029},
        "sinergias": [
            "Legatus Marco Antonio: +10% ATK y +5% DEF.",
            "Ingenieros (50): +5% DEF global y +10% de daño de ballestas.",
            "Esclavos (150): −45% de mantenimiento.",
            "Triplex Acies sin sinergia: 49,0% de legionarios (se requiere 50%).",
        ],
    },
    "x": {
        "id": "x",
        "nombre": "Legio X Equestris",
        "consul": "Cayo Julio César",
        "legatus": {"nombre": "Décimo Bruto", "atk": 25, "def": 0, "costo": 25},
        "estado": "lista",
        "presupuesto_inicial": 15000,
        "presupuesto": 8300,
        "tropas": _tropas(300, 300, 60, 30, 100),
        "contrato": {"cantidades": _tropas(300, 300, 60, 30, 100), "unidades": 790, "costo": 6700, "saldo": 8300},
        "fuerzas": _fuerzas(
            ("legionario", 300, 6000, 9375, 10815, 1500),
            ("caballeria", 300, 15000, 16875, 4635, 3600),
            ("ballesta", 60, 900, 4500, 309, 1200),
            ("ingeniero", 30, 60, 188, 618, 300),
            ("esclavo", 100, 500, 250, 515, 100),
        ),
        "totales": {"soldados": 790, "hp": 22460, "atk": 31188, "def": 16892},
        "mantenimiento": {"base": 6700, "legatus": 1675, "esclavos": 100, "esclavos_pct": 30, "descuento": 2513, "total": 5862},
        "sinergias": [
            "Legatus Décimo Bruto: +25% ATK.",
            "Ingenieros (30): +3% DEF global y +6% de daño de ballestas.",
            "Esclavos (100): −30% de mantenimiento.",
            "Cuneus disponible: 300 de caballería.",
            "Triplex Acies sin sinergia: 38,0% de legionarios (se requiere 50%).",
        ],
    },
    "i": {
        "id": "i",
        "nombre": "Legio I Pompeiana",
        "consul": "Cneo Pompeyo Magno",
        "legatus": {"nombre": "Tito Labieno", "atk": 20, "def": 5, "costo": 25},
        "estado": "lista",
        "presupuesto_inicial": 16000,
        "presupuesto": 8500,
        "tropas": _tropas(480, 250, 100, 0, 100),
        "contrato": {"cantidades": _tropas(480, 250, 100, 0, 100), "unidades": 930, "costo": 7500, "saldo": 8500},
        "fuerzas": _fuerzas(
            ("legionario", 480, 9600, 14400, 17640, 2400),
            ("caballeria", 250, 12500, 13500, 3938, 3000),
            ("ballesta", 100, 1500, 7200, 525, 2000),
            ("ingeniero", 0, 0, 0, 0, 0),
            ("esclavo", 100, 500, 240, 525, 100),
        ),
        "totales": {"soldados": 930, "hp": 24100, "atk": 35340, "def": 22628},
        "mantenimiento": {"base": 7500, "legatus": 1875, "esclavos": 100, "esclavos_pct": 30, "descuento": 2813, "total": 6562},
        "sinergias": [
            "Legatus Tito Labieno: +20% ATK y +5% DEF.",
            "Esclavos (100): −30% de mantenimiento.",
            "Triplex Acies con sinergia: 51,6% de legionarios (+35% DEF global).",
            "Sin ingenieros: no recibe bonos técnicos.",
        ],
    },
    "ix": {
        "id": "ix",
        "nombre": "Legio IX Hispana",
        "consul": "Cneo Pompeyo Magno",
        "legatus": {"nombre": "Lucio Afranio", "atk": -20, "def": 20, "costo": 0},
        "estado": "sin_tropas",
        "presupuesto_inicial": 10000,
        "presupuesto": 10000,
        "tropas": _tropas(0, 0, 0, 0, 0),
        # Propuesta que excede el presupuesto: sirve para mostrar el mensaje de error.
        "contrato": {"cantidades": _tropas(800, 400, 150, 0, 200), "unidades": 1550, "costo": 12000, "saldo": -2000},
        "fuerzas": [],
        "totales": {"soldados": 0, "hp": 0, "atk": 0, "def": 0},
        "mantenimiento": {"base": 12000, "legatus": 0, "esclavos": 200, "esclavos_pct": 60, "descuento": 7200, "total": 4800},
        "sinergias": [],
    },
}

BATALLA = {
    "nombre": "Batalla de Farsalia",
    "legiones": ("xiii", "i"),  # la primera es la atacante inicial
    "hp_inicial": {"xiii": 22650, "i": 24100},
    "tropas_iniciales": {"xiii": _tropas(500, 200, 120, 50, 150), "i": _tropas(480, 250, 100, 0, 100)},
}

VALIDACIONES_ENFRENTAMIENTO = [
    ("ok", "Hay 3 legiones con tropas; se necesitan al menos 2."),
    ("ok", "Legio XIII Gemina y Legio I Pompeiana tienen unidades que pueden atacar."),
    ("ok", "Ambas pueden pagar los sueldos estimados del primer turno: 5.029 y 6.562 denarios."),
    ("aviso", "La Legio IX Hispana no tiene tropas y no puede entrar en combate."),
]

# Fotografías de la batalla que recorre la consola con «Paso a paso» o «Automático».
# El daño de cada etapa usa el ATK del atacante y la DEF del defensor al inicio de la etapa.
_XIII_T1 = {
    "formacion": "triplex",
    "vivos": _tropas(500, 200, 120, 50, 150),
    "hp": 22650, "atk": 35100, "def": 27420, "presupuesto": 12050,
    "sinergias": ["Triplex Acies: +10% ATK y +10% DEF", "Sin sinergia Triplex (49,0% legionarios)", "Ingenieros: +5% DEF"],
}
_I_T1_INICIO = {
    "formacion": "triplex",
    "vivos": _tropas(480, 250, 100, 0, 100),
    "hp": 24100, "atk": 38285, "def": 32325, "presupuesto": 8500,
    "sinergias": ["Triplex Acies: +10% ATK y +10% DEF", "Sinergia Triplex: +35% DEF (51,6% legionarios)"],
}
_I_T1_FIN = {
    "formacion": "triplex",
    "vivos": _tropas(442, 228, 94, 0, 100),
    "hp": 21510, "atk": 35295, "def": 29790, "presupuesto": 8500,
    "sinergias": ["Triplex Acies: +10% ATK y +10% DEF", "Sinergia Triplex: +35% DEF (51,2% legionarios)"],
}
_XIII_T2_INICIO = {
    "formacion": "cuneus",
    "vivos": _tropas(484, 173, 111, 48, 100),
    "hp": 19191, "atk": 41827, "def": 18102, "presupuesto": 6097,
    "sinergias": ["Cuneus: +45% ATK y −25% DEF", "Caballería: +50% de daño", "Recibe +50% de daño", "Ingenieros: +4% DEF"],
    "validacion": "✓ Cuneus requiere caballería: la legión tiene 173.",
}
_I_T2 = {
    "formacion": "triplex",
    "vivos": _tropas(442, 228, 94, 0, 100),
    "hp": 21510, "atk": 35295, "def": 29790, "presupuesto": 2439,
    "sinergias": ["Triplex Acies: +10% ATK y +10% DEF", "Sinergia Triplex: +35% DEF (51,2% legionarios)"],
    "validacion": "✓ Triplex Acies con sinergia: 51,2% de legionarios.",
}
_I_T2_FIN = {
    "formacion": "triplex",
    "vivos": _tropas(346, 170, 83, 0, 86),
    "hp": 15155, "atk": 27888, "def": 23258, "presupuesto": 2439,
    "sinergias": ["Triplex Acies: +10% ATK y +10% DEF", "Sinergia Triplex: +35% DEF (50,5% legionarios)"],
}

PASOS = [
    {
        "turno": 1, "etapa": 0, "titulo": "Turno 1 · Preparación",
        "atacante": "xiii", "defensor": "i", "formaciones_editables": False,
        "nota": "En el primer turno ambas legiones forman en Triplex Acies. Ataca primero la Legio XIII Gemina.",
        "estado": {"xiii": _XIII_T1, "i": _I_T1_INICIO},
        "resultado": None,
    },
    {
        "turno": 1, "etapa": 1, "titulo": "Turno 1 · Etapa 1",
        "atacante": "xiii", "defensor": "i", "formaciones_editables": False,
        "estado": {"xiii": _XIII_T1, "i": _I_T1_FIN},
        "resultado": {
            "atk": 35100, "def": 32325, "dano_base": 2775, "dano": 2775, "modificador": None,
            "reparto": [("legionario", 61.0, 1692), ("caballeria", 24.4, 677), ("ballesta", 14.6, 406)],
            "bajas": _tropas(38, 22, 6, 0, 0),
        },
    },
    {
        "turno": 1, "etapa": 2, "titulo": "Turno 1 · Etapa 2",
        "atacante": "i", "defensor": "xiii", "formaciones_editables": False,
        "estado": {
            "xiii": {
                "formacion": "triplex",
                "vivos": _tropas(439, 173, 111, 48, 145),
                "hp": 18516, "atk": 31140, "def": 24038, "presupuesto": 12050,
                "sinergias": ["Triplex Acies: +10% ATK y +10% DEF", "Sin sinergia Triplex (47,9% legionarios)", "Ingenieros: +4% DEF"],
            },
            "i": _I_T1_FIN,
        },
        "resultado": {
            "atk": 35295, "def": 27420, "dano_base": 7875, "dano": 7875, "modificador": None,
            "reparto": [("legionario", 57.9, 4556), ("caballeria", 29.8, 2350), ("ballesta", 12.3, 969)],
            "bajas": _tropas(61, 27, 9, 2, 5),
        },
    },
    {
        "turno": 2, "etapa": 0, "titulo": "Turno 2 · Preparación",
        "atacante": "xiii", "defensor": "i", "formaciones_editables": True,
        "nota": "Elige la formación de cada legión. Quedará fija hasta el final del turno.",
        "estado": {"xiii": _XIII_T2_INICIO, "i": _I_T2},
        "resultado": None,
    },
    {
        "turno": 2, "etapa": 1, "titulo": "Turno 2 · Etapa 1",
        "atacante": "xiii", "defensor": "i", "formaciones_editables": False,
        "estado": {"xiii": _XIII_T2_INICIO, "i": _I_T2_FIN},
        "resultado": {
            "atk": 41827, "def": 29790, "dano_base": 12037, "dano": 13393,
            "modificador": "Cuneus: la caballería causa +50% de daño",
            "reparto": [("legionario", 63.0, 7586), ("caballeria", 22.5, 4067), ("ballesta", 14.5, 1740)],
            "bajas": _tropas(96, 58, 11, 0, 14),
        },
    },
    {
        "turno": 2, "etapa": 2, "titulo": "Turno 2 · Etapa 2",
        "atacante": "i", "defensor": "xiii", "formaciones_editables": False,
        "estado": {
            "xiii": {
                "formacion": "cuneus",
                "vivos": _tropas(396, 127, 97, 45, 94),
                "hp": 12985, "atk": 33864, "def": 14801, "presupuesto": 6097,
                "sinergias": ["Cuneus: +45% ATK y −25% DEF", "Caballería: +50% de daño", "Recibe +50% de daño", "Ingenieros: +4% DEF"],
            },
            "i": _I_T2_FIN,
        },
        "resultado": {
            "atk": 27888, "def": 18102, "dano_base": 9786, "dano": 14679,
            "modificador": "Cuneus: la legión en cuña recibe +50% de daño",
            "reparto": [("legionario", 57.8, 8479), ("caballeria", 28.4, 4166), ("ballesta", 13.9, 2034)],
            "bajas": _tropas(88, 46, 14, 3, 6),
        },
    },
]

# Fin del turno 1: sueldos pagados (tipo, vivos, costo, subtotal) y conversión de esclavos.
REAGRUPACION = {
    "turno": 1,
    "legiones": {
        "xiii": {
            "sueldos": [("legionario", 439, 5, 2195), ("caballeria", 173, 12, 2076), ("ballesta", 111, 20, 2220),
                        ("ingeniero", 48, 10, 480), ("esclavo", 145, 1, 145)],
            "base": 7116, "legatus_pct": 15, "legatus": 1067,
            "esclavos": 145, "esclavos_pct": 30, "descuento": 2455, "total": 5728,
            "presupuesto_antes": 12050, "presupuesto_despues": 6322,
            "conversion": {"legionario": 45, "caballeria": 0, "costo": 225, "saldo": 6097},
            "nota": "Al convertir 45 esclavos quedan 100: se mantiene el descuento de −30% en los sueldos.",
            "aviso": None,
        },
        "i": {
            "sueldos": [("legionario", 442, 5, 2210), ("caballeria", 228, 12, 2736), ("ballesta", 94, 20, 1880),
                        ("ingeniero", 0, 10, 0), ("esclavo", 100, 1, 100)],
            "base": 6926, "legatus_pct": 25, "legatus": 1732,
            "esclavos": 100, "esclavos_pct": 30, "descuento": 2597, "total": 6061,
            "presupuesto_antes": 8500, "presupuesto_despues": 2439,
            "conversion": {"legionario": 0, "caballeria": 0, "costo": 0, "saldo": 2439},
            "nota": None,
            "aviso": "Con 2.439 denarios no alcanza para los sueldos del turno 2 (6.061 con las tropas actuales).",
        },
    },
}

# Contratar tropas al elegir la formación del turno 2 (CU003 extiende CU006): cada legión
# contrata con los denarios que le quedan. La propuesta parte vacía, y los sueldos estimados
# del turno son los de sus tropas actuales.
REFUERZOS = {
    "turno": 2,
    "legiones": {
        "xiii": {
            "presupuesto": 6097,
            "contrato": {"cantidades": _tropas(0, 0, 0, 0, 0), "unidades": 0, "costo": 0, "saldo": 6097},
            "mantenimiento": {"base": 7296, "legatus": 1094, "esclavos": 100, "esclavos_pct": 30, "descuento": 2517, "total": 5873},
            "nota": "Tras los sueldos estimados le quedarían 224 denarios, y cada soldado nuevo también cobra sueldo al cerrar el turno.",
            "aviso": None,
        },
        "i": {
            "presupuesto": 2439,
            "contrato": {"cantidades": _tropas(0, 0, 0, 0, 0), "unidades": 0, "costo": 0, "saldo": 2439},
            "mantenimiento": {"base": 6926, "legatus": 1732, "esclavos": 100, "esclavos_pct": 30, "descuento": 2597, "total": 6061},
            "nota": None,
            "aviso": "Con 2.439 denarios no alcanza para los sueldos del turno 2 (6.061 con las tropas actuales). Más tropas suben los sueldos.",
        },
    },
}

RESULTADO = {
    "ganador": "xiii",
    "perdedor": "i",
    "turnos": 2,
    "motivo": "La Legio I Pompeiana no pudo pagar los sueldos del turno 2: necesitaba 5.861 denarios "
              "y solo tenía 2.439. Sus tropas desertan.",
    "leccion": "La Legio I Pompeiana perdió menos soldados (245 contra 261), pero el +25% de costo "
               "de su Legatus vació sus arcas.",
    "legiones": {
        "xiii": {
            # tipo, al inicio, bajas, convertidos, al final
            "filas": [("legionario", 500, 149, 45, 396), ("caballeria", 200, 73, 0, 127), ("ballesta", 120, 23, 0, 97),
                      ("ingeniero", 50, 5, 0, 45), ("esclavo", 150, 11, -45, 94)],
            "inicio": 1020, "bajas": 261, "final": 759,
            "hp": 12985, "hp_inicial": 22650,
            "economia": [("Presupuesto inicial", 20000), ("Contrato de tropas", -7950), ("Sueldos del turno 1", -5728),
                         ("Conversión de 45 esclavos", -225), ("Sueldos del turno 2", -5853)],
            "saldo": 244,
            "deuda": 0,
        },
        "i": {
            "filas": [("legionario", 480, 134, 0, 346), ("caballeria", 250, 80, 0, 170), ("ballesta", 100, 17, 0, 83),
                      ("ingeniero", 0, 0, 0, 0), ("esclavo", 100, 14, 0, 86)],
            "inicio": 930, "bajas": 245, "final": 685,
            "hp": 15155, "hp_inicial": 24100,
            "economia": [("Presupuesto inicial", 16000), ("Contrato de tropas", -7500), ("Sueldos del turno 1", -6061)],
            "saldo": 2439,
            "deuda": 5861,
        },
    },
}

# Bitácora de la campaña (EventoBatalla: instante, turno, etapa, descripción).
EVENTOS = [
    _evento("18:05:12", 0, None, "sistema", "Campaña «Guerra Civil — 49 a.C.» creada. El Senado designa como cónsules a Cayo Julio César y Cneo Pompeyo Magno."),
    _evento("18:07:40", 0, None, "legion", "Cayo Julio César crea la Legio XIII Gemina al mando del Legatus Marco Antonio (+10% ATK, +5% DEF, +15% costo). Presupuesto: 20.000 denarios."),
    _evento("18:09:03", 0, None, "contrato", "La Legio XIII Gemina contrata 500 legionarios, 200 de caballería, 120 ballestas, 50 ingenieros y 150 esclavos por 7.950 denarios."),
    _evento("18:11:26", 0, None, "legion", "Cayo Julio César crea la Legio X Equestris al mando del Legatus Décimo Bruto (+25% ATK, 0% DEF, +25% costo). Presupuesto: 15.000 denarios."),
    _evento("18:12:58", 0, None, "contrato", "La Legio X Equestris contrata 300 legionarios, 300 de caballería, 60 ballestas, 30 ingenieros y 100 esclavos por 6.700 denarios."),
    _evento("18:14:31", 0, None, "legion", "Cneo Pompeyo Magno crea la Legio I Pompeiana al mando del Legatus Tito Labieno (+20% ATK, +5% DEF, +25% costo). Presupuesto: 16.000 denarios."),
    _evento("18:16:07", 0, None, "contrato", "La Legio I Pompeiana contrata 480 legionarios, 250 de caballería, 100 ballestas y 100 esclavos por 7.500 denarios."),
    _evento("18:18:45", 0, None, "legion", "Cneo Pompeyo Magno crea la Legio IX Hispana al mando del Legatus Lucio Afranio (−20% ATK, +20% DEF, 0% costo). Presupuesto: 10.000 denarios."),
    _evento("18:19:52", 0, None, "contrato", "Contrato rechazado: la Legio IX Hispana intentó contratar tropas por 12.000 denarios y solo dispone de 10.000."),
    _evento("18:30:00", 1, 0, "sistema", "Comienza la Batalla de Farsalia: Legio XIII Gemina (atacante inicial) contra Legio I Pompeiana.", 0),
    _evento("18:30:00", 1, 0, "estrategia", "Turno 1: ambas legiones forman en Triplex Acies, obligatoria en el primer turno.", 0),
    _evento("18:30:00", 1, 0, "estrategia", "La Legio I Pompeiana activa la sinergia de Triplex Acies (51,6% de legionarios): +35% DEF global y +15% de daño de ballestas.", 0),
    _evento("18:30:00", 1, 0, "estrategia", "La Legio XIII Gemina no activa la sinergia de Triplex Acies: tiene 49,0% de legionarios y se requiere 50%.", 0),
    _evento("18:30:04", 1, 1, "combate", "Etapa 1: ataca la Legio XIII Gemina. ATK 35.100 − DEF 32.325 = 2.775 de daño.", 1),
    _evento("18:30:04", 1, 1, "combate", "Reparto del daño: legionarios 61,0% (1.692), caballería 24,4% (677), ballestas 14,6% (406).", 1),
    _evento("18:30:05", 1, 1, "bajas", "La Legio I Pompeiana pierde 38 legionarios, 22 de caballería y 6 ballestas.", 1),
    _evento("18:30:09", 1, 2, "combate", "Etapa 2: se invierten los roles y ataca la Legio I Pompeiana. ATK 35.295 − DEF 27.420 = 7.875 de daño.", 2),
    _evento("18:30:09", 1, 2, "combate", "Reparto del daño: legionarios 57,9% (4.556), caballería 29,8% (2.350), ballestas 12,3% (969).", 2),
    _evento("18:30:10", 1, 2, "bajas", "La Legio XIII Gemina pierde 61 legionarios, 27 de caballería, 9 ballestas, 2 ingenieros y 5 esclavos.", 2),
    _evento("18:30:14", 1, 3, "economia", "La Legio XIII Gemina paga 5.728 denarios de sueldos (7.116 base, +15% del Legatus, −30% por 145 esclavos). Le quedan 6.322.", 3),
    _evento("18:30:14", 1, 3, "economia", "La Legio I Pompeiana paga 6.061 denarios de sueldos (6.926 base, +25% del Legatus, −30% por 100 esclavos). Le quedan 2.439.", 3),
    _evento("18:31:02", 1, 3, "conversion", "La Legio XIII Gemina convierte 45 esclavos en legionarios por 225 denarios. Le quedan 6.097.", 3),
    _evento("18:31:40", 2, 0, "estrategia", "Turno 2: la Legio XIII Gemina adopta Cuneus (+45% ATK, −25% DEF).", 4),
    _evento("18:31:40", 2, 0, "estrategia", "Turno 2: la Legio I Pompeiana mantiene Triplex Acies; su sinergia sigue activa (51,2% de legionarios).", 4),
    _evento("18:31:44", 2, 1, "combate", "Etapa 1: la Legio XIII Gemina carga en cuña. ATK 41.827 − DEF 29.790 = 12.037; con la caballería a +50%, 13.393 de daño.", 4),
    _evento("18:31:44", 2, 1, "combate", "Reparto del daño: legionarios 63,0% (7.586), caballería 22,5% (4.067 con el +50%), ballestas 14,5% (1.740).", 4),
    _evento("18:31:45", 2, 1, "bajas", "La Legio I Pompeiana pierde 96 legionarios, 58 de caballería, 11 ballestas y 14 esclavos: en cuña, la caballería también alcanza a los esclavos.", 4),
    _evento("18:31:49", 2, 2, "combate", "Etapa 2: contraataca la Legio I Pompeiana. ATK 27.888 − DEF 18.102 = 9.786; la legión en cuña recibe +50%: 14.679 de daño.", 5),
    _evento("18:31:49", 2, 2, "combate", "Reparto del daño: legionarios 57,8% (8.479), caballería 28,4% (4.166), ballestas 13,9% (2.034).", 5),
    _evento("18:31:50", 2, 2, "bajas", "La Legio XIII Gemina pierde 88 legionarios, 46 de caballería, 14 ballestas, 3 ingenieros y 6 esclavos.", 5),
    _evento("18:31:54", 2, 3, "economia", "La Legio XIII Gemina paga 5.853 denarios de sueldos (5.988 base, +15% del Legatus, −15% por 94 esclavos). Le quedan 244.", 6),
    _evento("18:31:54", 2, 3, "fin", "La Legio I Pompeiana no puede pagar 5.861 denarios de sueldos: solo tiene 2.439. Sus tropas desertan.", 6),
    _evento("18:31:54", 2, 3, "fin", "¡Victoria de la Legio XIII Gemina! La Batalla de Farsalia termina en el turno 2.", 6),
]
