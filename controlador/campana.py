"""Inicio, campaña y persistencia (CU001, CU004, CU013, CU014)."""
import json

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from modelo import datos_prototipo as datos

bp = Blueprint("campana", __name__)


@bp.get("/")
def inicio():
    return render_template("inicio.html", recientes=datos.CAMPANAS_RECIENTES)


@bp.route("/campana/nueva", methods=["GET", "POST"])
def nueva():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip() or datos.CAMPANA["nombre"]
        flash(f"Campaña «{nombre}» creada. El Senado ya tiene a sus dos cónsules.", "exito")
        return redirect(url_for("campana.panel"))
    return render_template("campana_nueva.html", campana=datos.CAMPANA)


@bp.get("/campana")
def panel():
    return render_template("campana_panel.html", campana=datos.CAMPANA, legiones=datos.LEGIONES)


@bp.get("/campana/exportar")
def exportar():
    """Archivo de la campaña que se guarda. En el Hito 3 lo arma GestorPersistencia."""
    contenido = {
        "formato": "legio-imperium",
        "version": 1,
        "guardada": "29-10-2026 18:33:10",
        "campana": datos.CAMPANA["nombre"],
        "consules": datos.CAMPANA["consules"],
        "legiones": [
            {clave: legion[clave] for clave in ("id", "nombre", "consul", "legatus", "presupuesto", "tropas")}
            for legion in datos.LEGIONES.values()
        ],
        "batalla": {"nombre": datos.BATALLA["nombre"], "turno": 2, "etapa": 2},
        "bitacora": [
            {clave: evento[clave] for clave in ("instante", "turno", "etapa", "tipo", "texto")}
            for evento in datos.EVENTOS
        ],
    }
    return Response(
        json.dumps(contenido, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{datos.CAMPANA["archivo"]}"'},
    )


@bp.post("/campana/cargar")
def cargar():
    archivo = request.files.get("archivo")
    if archivo is None or not archivo.filename.lower().endswith(".json"):
        flash("Ese archivo no es una campaña de Legio Imperium. Elige un archivo .json.", "error")
        return redirect(request.referrer or url_for("campana.inicio"))
    flash(f"Campaña cargada desde «{archivo.filename}»: {datos.CAMPANA['nombre']}, 4 legiones.", "exito")
    return redirect(url_for("campana.panel"))
