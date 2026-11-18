"""Batalla: preparar, consola por turnos, refuerzos, abandono y resultado (CU005 a CU011).

La consola responde con fragmentos HTML cuando la pide el JavaScript (paso a paso o en modo
automático) y con páginas completas si se usa sin JavaScript.
"""
from flask import Blueprint, abort, flash, make_response, redirect, render_template, request, url_for

from controlador.presentacion import contexto_consola, filas_turnos
from controlador.sesion import campana_actual, es_fetch, leer_entero, leer_tropas, modificar_campana
from modelo.catalogos import UNIDADES
from modelo.combate import LADOS, ConsolaDesactualizada
from modelo.errores import ReglaInvalida
from modelo.textos import miles, tropas_en_texto
from modelo.unidades import EsclavoAuxiliar

bp = Blueprint("combate", __name__, url_prefix="/combate")


def _id_form(campo, que):
    return leer_entero(request.form, campo, que, defecto=None)


def _seleccion_inicial(campana):
    """Las dos primeras legiones listas para combatir (o las dos primeras que haya)."""
    listas = [legion.id for legion in campana.legiones.values() if legion.esta_lista()]
    todas = list(campana.legiones)
    ids = (listas + [i for i in todas if i not in listas] + [None, None])[:2]
    return ids[0], ids[1]


@bp.route("/preparar", methods=["GET", "POST"])
def preparar():
    campana = campana_actual()
    if campana.enfrentamiento_activo():
        flash("Hay un enfrentamiento en curso: continúalo o abandónalo antes de preparar otro.", "aviso")
        return redirect(url_for("combate.consola"))
    id_a, id_b = _seleccion_inicial(campana)
    nombre = f"Batalla {campana.siguiente_enfrentamiento}"
    if request.method == "POST":
        id_a = request.form.get("atacante", type=int)
        id_b = request.form.get("defensora", type=int)
        nombre = request.form.get("nombre", "")
        try:
            with modificar_campana() as campana:
                enfrentamiento = campana.iniciar_enfrentamiento(nombre, id_a, id_b)
        except ReglaInvalida as error:
            flash(str(error), "error")
            return render_template("combate_preparar.html", campana=campana, id_a=id_a, id_b=id_b, nombre=nombre,
                                   comparacion=campana.comparar(id_a, id_b)), 400
        flash(f"¡Comienza «{enfrentamiento.nombre}»! En el turno 1 ambas legiones forman en Triplex Acies.", "exito")
        return redirect(url_for("combate.consola"))
    return render_template("combate_preparar.html", campana=campana, id_a=id_a, id_b=id_b, nombre=nombre,
                           comparacion=campana.comparar(id_a, id_b))


@bp.get("/comparar")
def comparar():
    """Fragmento con la comparación de las legiones elegidas (se actualiza al cambiarlas)."""
    campana = campana_actual()
    id_a = request.args.get("atacante", type=int)
    id_b = request.args.get("defensora", type=int)
    return render_template("parciales/comparacion.html", campana=campana, comparacion=campana.comparar(id_a, id_b))


@bp.get("/")
def consola():
    campana = campana_actual()
    enfrentamiento = campana.enfrentamiento_activo()
    if enfrentamiento is None:
        ultimo = campana.ultimo_enfrentamiento()
        if ultimo is not None:
            return redirect(url_for("combate.resultado", id_enfrentamiento=ultimo.id))
        flash("No hay un enfrentamiento en curso: elige dos legiones para preparar uno.", "info")
        return redirect(url_for("combate.preparar"))
    return render_template("combate_consola.html", **contexto_consola(campana, enfrentamiento,
                                                                      visto=_ultimo_evento(campana, enfrentamiento)))


def _ultimo_evento(campana, enfrentamiento):
    eventos = campana.bitacora.obtener_historial(enfrentamiento=enfrentamiento.id)
    return eventos[-1].numero if eventos else 0


def _decisiones(form):
    """Formación y esclavos a convertir de cada legión, tal como vienen de la consola."""
    decisiones = {}
    for lado in LADOS:
        decision = {}
        if form.get(f"formacion_{lado}"):
            decision["formacion"] = form.get(f"formacion_{lado}")
        convertir = {destino: leer_entero(form, f"convertir_{lado}_{destino}",
                                          f"la cantidad de esclavos a convertir en {destino}")
                     for destino in EsclavoAuxiliar.DESTINOS}
        if any(convertir.values()):
            decision["convertir"] = convertir
        decisiones[lado] = decision
    return decisiones


