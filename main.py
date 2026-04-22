"""
Sistema tutor inteligente para Python básico.
TFG · Víctor Cánovas del Pino · Universidad de La Laguna · 2025-2026
"""

import json
import random
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from src.modelos import Alumno, Traza, RespuestaAlumno
from src.database import cargar_alumno, guardar_alumno, eliminar_alumno
from src.analizador import construir_traza

load_dotenv()

app       = FastAPI(title="TFG", version="0.1.0")
templates = Jinja2Templates(directory="templates")

_banco_cache: list[dict] | None = None

def cargar_banco() -> list[dict]:
    global _banco_cache
    if _banco_cache is None:
        with open(Path("data/banco_preguntas.json"), encoding="utf-8") as f:
            _banco_cache = json.load(f)["preguntas"]
    return _banco_cache


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={})


# ===========================================================================
# API — Banco
# ===========================================================================

@app.get("/api/banco/info")
def banco_info():
    """Devuelve información general del banco de preguntas."""
    banco = cargar_banco()
    por_categoria = {}
    for p in banco:
        cat = str(p["categoria"])
        por_categoria[cat] = por_categoria.get(cat, 0) + 1
    return JSONResponse(content={
        "total":         len(banco),
        "por_categoria": por_categoria,
    })


# ===========================================================================
# API — Alumno
# ===========================================================================

@app.post("/api/alumno/iniciar")
def iniciar_sesion(nombre: str, id_alumno: str = ""):
    """Crea un perfil nuevo o carga uno existente."""
    if not id_alumno:
        sufijo    = datetime.now().strftime("%H%M%S")
        id_alumno = f"{nombre.lower().strip()[:10].replace(' ', '_')}_{sufijo}"

    datos = cargar_alumno(id_alumno)
    if datos is None:
        alumno = Alumno(id_alumno=id_alumno, nombre=nombre)
        guardar_alumno(alumno)
        nuevo = True
    else:
        alumno = Alumno(**datos)
        if nombre and alumno.nombre != nombre:
            alumno.nombre = nombre
            guardar_alumno(alumno)
        nuevo = False

    return JSONResponse(content={
        "id_alumno": alumno.id_alumno,
        "nombre":    alumno.nombre,
        "nuevo":     nuevo,
        "intentos":  alumno.total_intentos(),
        "precision": alumno.precision_global(),
    })


@app.get("/api/alumno/{id_alumno}")
def obtener_alumno(id_alumno: str):
    datos = cargar_alumno(id_alumno)
    if datos is None:
        return JSONResponse(status_code=404, content={"error": "Alumno no encontrado."})
    alumno = Alumno(**datos)
    return JSONResponse(content={
        "id_alumno": alumno.id_alumno,
        "nombre":    alumno.nombre,
        "intentos":  alumno.total_intentos(),
        "correctas": alumno.total_correctas(),
        "precision": alumno.precision_global(),
    })


@app.delete("/api/alumno/{id_alumno}")
def borrar_alumno(id_alumno: str):
    if eliminar_alumno(id_alumno):
        return JSONResponse(content={"ok": True})
    return JSONResponse(status_code=404, content={"error": "Alumno no encontrado."})


# ===========================================================================
# API — Ejercicios
# ===========================================================================

@app.get("/api/ejercicio/siguiente")
def siguiente_ejercicio(id_alumno: str):
    """Devuelve una pregunta aleatoria no vista por el alumno."""
    datos = cargar_alumno(id_alumno)
    if datos is None:
        return JSONResponse(status_code=404, content={"error": "Alumno no encontrado."})

    alumno      = Alumno(**datos)
    vistas      = alumno.preguntas_vistas()
    banco       = cargar_banco()
    disponibles = [p for p in banco if p["id"] not in vistas]

    if not disponibles:
        return JSONResponse(content={
            "fin_banco": True,
            "mensaje":   "¡Has respondido todas las preguntas! Vuelve más tarde.",
        })

    pregunta = random.choice(disponibles)
    return JSONResponse(content={
        "id":           pregunta["id"],
        "categoria":    pregunta["categoria"],
        "subcategoria": pregunta["subcategoria"],
        "nivel":        pregunta["nivel"],
        "tipo":         pregunta["tipo"],
        "enunciado":    pregunta["enunciado"],
        "codigo":       pregunta.get("codigo", ""),
        "opciones":     pregunta.get("opciones", []),
        "hueco":        pregunta.get("hueco", ""),
        "pista":        pregunta.get("pista", ""),
        "contador": {
            "vistas": len(vistas),
            "total":  len(banco),
        },
    })


@app.post("/api/ejercicio/responder")
def responder_ejercicio(payload: RespuestaAlumno):
    """
    Evalúa la respuesta, guarda la traza y devuelve feedback
    junto con la siguiente pregunta.
    """
    datos = cargar_alumno(payload.id_alumno)
    if datos is None:
        return JSONResponse(status_code=404, content={"error": "Alumno no encontrado."})

    alumno = Alumno(**datos)

    # Evaluar y guardar traza
    traza_dict, feedback = construir_traza(
        payload.id_pregunta,
        payload.respuesta,
        payload.tiempo,
    )
    alumno.trazas.append(Traza(**traza_dict))
    guardar_alumno(alumno)

    # Siguiente pregunta aleatoria
    vistas      = alumno.preguntas_vistas()
    banco       = cargar_banco()
    disponibles = [p for p in banco if p["id"] not in vistas]
    siguiente   = random.choice(disponibles) if disponibles else None

    sig_data = None
    if siguiente:
        sig_data = {
            "id":           siguiente["id"],
            "categoria":    siguiente["categoria"],
            "subcategoria": siguiente["subcategoria"],
            "nivel":        siguiente["nivel"],
            "tipo":         siguiente["tipo"],
            "enunciado":    siguiente["enunciado"],
            "codigo":       siguiente.get("codigo", ""),
            "opciones":     siguiente.get("opciones", []),
            "hueco":        siguiente.get("hueco", ""),
            "pista":        siguiente.get("pista", ""),
            "contador": {
                "vistas": len(vistas),
                "total":  len(banco),
            },
        }

    return JSONResponse(content={
        "feedback":           feedback,
        "siguiente_pregunta": sig_data,
        "fin_banco":          siguiente is None,
        "stats": {
            "intentos":  alumno.total_intentos(),
            "correctas": alumno.total_correctas(),
            "precision": alumno.precision_global(),
        },
    })