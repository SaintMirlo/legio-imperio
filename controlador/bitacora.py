"""Visor de la bitácora de campaña (CU010, CU012)."""
from flask import Blueprint, render_template

from modelo import datos_prototipo as datos

bp = Blueprint("bitacora", __name__)


@bp.get("/bitacora")
def ver():
    return render_template("bitacora.html", eventos=datos.EVENTOS)
