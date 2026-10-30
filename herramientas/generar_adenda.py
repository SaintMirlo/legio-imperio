"""Anexa la adenda sin volver a componer las páginas del informe original.

Uso: python herramientas/generar_adenda.py --original "ruta/Proyecto Ingeso.pdf"
Requiere las fuentes Times New Roman del informe; no las distribuye.
"""
import argparse
import hashlib
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle

RAIZ = Path(__file__).resolve().parents[1]
ANCHO, ALTO = 596, 842
IZQUIERDA, DERECHA = 63.7795257568, 69.7795257568
ANCHO_TEXTO = ANCHO - IZQUIERDA - DERECHA
ANCHOS_TABLAS = {
    6: (0.15, 0.23, 0.62),
    7: (0.19, 0.40, 0.41),
    8: (0.10, 0.66, 0.24),
    9: (0.19, 0.81),
    10: (0.32, 0.23, 0.45),
    11: (0.20, 0.16, 0.64),
    12: (0.46, 0.54),
    13: (0.12, 0.20, 0.27, 0.41),
}


def registrar_fuentes(carpeta):
    for nombre, archivo in (("TNR", "times.ttf"), ("TNR-Bold", "timesbd.ttf"), ("TNR-Italic", "timesi.ttf")):
        ruta = carpeta / archivo
        if not ruta.is_file():
            raise FileNotFoundError(f"Falta la fuente del informe: {ruta}")
        pdfmetrics.registerFont(TTFont(nombre, str(ruta)))


def estilos():
    cuerpo = ParagraphStyle(
        "Cuerpo", fontName="TNR", fontSize=12, leading=15.86865,
        alignment=TA_JUSTIFY, spaceAfter=10, textColor=colors.black,
    )
    return {
        "cuerpo": cuerpo,
        "titulo": ParagraphStyle("Titulo", parent=cuerpo, fontName="TNR-Bold", fontSize=14,
                                  leading=17, alignment=TA_CENTER, spaceBefore=0, spaceAfter=18),
        "subtitulo": ParagraphStyle("Subtitulo", parent=cuerpo, fontName="TNR-Bold", fontSize=14,
                                     leading=17, alignment=TA_CENTER, spaceBefore=8, spaceAfter=14),
        "menor": ParagraphStyle("Menor", parent=cuerpo, fontName="TNR-Bold", alignment=TA_CENTER,
                                spaceBefore=8, spaceAfter=10),
        "leyenda": ParagraphStyle("Leyenda", parent=cuerpo, fontName="TNR-Italic", fontSize=11,
                                  leading=13, alignment=TA_CENTER, spaceBefore=4, spaceAfter=6),
        "celda": ParagraphStyle("Celda", parent=cuerpo, leading=13.79883, alignment=TA_LEFT, spaceAfter=0),
    }


def componer_pagina(texto, estilos_pagina):
    lineas = texto.strip().splitlines()
    elementos = []
    indice = 0
    cuadro = None
    while indice < len(lineas):
        linea = lineas[indice].strip()
        if not linea:
            indice += 1
            continue
        if linea.startswith("|"):
            filas = []
            while indice < len(lineas) and lineas[indice].strip().startswith("|"):
                valores = [c.strip() for c in lineas[indice].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in valores):
                    filas.append([Paragraph(escape(c), estilos_pagina["celda"]) for c in valores])
                indice += 1
            proporciones = ANCHOS_TABLAS.get(cuadro, (0.87, 0.13))
            tabla = Table(filas, colWidths=[ANCHO_TEXTO * p for p in proporciones], repeatRows=1, hAlign="LEFT")
            tabla.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cad5e5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3.75),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3.75),
                ("TOPPADDING", (0, 0), (-1, -1), 3.75),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.75),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f5f9")]),
            ]))
            elementos.extend((tabla, Spacer(1, 12)))
            cuadro = None
            continue
        if linea.startswith("### "):
            estilo, contenido = "menor", linea[4:]
        elif linea.startswith("## "):
            estilo, contenido = ("titulo" if not elementos else "subtitulo"), linea[3:]
        elif linea.startswith("# "):
            estilo, contenido = "titulo", linea[2:]
        elif linea.startswith("Cuadro "):
            cuadro = int(linea.split()[1])
            estilo, contenido = "leyenda", linea
        else:
            parrafo = [linea]
            while indice + 1 < len(lineas) and lineas[indice + 1].strip() and not lineas[indice + 1].startswith(("#", "|")):
                indice += 1
                parrafo.append(lineas[indice].strip())
            estilo, contenido = "cuerpo", " ".join(parrafo)
        elementos.append(Paragraph(escape(contenido), estilos_pagina[estilo]))
        indice += 1
    return elementos


