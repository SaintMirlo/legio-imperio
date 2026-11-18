"""Inicio, campaña y persistencia en archivos (CU001, CU004, CU013, CU014)."""
from flask import Blueprint, Response, flash, redirect, render_template, request, url_for

from controlador.sesion import abrir_campana, campana_actual, persistencia
from modelo.archivo import exportar_campana, importar_campana, nombre_archivo
from modelo.campana import Campana
from modelo.errores import ArchivoCampanaInvalido, ReglaInvalida
from modelo.textos import contar

bp = Blueprint("campana", __name__)


def _volver():
    """Página desde la que se pidió la acción (solo rutas internas)."""
    destino = request.form.get("volver") or ""
    if destino.startswith("/") and not destino.startswith("//"):
        return destino
    return url_for("campana.inicio")


@bp.get("/")
def inicio():
    return render_template("inicio.html", campana=campana_actual(requerida=False))


@bp.route("/campana/nueva", methods=["GET", "POST"])
def nueva():
    if request.method == "POST":
        try:
            campana = Campana.iniciar(request.form.get("nombre"), request.form.get("consul_1"),
                                      request.form.get("consul_2"))
        except ReglaInvalida as error:
            flash(str(error), "error")
            return render_template("campana_nueva.html", valores=request.form), 400
        persistencia().guardar_campana(campana)
        abrir_campana(campana.id)
        flash(f"Campaña «{campana.nombre}» creada. Crea al menos dos legiones y contrata sus tropas "
              "para preparar un enfrentamiento.", "exito")
        return redirect(url_for("campana.panel"))
    return render_template("campana_nueva.html", valores={}, anterior=campana_actual(requerida=False))


@bp.get("/campana")
def panel():
    return render_template("campana_panel.html", campana=campana_actual())


@bp.get("/campana/guardar")
def guardar():
    """CU013: descarga la campaña completa; el navegador muestra el diálogo «Guardar como»."""
    campana = campana_actual()
    return Response(
        exportar_campana(campana), mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo(campana)}"',
                 "Cache-Control": "no-store"},
    )


@bp.post("/campana/cargar")
def cargar():
    """CU014: reconstruye la campaña del archivo y la deja abierta."""
    archivo = request.files.get("archivo")
    if archivo is None or not archivo.filename:
        flash("Elige un archivo de campaña (.json) para cargarlo.", "error")
        return redirect(_volver())
    try:
        campana = importar_campana(archivo.read())
    except ArchivoCampanaInvalido as error:
        flash(str(error), "error")
        return redirect(_volver())
    reemplaza = persistencia().existe(campana.id)
    nombre = archivo.filename.replace("\\", "/").rsplit("/", 1)[-1][:80]
    campana.bitacora.registrar_suceso("sistema", f"Se recupera la campaña desde el archivo «{nombre}».")
    campana.tocar()
    persistencia().guardar_campana(campana)
    abrir_campana(campana.id)
    detalle = ("Reemplazó la versión que había en la base de datos." if reemplaza
               else "Quedó guardada en la base de datos.")
    flash(f"Campaña «{campana.nombre}» cargada: {contar(len(campana.legiones), 'legión', 'legiones')}, "
          f"{contar(len(campana.enfrentamientos), 'enfrentamiento', 'enfrentamientos')} y "
          f"{contar(len(campana.bitacora), 'suceso', 'sucesos')}. {detalle}", "exito")
    if campana.enfrentamiento_activo():
        return redirect(url_for("combate.consola"))
    return redirect(url_for("campana.panel"))
