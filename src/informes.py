"""
Generación de informes PDF.

Usa reportlab para construir un informe individual del alumno con:
  - Datos generales (nombre, curso, fecha)
  - Estadísticas globales (ejercicios, precisión, puntos, nivel)
  - Progreso BKT por categoría
  - Insignias conseguidas
  - Errores más frecuentes
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

from src.modelos import CATEGORIAS


INSIGNIA_DEF = {
    "primer_acierto": ("🏅", "Primer acierto"),
    "racha_3": ("🔥", "Racha de 3"),
    "racha_5": ("🔥", "Racha de 5"),
    "racha_10": ("🔥", "Racha de 10"),
    "nivel_2": ("⬆", "Nivel 2"),
    "nivel_5": ("⬆", "Nivel 5"),
    "nivel_10": ("⬆", "Nivel 10"),
    "10_correctas": ("✓", "10 correctas"),
    "25_correctas": ("✓", "25 correctas"),
    "50_correctas": ("✓", "50 correctas"),
}

COLOR_ACCENT = colors.HexColor("#7c6af7")
COLOR_OK = colors.HexColor("#4caf7d")
COLOR_FAIL = colors.HexColor("#f06292")
COLOR_MUTED = colors.HexColor("#6b7080")
COLOR_BORDER = colors.HexColor("#dcdde3")


def _nombre_insignia(ins: str) -> str:
    if ins.startswith("domina_cat_"):
        try:
            cat = int(ins.replace("domina_cat_", ""))
            return f"Domina {CATEGORIAS.get(cat, f'Categoría {cat}')}"
        except ValueError:
            pass
    _, nombre = INSIGNIA_DEF.get(ins, ("", ins))
    return nombre


def generar_informe_alumno(datos: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2*cm, rightMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle("Titulo", parent=styles["Title"],
        textColor=COLOR_ACCENT, fontSize=20, spaceAfter=4)
    subtitulo_style = ParagraphStyle("Subtitulo", parent=styles["Normal"],
        textColor=COLOR_MUTED, fontSize=10, spaceAfter=20)
    seccion_style = ParagraphStyle("Seccion", parent=styles["Heading2"],
        fontSize=13, spaceBefore=18, spaceAfter=8,
        textColor=colors.HexColor("#1a1d27"))
    normal_style = styles["Normal"]

    elementos = []

    # Cabecera
    elementos.append(Paragraph("Informe de progreso — PyTutor", titulo_style))
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    curso_txt = f" · Curso: {datos.get('curso')}" if datos.get("curso") else ""
    elementos.append(Paragraph(
        f"Alumno: <b>{datos['nombre']}</b>{curso_txt} · Generado el {fecha}",
        subtitulo_style))

    # Estadísticas generales
    stats = datos.get("stats", {})
    gami  = datos.get("gamificacion", {})
    elementos.append(Paragraph("Resumen general", seccion_style))
    tabla_stats = Table([
        ["Ejercicios realizados", "Precisión", "Puntos", "Nivel"],
        [str(stats.get("intentos", 0)), f"{stats.get('precision', 0)}%",
         str(gami.get("puntos", 0)), str(gami.get("nivel", 1))],
    ], colWidths=[4*cm]*4)
    tabla_stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f1ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_ACCENT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
    ]))
    elementos.append(tabla_stats)

    # Progreso por categoría (BKT)
    elementos.append(Paragraph("Progreso por categoría", seccion_style))
    bkt = datos.get("bkt", {})
    filas_bkt = [["Categoría", "Dominio estimado", "Estado", "Intentos"]]
    for cat_id in sorted(CATEGORIAS.keys()):
        v = bkt.get(str(cat_id))
        nombre_cat = CATEGORIAS[cat_id]
        if v is None:
            filas_bkt.append([nombre_cat, "—", "Sin datos", "0"])
        else:
            pct = round(v["p_dominio"] * 100)
            estado = "Dominada" if v["dominado"] else "En progreso"
            filas_bkt.append([nombre_cat, f"{pct}%", estado, str(v["num_intentos"])])

    tabla_bkt = Table(filas_bkt, colWidths=[5*cm, 4*cm, 4*cm, 3*cm])
    estilo_bkt = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f1ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_ACCENT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
    ]
    for i, fila in enumerate(filas_bkt[1:], start=1):
        if fila[2] == "Dominada":
            estilo_bkt.append(("TEXTCOLOR", (2, i), (2, i), COLOR_OK))
        elif fila[2] == "Sin datos":
            estilo_bkt.append(("TEXTCOLOR", (2, i), (2, i), COLOR_MUTED))
    tabla_bkt.setStyle(TableStyle(estilo_bkt))
    elementos.append(tabla_bkt)

    # Insignias
    elementos.append(Paragraph("Insignias conseguidas", seccion_style))
    insignias = gami.get("insignias", [])
    if insignias:
        elementos.append(Paragraph(
            " · ".join(_nombre_insignia(i) for i in insignias), normal_style))
    else:
        elementos.append(Paragraph(
            "Todavía no se ha conseguido ninguna insignia.",
            ParagraphStyle("muted", parent=normal_style, textColor=COLOR_MUTED)))

    # Errores más frecuentes
    elementos.append(Paragraph("Errores más frecuentes", seccion_style))
    errores = datos.get("errores_top", [])
    if errores:
        filas_err = [["Subcategoría", "Frecuencia"]] + [
            [e["subcategoria"], str(e["frecuencia"])] for e in errores]
        tabla_err = Table(filas_err, colWidths=[8*cm, 4*cm])
        tabla_err.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fdeef2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_FAIL),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ]))
        elementos.append(tabla_err)
    else:
        elementos.append(Paragraph(
            "No se han registrado errores significativos.",
            ParagraphStyle("muted", parent=normal_style, textColor=COLOR_MUTED)))

    elementos.append(Spacer(1, 1*cm))
    elementos.append(Paragraph(
        "Informe generado automáticamente.",
        ParagraphStyle("footer", parent=normal_style, fontSize=8, textColor=COLOR_MUTED)))

    doc.build(elementos)
    return buffer.getvalue()


def generar_informe_clase(datos: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2*cm, rightMargin=2*cm,
    )

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle("Titulo", parent=styles["Title"],
        textColor=COLOR_ACCENT, fontSize=20, spaceAfter=4)
    subtitulo_style = ParagraphStyle("Subtitulo", parent=styles["Normal"],
        textColor=COLOR_MUTED, fontSize=10, spaceAfter=20)
    seccion_style = ParagraphStyle("Seccion", parent=styles["Heading2"],
        fontSize=13, spaceBefore=18, spaceAfter=8,
        textColor=colors.HexColor("#1a1d27"))
    normal_style = styles["Normal"]

    elementos = []

    # Cabecera
    elementos.append(Paragraph("Informe de clase — PyTutor", titulo_style))
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    elementos.append(Paragraph(f"Generado el {fecha}", subtitulo_style))

    alumnos = datos.get("alumnos", [])
    total_ejercicios = sum(a.get("intentos", 0) for a in alumnos)
    precision_media = (
        round(sum(a.get("precision", 0) for a in alumnos) / len(alumnos))
        if alumnos else 0)

    # Métricas globales
    elementos.append(Paragraph("Resumen general", seccion_style))
    tabla_resumen = Table([
        ["Alumnos registrados", "Precisión media", "Ejercicios totales"],
        [str(datos.get("total_alumnos", len(alumnos))), f"{precision_media}%", str(total_ejercicios)],
    ], colWidths=[5.5*cm]*3)
    tabla_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f1ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_ACCENT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
    ]))
    elementos.append(tabla_resumen)

    # Errores más frecuentes
    elementos.append(Paragraph("Errores más frecuentes en la clase", seccion_style))
    errores_clase = datos.get("errores_clase", [])
    if errores_clase:
        filas_err = [["Subcategoría", "Frecuencia"]] + [
            [e["subcategoria"], str(e["frecuencia"])] for e in errores_clase]
        tabla_err = Table(filas_err, colWidths=[8*cm, 4*cm])
        tabla_err.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fdeef2")),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_FAIL),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ]))
        elementos.append(tabla_err)
    else:
        elementos.append(Paragraph("Sin datos suficientes todavía.",
            ParagraphStyle("muted", parent=normal_style, textColor=COLOR_MUTED)))

    # Tabla de alumnos
    elementos.append(Paragraph("Alumnos", seccion_style))
    filas_alumnos = [["Nombre", "Curso", "Ejerc.", "Precisión", "Puntos", "Cats. dominadas"]]
    for a in alumnos:
        bkt = a.get("bkt", {})
        dominadas = sum(1 for v in bkt.values() if v.get("dominado"))
        filas_alumnos.append([
            a.get("nombre", ""),
            a.get("curso") or "—",
            str(a.get("intentos", 0)),
            f"{a.get('precision', 0)}%",
            str(a.get("puntos", 0)),
            f"{dominadas}/{len(CATEGORIAS)}",
        ])

    tabla_alumnos = Table(filas_alumnos, colWidths=[4*cm, 2.5*cm, 2*cm, 2.5*cm, 2*cm, 4*cm])
    tabla_alumnos.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f1ff")),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_ACCENT),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafc")]),
    ]))
    elementos.append(tabla_alumnos)

    elementos.append(Spacer(1, 1*cm))
    elementos.append(Paragraph(
        "Informe generado automáticamente por PyTutor — Sistema tutor inteligente para Python básico.",
        ParagraphStyle("footer", parent=normal_style, fontSize=8, textColor=COLOR_MUTED)))

    doc.build(elementos)
    return buffer.getvalue()