def crear_pagina(texto, numero, estilos_pagina):
    salida = BytesIO()
    documento = BaseDocTemplate(salida, pagesize=(ANCHO, ALTO))
    marco = Frame(IZQUIERDA, 72, ANCHO_TEXTO, ALTO - 72 - 72,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def pie(canvas, _documento):
        canvas.setFont("TNR", 11)
        canvas.drawRightString(ANCHO - DERECHA, 40, str(numero))

    documento.addPageTemplates(PageTemplate(id="informe", frames=[marco], onPage=pie))
    documento.build(componer_pagina(texto, estilos_pagina))
    salida.seek(0)
    pagina = PdfReader(salida)
    if len(pagina.pages) != 1:
        raise ValueError(f"La página {numero} ocupa {len(pagina.pages)} páginas; ajustar el contenido sin reducir la tipografía.")
    return pagina


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--adenda", type=Path, default=RAIZ / "docs/adenda-hito-2.md")
    parser.add_argument("--salida", type=Path, default=RAIZ / "docs/Proyecto-Ingeso-Hito-2-ampliado.pdf")
    parser.add_argument("--fuentes", type=Path, default=Path("C:/Windows/Fonts"))
    args = parser.parse_args()
    if args.original.resolve() == args.salida.resolve():
        raise ValueError("La salida debe ser distinta del informe original.")
    huella_original = hashlib.sha256(args.original.read_bytes()).hexdigest()
    original = PdfReader(args.original)
    if len(original.pages) != 20:
        raise ValueError("Se esperaba el informe versión 2 de 20 páginas.")
    if any(tuple(map(float, p.mediabox[2:])) != (ANCHO, ALTO) for p in original.pages):
        raise ValueError("El tamaño del original no corresponde al informe revisado.")
    registrar_fuentes(args.fuentes)
    estilos_pagina = estilos()
    paginas = args.adenda.read_text(encoding="utf-8").split("<!-- pagina -->")
    if len(paginas) != 8:
        raise ValueError("El índice de la adenda requiere ocho páginas nuevas.")
    escritor = PdfWriter()
    escritor.append(original)
    for numero, texto in enumerate(paginas, 21):
        escritor.append(crear_pagina(texto, numero, estilos_pagina))
    escritor.add_outline_item("Complementos de la especificación", 20)
    escritor.add_outline_item("Plan de pruebas del Hito 2", 25)
    escritor.add_metadata({"/Title": "Proyecto Ingeso Hito 2 con adenda 2.1", "/Author": "Los Apóstrofes"})
    salida = BytesIO()
    escritor.write(salida)
    salida.seek(0)
    resultado = PdfReader(salida)
    for indice in range(20):
        if original.pages[indice].get_contents().get_data() != resultado.pages[indice].get_contents().get_data():
            raise ValueError(f"Se alteró el contenido de la página original {indice + 1}.")
    if hashlib.sha256(args.original.read_bytes()).hexdigest() != huella_original:
        raise ValueError("El archivo original cambió durante la generación.")
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_bytes(salida.getvalue())
    print(f"Informe generado: {len(resultado.pages)} páginas; primeras 20 conservadas.")
    print(f"SHA256 del original: {huella_original}")


if __name__ == "__main__":
    main()
