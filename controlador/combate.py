"""Batalla: preparar, consola por turnos, refuerzos, reagrupación y resultado (CU003, CU005 a CU011)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from controlador.prototipo import obtener_prototipo

bp = Blueprint("combate", __name__, url_prefix="/combate")


@bp.route("/preparar", methods=["GET", "POST"])
def preparar():
    prototipo = obtener_prototipo()
    contexto = prototipo.contexto_batalla()
    if request.method == "POST":
        elegidas = [request.form.get("legion_a"), request.form.get("legion_b")]
        if any(id_legion not in contexto["legiones"] for id_legion in elegidas):
            flash("Elige dos legiones del panel de campaña.", "error")
            return redirect(url_for("combate.preparar"))
        if elegidas[0] == elegidas[1]:
            flash("Una legión no puede enfrentarse a sí misma. Elige dos legiones distintas.", "error")
            return redirect(url_for("combate.preparar"))
        if any(contexto["legiones"][id_legion]["estado"] != "lista" for id_legion in elegidas):
            flash("Ambas legiones deben tener tropas para entrar en combate.", "error")
            return redirect(url_for("combate.preparar"))
        flash(f"¡Alea iacta est! Se abre el recorrido de ejemplo de la {contexto['batalla']['nombre']}.", "info")
        return redirect(url_for("combate.consola", paso=0))
    return render_template(
        "combate_preparar.html",
        **contexto,
        inicio=prototipo.paso(0)["estado"],
        validaciones=prototipo.validaciones(),
    )


def _siguiente(paso, actual):
    """Qué hace «Paso a paso» en cada punto del recorrido fijo de la batalla."""
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
    prototipo = obtener_prototipo()
    try:
        actual = prototipo.paso(paso)
    except IndexError:
        abort(404)
    return render_template(
        "combate_consola.html",
        paso=paso,
        actual=actual,
        anterior=prototipo.paso(paso - 1) if paso else actual,
        **prototipo.contexto_batalla(),
        eventos=prototipo.eventos(hasta=paso),
        siguiente=_siguiente(paso, actual),
        auto=request.args.get("auto") == "1" and not actual["formaciones_editables"],
    )


@bp.post("/formaciones")
def formaciones():
    flash("Selección recibida. El ejemplo continúa con la Legio XIII Gemina en Cuneus y la Legio I Pompeiana en Triplex Acies.", "info")
    return redirect(url_for("combate.consola", paso=4, auto=request.form.get("auto")))


@bp.route("/contratar/<id_legion>", methods=["GET", "POST"])
def contratar(id_legion):
    """CU003 extiende CU006: contratar tropas al elegir la formación del turno 2."""
    prototipo = obtener_prototipo()
    try:
        refuerzo = prototipo.refuerzo(id_legion)
    except KeyError:
        abort(404)
    legion = prototipo.legion(id_legion)
    if request.method == "POST":
        flash(f"Contrato registrado para la {legion['nombre']}. En el prototipo la batalla sigue con las cifras de ejemplo.", "info")
        return redirect(url_for("combate.consola", paso=3))
    return render_template(
        "legion_contratar.html",
        legion=legion,
        refuerzo=refuerzo,
        turno=prototipo.paso(3)["turno"],
        **prototipo.contexto_batalla(),
    )


@bp.post("/cerrar-turno")
def cerrar_turno():
    if request.form.get("turno") == "1":
        flash("Turno 1 cerrado: ambas legiones pagaron los sueldos de sus tropas.", "info")
        return redirect(url_for("combate.reagrupacion"))
    if request.form.get("turno") != "2":
        abort(400)
    flash("La Legio I Pompeiana no puede pagar los sueldos del turno 2. ¡Fin de la batalla!", "aviso")
    return redirect(url_for("combate.resultado"))


@bp.route("/reagrupacion", methods=["GET", "POST"])
def reagrupacion():
    if request.method == "POST":
        flash("Reagrupación confirmada: la Legio XIII Gemina convirtió 45 esclavos en legionarios por 225 denarios.", "exito")
        return redirect(url_for("combate.consola", paso=3))
    return render_template(
        "combate_reagrupacion.html",
        reagrupacion=obtener_prototipo().reagrupacion(),
        **obtener_prototipo().contexto_batalla(),
    )


@bp.get("/resultado")
def resultado():
    prototipo = obtener_prototipo()
    return render_template(
        "combate_resultado.html",
        resultado=prototipo.resultado(),
        **prototipo.contexto_batalla(),
        eventos=prototipo.eventos(solo=prototipo.cantidad_pasos),
    )
