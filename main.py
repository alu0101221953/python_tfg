"""
Sistema tutor inteligente para Python básico.
TFG · Víctor Cánovas del Pino · Universidad de La Laguna · 2025-2026
"""

import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from src.modelos import Alumno, Traza, RespuestaAlumno
from src.database import cargar_alumno, guardar_alumno, eliminar_alumno

load_dotenv()

app = FastAPI(title="TFG", version="0.1.0")

_banco_cache: list[dict] | None = None

def cargar_banco_preguntas() -> list[dict]:
    global _banco_cache
    if _banco_cache is None:
        with open(Path("data/banco_preguntas.json"), encoding="utf-8") as f:
            _banco_cache = json.load(f)["preguntas"]
    return _banco_cache


@app.get("/")
def index():
    return JSONResponse(content={
        "mensaje": "TFG API funcionando",
        "version": "0.1.0",
    })


@app.get("/api/banco/info")
def banco_info():
    """Devuelve información general del banco de preguntas."""
    banco = cargar_banco_preguntas()
    por_categoria = {}
    for p in banco:
        cat = str(p["categoria"])
        por_categoria[cat] = por_categoria.get(cat, 0) + 1
    return JSONResponse(content={
        "total": len(banco),
        "categorias": por_categoria,
    })


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
        "nombre": alumno.nombre,
        "nuevo": nuevo,
        "intentos": alumno.total_intentos(),
        "precision": alumno.precision_global(),
    })

@app.get("/api/alumno/{id_alumno}")
def obtener_alumno(id_alumno: str):
    """Devuelve el perfil completo de un alumno."""
    datos = cargar_alumno(id_alumno)
    if datos is None:
        return JSONResponse(status_code=404, content={"error": "Alumno no encontrado"})
    alumno = Alumno(**datos)
    return JSONResponse(content={
        "id_alumno": alumno.id_alumno,
        "nombre": alumno.nombre,
        "intentos": alumno.total_intentos(),
        "correctas": alumno.total_correctas(),
        "precision": alumno.precision_global(),
    })

@app.delete("/api/alumno/{id_alumno}")
def borrar_alumno(id_alumno: str):
    """Elimina el perfil de un alumno."""
    if eliminar_alumno(id_alumno):
        return JSONResponse(content={"ok": True})
    return JSONResponse(status_code=404, content={"error": "Alumno no encontrado."})