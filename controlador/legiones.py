"""Legiones: crear, configurar, contratar tropas y revisar fuerzas (CU001 a CU004)."""
from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for

from controlador.sesion import campana_actual, leer_entero, leer_tropas, modificar_campana
from modelo.catalogos import UNIDADES
from modelo.errores import ReglaInvalida
from modelo.estrategias import ESTRATEGIAS_TACTICAS
from modelo.textos import decimal, miles, tropas_en_texto

bp = Blueprint("legiones", __name__, url_prefix="/legiones")


def _legion(campana, id_legion):
    try:
        return campana.legion(id_legion)
    except KeyError:
        abort(404)


def _datos_legion(form):
    return {
        "nombre": form.get("nombre"),
        "consul": leer_entero(form, "consul", "el cónsul que nombra al Legatus", defecto=None),
        "legatus_nombre": form.get("legatus"),
        "bono_atk": leer_entero(form, "bono_atk", "la bonificación de ATK"),
        "bono_def": leer_entero(form, "bono_def", "la bonificación de DEF"),
        "presupuesto": leer_entero(form, "presupuesto", "el presupuesto", defecto=None),
    }


def _valores(legion):
    return {"nombre": legion.nombre, "consul": legion.consul, "legatus": legion.legatus.nombre,
            "bono_atk": legion.legatus.bono_atk, "bono_def": legion.legatus.bono_def,
            "presupuesto": legion.presupuesto}


@bp.route("/nueva", methods=["GET", "POST"])
def nueva():
    campana = campana_actual()
    if request.method == "POST":
        try:
            datos = _datos_legion(request.form)
            with modificar_campana() as campana:
                legion = campana.crear_legion(**datos)
        except ReglaInvalida as error:
            flash(str(error), "error")
            return render_template("legion_form.html", campana=campana, legion=None, valores=request.form), 400
        flash(f"{legion.nombre} creada con {miles(legion.presupuesto)} denarios. Ahora contrata sus tropas.", "exito")
        return redirect(url_for("legiones.contratar", id_legion=legion.id))
    sugerencia = {"consul": 1 if len(campana.legiones_de_consul(1)) <= len(campana.legiones_de_consul(2)) else 2,
                  "bono_atk": 0, "bono_def": 0, "presupuesto": 50_000}
    return render_template("legion_form.html", campana=campana, legion=None, valores=sugerencia)


@bp.get("/<int:id_legion>")
def detalle(id_legion):
    campana = campana_actual()
    legion = _legion(campana, id_legion)
    formaciones = []
    conteo = legion.contar()
    for estrategia in ESTRATEGIAS_TACTICAS.values():
        formaciones.append({"estrategia": estrategia, "motivo": estrategia.validar_composicion(conteo),
                            "atributos": legion.calcular_atributos(estrategia)})
    return render_template("legion_detalle.html", campana=campana, legion=legion,
                           atributos=legion.calcular_atributos(), formaciones=formaciones,
                           mantenimiento=legion.calcular_mantenimiento(), en_combate=campana.en_combate(legion))


@bp.route("/<int:id_legion>/configurar", methods=["GET", "POST"])
def configurar(id_legion):
    campana = campana_actual()
    legion = _legion(campana, id_legion)
    if request.method == "POST":
        try:
            datos = _datos_legion(request.form)
            with modificar_campana() as campana:
                cambio = campana.configurar_legion(id_legion, **datos)
                legion = campana.legion(id_legion)
        except ReglaInvalida as error:
            flash(str(error), "error")
            return render_template("legion_form.html", campana=campana, legion=legion, valores=request.form), 400
        flash(f"{legion.nombre} actualizada." if cambio else "No hubo cambios que guardar.",
              "exito" if cambio else "info")
        return redirect(url_for("legiones.detalle", id_legion=id_legion))
    if campana.en_combate(legion):
        flash(f"{legion.nombre} está en combate: podrás configurarla cuando termine el enfrentamiento.", "aviso")
        return redirect(url_for("legiones.detalle", id_legion=id_legion))
    return render_template("legion_form.html", campana=campana, legion=legion, valores=_valores(legion))


@bp.post("/<int:id_legion>/eliminar")
def eliminar(id_legion):
    _legion(campana_actual(), id_legion)
    try:
        with modificar_campana() as campana:
            legion = campana.eliminar_legion(id_legion)
    except ReglaInvalida as error:
        flash(str(error), "error")
        return redirect(url_for("legiones.detalle", id_legion=id_legion))
    flash(f"{legion.nombre} fue disuelta.", "exito")
    return redirect(url_for("campana.panel"))


@bp.route("/<int:id_legion>/contratar", methods=["GET", "POST"])
def contratar(id_legion):
    campana = campana_actual()
    legion = _legion(campana, id_legion)
    if campana.en_combate(legion):
        flash(f"{legion.nombre} está en combate: contrata refuerzos desde la consola, en la preparación "
              "de un turno.", "aviso")
        return redirect(url_for("combate.consola"))
    if request.method == "POST":
        try:
            cantidades = leer_tropas(request.form, UNIDADES)
            with modificar_campana() as campana:
                cantidades, costo = campana.contratar_tropas(id_legion, cantidades)
                legion = campana.legion(id_legion)
        except ReglaInvalida as error:
            flash(str(error), "error")
            return render_template("legion_contratar.html", campana=campana, legion=legion,
                                   valores=request.form), 400
        flash(f"{legion.nombre} contrata {tropas_en_texto(cantidades)} por {miles(costo)} denarios. "
              f"Le quedan {miles(legion.presupuesto)}.", "exito")
        return redirect(url_for("legiones.detalle", id_legion=id_legion))
    return render_template("legion_contratar.html", campana=campana, legion=legion, valores={})


@bp.get("/<int:id_legion>/simular")
def simular(id_legion):
    """Vista previa del contrato mientras el usuario escribe las cantidades (JSON)."""
    legion = _legion(campana_actual(), id_legion)
    try:
        cantidades = leer_tropas(request.args, UNIDADES)
    except ReglaInvalida as error:
        return jsonify({"valido": False, "mensaje": str(error)})
    vista = legion.simular_contrato(cantidades)
    if "costo" in vista:
        vista["texto"] = {
            "costo": miles(vista["costo"]), "restante": miles(vista["restante"]),
            "integrantes": miles(vista["integrantes"]), "nuevas": miles(vista["nuevas"]),
            "atk": decimal(vista["atk"]), "def": decimal(vista["def"]),
            "mantenimiento": miles(vista["mantenimiento"]),
            "subtotales": {tipo: miles(valor) for tipo, valor in vista["subtotales"].items()},
        }
    return jsonify(vista)
