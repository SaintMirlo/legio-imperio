"""Datos que las vistas de combate necesitan ya calculados (consola, comparación y resultado).

Las plantillas solo muestran: aquí se piden al modelo los atributos, las barras de salud y
el resumen del último paso, sin repetir reglas del juego.
"""
from modelo.catalogos import UNIDAD, UNIDADES
from modelo.combate import ETAPA_1, ETAPA_2, LADOS, PREPARACION, MotorCombate
from modelo.estrategias import ESTRATEGIAS_TACTICAS

EVENTOS_CONSOLA = 150  # la consola muestra los últimos sucesos; la bitácora, todos


def _barra(clave, etiqueta, actual, referencia, antes, tipo=None):
    return {"clave": clave, "etiqueta": etiqueta, "actual": actual, "referencia": referencia,
            "antes": max(actual, antes), "tipo": tipo}


def vista_lado(enfrentamiento, legion, lado, animar):
    """Panel de una legión en la consola: formación, tabla dinámica y barras de salud."""
    turno = enfrentamiento.turno_actual
    participante = enfrentamiento.participantes[lado]
    estrategia = turno.estrategia(lado)
    atributos = legion.calcular_atributos(estrategia)
    _, etapa = enfrentamiento.ultima_etapa()
    golpeado = animar and etapa is not None and etapa.defensor == lado

    hp = legion.hp_actual()
    barras = [_barra(f"{lado}-hp", "HP total", hp, hp + participante.hp_perdido,
                     hp + (etapa.hp_perdido if golpeado else 0))]
    for tipo in UNIDADES:
        vivos = len(legion.unidades[tipo])
        caidos = etapa.bajas.get(tipo, 0) if golpeado else 0
        barras.append(_barra(f"{lado}-{tipo}", UNIDAD[tipo]["plural"], vivos,
                             vivos + participante.bajas[tipo], vivos + caidos, tipo=tipo))

    conteo = legion.contar()
    opciones = [{"estrategia": e, "motivo": e.validar_composicion(conteo)} for e in ESTRATEGIAS_TACTICAS.values()]
    return {
        "lado": lado,
        "legion": legion,
        "participante": participante,
        "estrategia": estrategia,
        "atributos": atributos,
        "filas": legion.filas(atributos),
        "mantenimiento": legion.calcular_mantenimiento(),
        "barras": barras,
        "opciones": opciones,
        "golpeado": golpeado,
    }


def contexto_consola(campana, enfrentamiento, visto=0):
    """Todo lo que muestra la consola de batalla (página completa o fragmento)."""
    turno = enfrentamiento.turno_actual
    # Las barras se animan cuando el último paso fue una etapa (el daño recién recibido).
    animar = turno.fase in (ETAPA_1, ETAPA_2)
    legiones = campana.legiones_en(enfrentamiento)
    lados = {lado: vista_lado(enfrentamiento, legiones[lado], lado, animar) for lado in LADOS}

    proxima = None
    if enfrentamiento.en_curso and turno.fase in (PREPARACION, ETAPA_1):
        atacante = "a" if turno.fase == PREPARACION else "b"
        defensor = "b" if atacante == "a" else "a"
        dano = MotorCombate.dano_total(lados[atacante]["atributos"], lados[defensor]["atributos"])[1]
        proxima = {"numero": 1 if atacante == "a" else 2, "atacante": atacante, "defensor": defensor, "dano": dano}

    turno_etapa, etapa = enfrentamiento.ultima_etapa()
    eventos = campana.bitacora.obtener_historial(enfrentamiento=enfrentamiento.id)
    return {
        "campana": campana,
        "enfrentamiento": enfrentamiento,
        "turno": turno,
        "lados": lados,
        "proxima": proxima,
        "ultima_etapa": etapa if animar else None,
        "turno_etapa": turno_etapa,
        "turno_anterior": enfrentamiento.turnos[-2] if len(enfrentamiento.turnos) > 1 else None,
        "eventos": eventos[-EVENTOS_CONSOLA:],
        "eventos_ocultos": max(0, len(eventos) - EVENTOS_CONSOLA),
        "visto": visto,
        "ultimo_evento": eventos[-1].numero if eventos else 0,
    }


def filas_turnos(enfrentamiento):
    """Resumen por turno para la página de resultado."""
    filas = []
    for turno in enfrentamiento.turnos:
        etapas = {etapa.numero: etapa for etapa in turno.etapas}
        filas.append({"turno": turno, "etapas": etapas})
    return filas
