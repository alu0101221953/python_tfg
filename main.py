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
from src.bkt import calcular_bkt_alumno, resumen_bkt
from src.recomendador import seleccionar_siguiente_pregunta, cargar_banco as cargar_banco_recomendador
from src.gamificacion import PerfilGamificacion, actualizar_gamificacion, comprobar_insignias

load_dotenv()

app = FastAPI(title="TFG", version="0.1.0")
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

@app.get("/ejercicio", response_class=HTMLResponse)
def ejercicio(request: Request):
    return templates.TemplateResponse(request=request, name="ejercicio.html", context={})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html", context={})

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
        "total": len(banco),
        "por_categoria": por_categoria,
    })


# ===========================================================================
# API — Alumno
# ===========================================================================

@app.post("/api/alumno/iniciar")
def iniciar_sesion(nombre: str, id_alumno: str = "", curso: str = ""):
    """Crea un perfil nuevo o carga uno existente."""
    if not id_alumno:
        sufijo = datetime.now().strftime("%H%M%S")
        id_alumno = f"{nombre.lower().strip()[:10].replace(' ', '_')}_{sufijo}"

    datos = cargar_alumno(id_alumno)
    if datos is None:
        alumno = Alumno(id_alumno=id_alumno, nombre=nombre, curso=curso)
        guardar_alumno(alumno)
        nuevo = True
    else:
        alumno = Alumno(**datos)
        if nombre and alumno.nombre != nombre:
            alumno.nombre = nombre
        if curso and alumno.curso != curso:
            alumno.curso = curso
        guardar_alumno(alumno)
        nuevo = False

    return JSONResponse(content={
        "id_alumno": alumno.id_alumno,
        "nombre": alumno.nombre,
        "curso": alumno.curso,
        "nuevo": nuevo,
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
        "nombre": alumno.nombre,
        "intentos": alumno.total_intentos(),
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
    alumno = Alumno(**datos)
    banco = cargar_banco()
    vistas = alumno.preguntas_vistas()
    pregunta = seleccionar_siguiente_pregunta(alumno)
    if pregunta is None:
        return JSONResponse(content={
            "fin_banco": True,
            "mensaje": "¡Has respondido todas las preguntas! Vuelve más tarde.",
        })
    return JSONResponse(content={
        "id": pregunta["id"],
        "categoria": pregunta["categoria"],
        "subcategoria": pregunta["subcategoria"],
        "nivel": pregunta["nivel"],
        "tipo": pregunta["tipo"],
        "enunciado": pregunta["enunciado"],
        "codigo": pregunta.get("codigo", ""),
        "opciones": pregunta.get("opciones", []),
        "hueco": pregunta.get("hueco", ""),
        "pistas": pregunta.get("pistas", []),
        "contador": {
            "vistas": len(vistas),
            "total": len(banco),
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
        payload.pistas_usadas,
    )
    alumno.trazas.append(Traza(**traza_dict))

    # Actualizar gamificación (con penalización por pistas usadas)
    gami = PerfilGamificacion(**alumno.gamificacion)
    gami, eventos = actualizar_gamificacion(gami, traza_dict["correcta"], payload.pistas_usadas)

    # Comprobar insignias
    bkt_temp = calcular_bkt_alumno(alumno.trazas)
    cats_dominadas = [c for c, v in bkt_temp.items() if v["dominado"]]
    nuevas_insignias = comprobar_insignias(gami, alumno.total_correctas(), cats_dominadas)
    eventos += [f"insignia:{ins}" for ins in nuevas_insignias]

    alumno.gamificacion = gami.model_dump()
    guardar_alumno(alumno)

    # Siguiente pregunta adaptativa (BKT)
    siguiente = seleccionar_siguiente_pregunta(alumno)
    vistas = alumno.preguntas_vistas()
    banco = cargar_banco()

    sig_data = None
    if siguiente:
        sig_data = {
            "id": siguiente["id"],
            "categoria": siguiente["categoria"],
            "subcategoria": siguiente["subcategoria"],
            "nivel": siguiente["nivel"],
            "tipo": siguiente["tipo"],
            "enunciado": siguiente["enunciado"],
            "codigo": siguiente.get("codigo", ""),
            "opciones": siguiente.get("opciones", []),
            "hueco": siguiente.get("hueco", ""),
            "pistas": siguiente.get("pistas", []),
            "contador": {
                "vistas": len(vistas),
                "total": len(banco),
            },
        }

    # Calcular BKT actualizado
    bkt = calcular_bkt_alumno(alumno.trazas)
    resumen = resumen_bkt(bkt)

    return JSONResponse(content={
        "feedback": feedback,
        "siguiente_pregunta": sig_data,
        "fin_banco": siguiente is None,
        "gamificacion": alumno.gamificacion,
        "eventos": eventos,
        "stats": {
            "intentos": alumno.total_intentos(),
            "correctas": alumno.total_correctas(),
            "precision": alumno.precision_global(),
        },
        "bkt": {
            str(cat): {
                "p_dominio": v["p_dominio"],
                "dominado": v["dominado"],
                "num_intentos": v["num_intentos"],
                "nombre": v["nombre"],
            }
            for cat, v in bkt.items()
        },
        "bkt_resumen": resumen,
    })

# ===========================================================================
# API — Profesor
# ===========================================================================

@app.get("/profesor", response_class=HTMLResponse)
def profesor(request: Request):
    return templates.TemplateResponse(request=request, name="profesor.html", context={})

@app.get("/api/profesor/alumnos")
def profesor_alumnos(clave: str = ""):
    """Devuelve datos agregados de todos los alumnos (requiere clave)."""
    import os
    from collections import Counter
    from src.database import listar_alumnos

    clave_correcta = os.getenv("PROFESOR_CLAVE", "profesor123")
    if clave != clave_correcta:
        return JSONResponse(status_code=401, content={"error": "Clave incorrecta."})

    ids = listar_alumnos()
    alumnos_data = []

    for id_alumno in ids:
        datos = cargar_alumno(id_alumno)
        if not datos:
            continue
        alumno = Alumno(**datos)
        bkt = calcular_bkt_alumno(alumno.trazas)
        resumen = resumen_bkt(bkt)

        # Última actividad
        ultima = max((t.timestamp for t in alumno.trazas), default="—")[:10]

        # Errores más frecuentes
        errores = Counter(
            t.subcategoria for t in alumno.trazas
            if not t.correcta and t.subcategoria
        )

        alumnos_data.append({
            "id_alumno": alumno.id_alumno,
            "nombre": alumno.nombre,
            "curso": alumno.curso,
            "intentos": alumno.total_intentos(),
            "correctas": alumno.total_correctas(),
            "precision": alumno.precision_global(),
            "puntos": alumno.gamificacion.get("puntos", 0),
            "nivel": alumno.gamificacion.get("nivel", 1),
            "ultima": ultima,
            "bkt": {
                str(cat): {
                    "p_dominio": v["p_dominio"],
                    "dominado": v["dominado"],
                    "nombre": v["nombre"],
                }
                for cat, v in bkt.items()
            },
            "bkt_resumen": resumen,
            "errores_top": [
                {"subcategoria": s, "frecuencia": f}
                for s, f in errores.most_common(3)
            ],
        })

    # Errores recurrentes globales de la clase
    todos_errores = Counter()
    for a in alumnos_data:
        for e in a["errores_top"]:
            todos_errores[e["subcategoria"]] += e["frecuencia"]

    return JSONResponse(content={
        "total_alumnos": len(alumnos_data),
        "alumnos":       alumnos_data,
        "errores_clase": [
            {"subcategoria": s, "frecuencia": f}
            for s, f in todos_errores.most_common(5)
        ],
    })


# ===========================================================================
# API — Dashboard
# ===========================================================================
 
@app.get("/api/dashboard/{id_alumno}")
def dashboard_alumno(id_alumno: str):
    """Devuelve el diagnóstico completo del alumno."""
    from collections import defaultdict, Counter
 
    datos = cargar_alumno(id_alumno)
    if datos is None:
        return JSONResponse(status_code=404, content={"error": "Alumno no encontrado."})
 
    alumno = Alumno(**datos)
    bkt = calcular_bkt_alumno(alumno.trazas)
    resumen = resumen_bkt(bkt)
 
    # Evolución temporal agrupada por día
    por_dia: dict = defaultdict(lambda: {"intentos": 0, "correctas": 0})
    for t in alumno.trazas:
        dia = t.timestamp[:10]
        por_dia[dia]["intentos"] += 1
        por_dia[dia]["correctas"] += int(t.correcta)
 
    evolucion = [
        {
            "dia": dia,
            "intentos": v["intentos"],
            "correctas": v["correctas"],
            "precision": round(v["correctas"] / v["intentos"] * 100) if v["intentos"] else 0,
        }
        for dia, v in sorted(por_dia.items())
    ]
 
    # Errores más frecuentes por subcategoría
    errores = Counter(
        t.subcategoria for t in alumno.trazas
        if not t.correcta and t.subcategoria
    )
    errores_top = [
        {"subcategoria": sub, "frecuencia": freq}
        for sub, freq in errores.most_common(5)
    ]
 
    return JSONResponse(content={
        "id_alumno": alumno.id_alumno,
        "nombre": alumno.nombre,
        "stats": {
            "intentos": alumno.total_intentos(),
            "correctas": alumno.total_correctas(),
            "precision": alumno.precision_global(),
        },
        "gamificacion": alumno.gamificacion,
        "bkt": {
            str(cat): {
                "p_dominio": v["p_dominio"],
                "dominado": v["dominado"],
                "num_intentos": v["num_intentos"],
                "nombre": v["nombre"],
            }
            for cat, v in bkt.items()
        },
        "bkt_resumen": resumen,
        "evolucion": evolucion,
        "errores_top": errores_top,
    })
