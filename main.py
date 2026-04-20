"""
Sistema tutor inteligente para Python básico.
TFG · Víctor Cánovas del Pino · Universidad de La Laguna · 2025-2026
"""

from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from src.modelos import Alumno, Traza, RespuestaAlumno
from src.database import cargar_alumno, guardar_alumno, eliminar_alumno

load_dotenv()

app = FastAPI(title="TFG", version="0.1.0")


@app.get("/")
def index():
    return JSONResponse(content={
        "mensaje": "TFG API funcionando",
        "version": "0.1.0",
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
