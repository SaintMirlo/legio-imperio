"""Legiones: crear, contratar tropas y revisar fuerzas (CU001 a CU004)."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from controlador.prototipo import obtener_legion, obtener_prototipo
from vista.formato import miles

bp = Blueprint("legiones", __name__, url_prefix="/legiones")


@bp.route("/nueva", methods=["GET", "POST"])
def nueva():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip() or "La nueva legión"
        legatus = request.form.get("legatus", "").strip() or "sin nombre"
        flash(f"Creación simulada de «{nombre}», Legatus {legatus}. El catálogo muestra la Legio X de ejemplo.", "info")
        # El recorrido sigue con la legión de ejemplo del formulario.
        return redirect(url_for("legiones.contratar", id_legion="x"))
    prototipo = obtener_prototipo()
    return render_template("legion_nueva.html", campana=prototipo.campana(), ejemplo=prototipo.legion("x"))


@bp.get("/<id_legion>")
def detalle(id_legion):
    return render_template("legion_detalle.html", legion=obtener_legion(id_legion))


@bp.route("/<id_legion>/contratar", methods=["GET", "POST"])
def contratar(id_legion):
    legion = obtener_legion(id_legion)
    contrato = legion["contrato"]
    if request.method == "POST":
        # La propuesta de la Legio IX Hispana excede su presupuesto: muestra el error.
        if contrato["saldo"] < 0:
            flash(
                f"Presupuesto insuficiente: el contrato cuesta {miles(contrato['costo'])} denarios "
                f"y la {legion['nombre']} solo tiene {miles(legion['presupuesto_inicial'])}.",
                "error",
            )
            return redirect(url_for("legiones.contratar", id_legion=id_legion))
        flash(
            f"Contrato simulado: la {legion['nombre']} recluta {miles(contrato['unidades'])} unidades de ejemplo "
            f"por {miles(contrato['costo'])} denarios.",
            "exito",
        )
        return redirect(url_for("legiones.detalle", id_legion=id_legion))
    return render_template("legion_contratar.html", legion=legion)