def _responder(campana, enfrentamiento, mensaje=None, nivel="info"):
    """Fragmento de la consola (fetch) o redirección con aviso (sin JavaScript)."""
    if es_fetch():
        visto = request.form.get("visto", type=int) or 0
        contexto = contexto_consola(campana, enfrentamiento, visto=visto)
        respuesta = make_response(render_template("parciales/batalla.html", mensaje=mensaje, nivel=nivel, **contexto))
        respuesta.headers["X-Legio-Estado"] = "error" if nivel == "error" else "ok"
        return respuesta
    if mensaje:
        flash(mensaje, nivel)
    if enfrentamiento.en_curso:
        return redirect(url_for("combate.consola"))
    return redirect(url_for("combate.resultado", id_enfrentamiento=enfrentamiento.id))


def _activo_o_volver(campana):
    enfrentamiento = campana.enfrentamiento_activo()
    if enfrentamiento is None:
        ultimo = campana.ultimo_enfrentamiento()
        if es_fetch() and ultimo is not None:
            return None, _responder(campana, ultimo, "El enfrentamiento ya había terminado.", "aviso")
        flash("No hay un enfrentamiento en curso.", "aviso")
        return None, redirect(url_for("combate.preparar"))
    return enfrentamiento, None


@bp.post("/avanzar")
def avanzar():
    """CU006 a CU009: aplica las decisiones del turno y ejecuta el siguiente paso."""
    campana = campana_actual()
    enfrentamiento, salida = _activo_o_volver(campana)
    if salida:
        return salida
    try:
        paso = _id_form("paso", "el paso de la consola")
        decisiones = _decisiones(request.form)
        with modificar_campana() as campana:
            enfrentamiento = campana.avanzar_combate(decisiones, paso)
    except ConsolaDesactualizada as error:
        return _responder(campana, campana.enfrentamiento_activo() or enfrentamiento, str(error), "aviso")
    except ReglaInvalida as error:
        return _responder(campana, enfrentamiento, str(error), "error")
    mensaje = None
    if not enfrentamiento.en_curso:
        mensaje = enfrentamiento.motivo
    return _responder(campana, enfrentamiento, mensaje, "exito" if mensaje else "info")


@bp.post("/refuerzos")
def refuerzos():
    """CU003 durante el combate: contratar tropas en la preparación de un turno."""
    campana = campana_actual()
    enfrentamiento, salida = _activo_o_volver(campana)
    if salida:
        return salida
    lado = request.form.get("lado")
    try:
        cantidades = leer_tropas(request.form, UNIDADES, prefijo=f"refuerzo_{lado}_")
        with modificar_campana() as campana:
            cantidades, costo = campana.contratar_refuerzos(lado, cantidades)
            enfrentamiento = campana.enfrentamiento_activo()
    except ReglaInvalida as error:
        return _responder(campana, enfrentamiento, str(error), "error")
    nombre = enfrentamiento.participantes[lado].nombre
    return _responder(campana, enfrentamiento,
                      f"{nombre} contrata {tropas_en_texto(cantidades)} por {miles(costo)} denarios.", "exito")


@bp.post("/abandonar")
def abandonar():
    campana = campana_actual()
    if campana.enfrentamiento_activo() is None:
        return redirect(url_for("combate.consola"))
    with modificar_campana() as campana:
        enfrentamiento = campana.abandonar_combate()
    flash(f"Se abandonó «{enfrentamiento.nombre}». Las legiones conservan sus tropas y presupuestos actuales.",
          "info")
    return redirect(url_for("combate.resultado", id_enfrentamiento=enfrentamiento.id))


@bp.get("/<int:id_enfrentamiento>")
def resultado(id_enfrentamiento):
    campana = campana_actual()
    try:
        enfrentamiento = campana.enfrentamiento(id_enfrentamiento)
    except KeyError:
        abort(404)
    if enfrentamiento.en_curso:
        return redirect(url_for("combate.consola"))
    return render_template(
        "combate_resultado.html", campana=campana, enfrentamiento=enfrentamiento,
        turnos=filas_turnos(enfrentamiento),
        eventos=campana.bitacora.obtener_historial(enfrentamiento=enfrentamiento.id),
    )
