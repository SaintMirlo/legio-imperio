"""Legiones: crear, contratar tropas y revisar fuerzas (CU001 a CU004)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from modelo import datos_prototipo as datos
from vista.formato import miles

bp = Blueprint("legiones", __name__, url_prefix="/legiones")


def _legion(id_legion):
    legion = datos.LEGIONES.get(id_legion)
    if legion is None:
        abort(404)
    return legion


@bp.route("/nueva", methods=["GET", "POST"])
def nueva():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip() or "La nueva legión"
        legatus = request.form.get("legatus", "").strip() or "sin nombre"
        flash(f"Legión «{nombre}» creada al mando del Legatus {legatus}. Ahora contrata sus tropas.", "exito")
        # El recorrido sigue con la legión de ejemplo del formulario.
        return redirect(url_for("legiones.contratar", id_legion="x"))
    return render_template("legion_nueva.html", campana=datos.CAMPANA, ejemplo=datos.LEGIONES["x"])


@bp.get("/<id_legion>")
def detalle(id_legion):
    return render_template("legion_detalle.html", legion=_legion(id_legion))


@bp.route("/<id_legion>/contratar", methods=["GET", "POST"])
def contratar(id_legion):
    legion = _legion(id_legion)
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
            f"Contrato firmado: la {legion['nombre']} recluta {miles(contrato['unidades'])} unidades "
            f"por {miles(contrato['costo'])} denarios.",
            "exito",
        )
        return redirect(url_for("legiones.detalle", id_legion=id_legion))
    return render_template("legion_contratar.html", legion=legion)
