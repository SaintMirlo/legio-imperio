"""Visor de la bitácora de campaña (CU010, CU012)."""
from flask import Blueprint, render_template

from controlador.prototipo import obtener_prototipo

bp = Blueprint("bitacora", __name__)


@bp.get("/bitacora")
def ver():
    return render_template("bitacora.html", eventos=obtener_prototipo().eventos())
