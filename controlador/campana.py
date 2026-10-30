"""Inicio, campaña y persistencia (CU001, CU004, CU013, CU014)."""
import json

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from controlador.prototipo import obtener_prototipo
from modelo.prototipo import ArchivoCampanaInvalido, validar_archivo_campana

bp = Blueprint("campana", __name__)


@bp.get("/")
def inicio():
    return render_template("inicio.html", recientes=obtener_prototipo().recientes())


@bp.route("/campana/nueva", methods=["GET", "POST"])
def nueva():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip() or "Nueva campaña"
        flash(f"Creación simulada de «{nombre}». El recorrido continúa con la campaña de ejemplo del Hito 2.", "info")
        return redirect(url_for("campana.panel"))
    return render_template("campana_nueva.html", campana=obtener_prototipo().campana())


@bp.get("/campana")
def panel():
    return render_template("campana_panel.html", **obtener_prototipo().contexto_campana())


@bp.get("/campana/exportar")
def exportar():
    """Descarga el ejemplo; la persistencia de una partida corresponde al Hito 3."""
    prototipo = obtener_prototipo()
    contenido = prototipo.archivo_de_ejemplo()
    return Response(
        json.dumps(contenido, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{prototipo.campana()["archivo"]}"'},
    )


@bp.post("/campana/cargar")
def cargar():
    archivo = request.files.get("archivo")
    if archivo is None or not (archivo.filename or "").lower().endswith(".json"):
        flash("Ese archivo no es una campaña de Legio Imperium. Elige un archivo .json.", "error")
        return redirect(url_for("campana.inicio"))
    try:
        nombre = validar_archivo_campana(json.load(archivo))
    except (ValueError, UnicodeError, RecursionError) as error:
        mensaje = str(error) if isinstance(error, ArchivoCampanaInvalido) else "El archivo no contiene un JSON válido."
        flash(mensaje, "error")
        return redirect(url_for("campana.inicio"))
    flash(f"Archivo de «{nombre}» validado. En el Hito 2 se muestra la campaña de ejemplo; todavía no se restaura una partida.", "info")
    return redirect(url_for("campana.panel"))
