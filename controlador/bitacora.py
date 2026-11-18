"""Visor de la bitácora de campaña (CU010, CU012 y RU008)."""
from flask import Blueprint, render_template, request

from controlador.sesion import campana_actual
from modelo.catalogos import TIPOS_EVENTO

bp = Blueprint("bitacora", __name__)

EVENTOS_POR_PAGINA = 1000


@bp.get("/bitacora")
def ver():
    campana = campana_actual()
    ids = {e.id for e in campana.enfrentamientos}
    enfrentamiento = request.args.get("enfrentamiento", type=int)
    if enfrentamiento not in ids:
        enfrentamiento = None
    turno = request.args.get("turno", type=int)
    tipo = request.args.get("tipo") if request.args.get("tipo") in TIPOS_EVENTO else None
    texto = (request.args.get("q") or "").strip()[:60]

    eventos = campana.bitacora.obtener_historial(enfrentamiento=enfrentamiento, turno=turno, tipo=tipo, texto=texto)
    if enfrentamiento is not None:
        turnos = range(1, campana.enfrentamiento(enfrentamiento).turno_numero + 1)
    else:
        turnos = sorted({e.turno for e in campana.bitacora.eventos if e.turno})
    return render_template(
        "bitacora.html", campana=campana, eventos=eventos[-EVENTOS_POR_PAGINA:],
        total=len(eventos), ocultos=max(0, len(eventos) - EVENTOS_POR_PAGINA), turnos=turnos,
        filtros={"enfrentamiento": enfrentamiento, "turno": turno, "tipo": tipo, "q": texto},
        filtrado=any(v is not None and v != "" for v in (enfrentamiento, turno, tipo, texto)),
    )
