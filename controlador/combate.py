"""Batalla: preparar, consola por turnos, refuerzos, reagrupación y resultado (CU003, CU005 a CU011)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from modelo import datos_prototipo as datos

bp = Blueprint("combate", __name__, url_prefix="/combate")


@bp.route("/preparar", methods=["GET", "POST"])
def preparar():
    if request.method == "POST":
        if request.form.get("legion_a") == request.form.get("legion_b"):
            flash("Una legión no puede enfrentarse a sí misma. Elige dos legiones distintas.", "error")
            return redirect(url_for("combate.preparar"))
        flash(f"¡Alea iacta est! Comienza la {datos.BATALLA['nombre']}.", "exito")
        return redirect(url_for("combate.consola", paso=0))
    return render_template(
        "combate_preparar.html",
        legiones=datos.LEGIONES,
        batalla=datos.BATALLA,
        inicio=datos.PASOS[0]["estado"],
        validaciones=datos.VALIDACIONES_ENFRENTAMIENTO,
    )


def _siguiente(paso):
    """Qué hace «Paso a paso» en cada punto del recorrido fijo de la batalla."""
    actual = datos.PASOS[paso]
    if actual["formaciones_editables"]:
        return {"metodo": "post", "url": url_for("combate.formaciones"), "texto": "Confirmar formaciones", "campos": {}}
    if actual["etapa"] == 2:
        return {
            "metodo": "post",
            "url": url_for("combate.cerrar_turno"),
            "texto": f"Cerrar turno {actual['turno']}",
            "campos": {"turno": actual["turno"]},
        }
    return {
        "metodo": "get",
        "url": url_for("combate.consola", paso=paso + 1),
        "texto": f"Resolver etapa {actual['etapa'] + 1}",
        "campos": {},
    }


@bp.get("/paso/<int:paso>")
def consola(paso):
    if not 0 <= paso < len(datos.PASOS):
        abort(404)
    actual = datos.PASOS[paso]
    return render_template(
        "combate_consola.html",
        paso=paso,
        actual=actual,
        anterior=datos.PASOS[paso - 1] if paso else actual,
        batalla=datos.BATALLA,
        legiones=datos.LEGIONES,
        eventos=[e for e in datos.EVENTOS if e["paso"] is not None and e["paso"] <= paso],
        siguiente=_siguiente(paso),
        auto=request.args.get("auto") == "1",
    )


@bp.post("/formaciones")
def formaciones():
    flash("Formaciones confirmadas: la Legio XIII Gemina carga en Cuneus y la Legio I Pompeiana mantiene Triplex Acies.", "exito")
    return redirect(url_for("combate.consola", paso=4, auto=request.form.get("auto")))


@bp.route("/contratar/<id_legion>", methods=["GET", "POST"])
def contratar(id_legion):
    """CU003 extiende CU006: contratar tropas al elegir la formación del turno 2."""
    refuerzo = datos.REFUERZOS["legiones"].get(id_legion)
    if refuerzo is None:
        abort(404)
    legion = datos.LEGIONES[id_legion]
    if request.method == "POST":
        flash(f"Contrato registrado para la {legion['nombre']}. En el prototipo la batalla sigue con las cifras de ejemplo.", "info")
        return redirect(url_for("combate.consola", paso=3))
    return render_template(
        "legion_contratar.html",
        legion=legion,
        refuerzo=refuerzo,
        turno=datos.REFUERZOS["turno"],
        batalla=datos.BATALLA,
    )


@bp.post("/cerrar-turno")
def cerrar_turno():
    if request.form.get("turno") == "1":
        flash("Turno 1 cerrado: ambas legiones pagaron los sueldos de sus tropas.", "info")
        return redirect(url_for("combate.reagrupacion"))
    flash("La Legio I Pompeiana no puede pagar los sueldos del turno 2. ¡Fin de la batalla!", "aviso")
    return redirect(url_for("combate.resultado"))


@bp.route("/reagrupacion", methods=["GET", "POST"])
def reagrupacion():
    if request.method == "POST":
        flash("Reagrupación confirmada: la Legio XIII Gemina convirtió 45 esclavos en legionarios por 225 denarios.", "exito")
        return redirect(url_for("combate.consola", paso=3))
    return render_template(
        "combate_reagrupacion.html",
        reagrupacion=datos.REAGRUPACION,
        batalla=datos.BATALLA,
        legiones=datos.LEGIONES,
    )


@bp.get("/resultado")
def resultado():
    return render_template(
        "combate_resultado.html",
        resultado=datos.RESULTADO,
        batalla=datos.BATALLA,
        legiones=datos.LEGIONES,
        eventos=[e for e in datos.EVENTOS if e["paso"] == len(datos.PASOS)],
    )
