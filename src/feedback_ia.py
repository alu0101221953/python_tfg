"""
Generación de feedback narrativo con IA.

Usa la API de Google Gemini para generar un resumen personalizado
del perfil de aprendizaje del alumno con recomendaciones concretas.

Requiere: pip install google-genai
Requiere: variable de entorno GEMINI_API_KEY
"""

import os
import json
import hashlib

from src.modelos import CATEGORIAS

_cache: dict[str, str] = {}

# Nombres de las categorías de error
CAT_NOMBRES = CATEGORIAS  # {1: "Sintaxis", 2: "Indentación", ...}


def _construir_prompt(datos: dict) -> str:
    """Construye el prompt para Gemini a partir de los datos del dashboard."""
    nombre = datos["nombre"]
    stats = datos["stats"]
    gami = datos["gamificacion"]
    bkt = datos.get("bkt", {})
    errores = datos.get("errores_top", [])

    # Resumen BKT por categoría
    lineas_bkt = []
    for cat_id in sorted(CAT_NOMBRES.keys()):
        v = bkt.get(str(cat_id))
        nombre_cat = CAT_NOMBRES[cat_id]
        if v is None:
            lineas_bkt.append(f"- {nombre_cat}: sin datos aún")
        else:
            pct = round(v["p_dominio"] * 100)
            estado = "dominada ✓" if v["dominado"] else "en progreso"
            lineas_bkt.append(
                f"- {nombre_cat}: {pct}% de dominio ({estado}, {v['num_intentos']} intento/s)"
            )

    # Errores frecuentes
    if errores:
        lineas_errores = [
            f"- Subcategoría {e['subcategoria']}: {e['frecuencia']} fallo/s"
            for e in errores
        ]
        bloque_errores = "\n".join(lineas_errores)
    else:
        bloque_errores = "- Sin errores frecuentes registrados"

    # Calcular categorías con dificultad y categorías no exploradas
    cats_dificultad = [
        CAT_NOMBRES[int(c)] for c, v in bkt.items()
        if not v["dominado"] and v["p_dominio"] < 0.50
    ]
    cats_sin_datos = [
        CAT_NOMBRES[c] for c in CAT_NOMBRES
        if str(c) not in bkt
    ]

    return f"""Eres un tutor de programación experto y empático. Tu tarea es escribir un mensaje
de feedback personalizado para el alumno '{nombre}' que está aprendiendo Python básico.

DATOS DEL ALUMNO:
- Ejercicios realizados: {stats['intentos']}
- Respuestas correctas: {stats['correctas']}
- Precisión global: {stats['precision']}%
- Puntos acumulados: {gami.get('puntos', 0)}
- Nivel actual: {gami.get('nivel', 1)}
- Racha máxima de aciertos: {gami.get('racha_maxima', 0)}

PROGRESO POR CATEGORÍA (BKT):
{chr(10).join(lineas_bkt)}

ERRORES MÁS FRECUENTES:
{bloque_errores}

CATEGORÍAS CON DIFICULTAD: {', '.join(cats_dificultad) if cats_dificultad else 'ninguna'}
CATEGORÍAS SIN EXPLORAR: {', '.join(cats_sin_datos) if cats_sin_datos else 'ninguna'}

INSTRUCCIONES PARA EL FEEDBACK:
- Dirígete al alumno por su nombre directamente
- Empieza con un resumen breve de su situación actual (1 párrafo)
- Menciona sus puntos fuertes (categorías dominadas o con buen progreso)
- Señala las áreas que necesitan más trabajo, con un consejo práctico para mejorar en ellas
- Si hay categorías sin explorar, anímale a explorarlas
- Tono motivador, cercano y honesto, sin ser condescendiente
- Sin markdown, solo texto plano
- Longitud: 3-4 párrafos
- Termina con una frase corta de ánimo"""


def _clave_cache(datos: dict) -> str:
    """Genera una clave de caché basada en los datos relevantes del alumno."""
    data = {
        "nombre": datos.get("nombre"),
        "precision": datos.get("stats", {}).get("precision"),
        "intentos": datos.get("stats", {}).get("intentos"),
        "bkt": datos.get("bkt", {}),
        "errores": datos.get("errores_top", []),
    }
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()


def generar_feedback_ia(datos: dict) -> dict:
    """
    Genera feedback narrativo personalizado usando Google Gemini.

    Args:
        datos: dict con las mismas claves que devuelve /api/dashboard/{id}

    Returns:
        {
            "feedback": str,
            "fuente":   "llm" | "cache" | "fallback",
            "error":    None | str
        }
    """
    clave = _clave_cache(datos)

    if clave in _cache:
        return {"feedback": _cache[clave], "fuente": "cache", "error": None}

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "feedback": _feedback_fallback(datos),
            "fuente": "fallback",
            "error": "GEMINI_API_KEY no configurada. Añádela al fichero .env.",
        }

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        prompt = _construir_prompt(datos)
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=prompt,
        )

        texto = response.text.strip()
        _cache[clave] = texto

        return {"feedback": texto, "fuente": "llm", "error": None}

    except Exception as e:
        return {
            "feedback": _feedback_fallback(datos),
            "fuente": "fallback",
            "error": str(e),
        }


def _feedback_fallback(datos: dict) -> str:
    """Feedback de plantilla cuando la API no está disponible."""
    nombre = datos.get("nombre", "alumno")
    stats = datos.get("stats", {})
    gami = datos.get("gamificacion", {})
    bkt = datos.get("bkt", {})

    precision = stats.get("precision", 0)
    intentos = stats.get("intentos", 0)
    nivel = gami.get("nivel", 1)

    dominadas = [CAT_NOMBRES[int(c)] for c, v in bkt.items() if v["dominado"]]
    dificultad  = [CAT_NOMBRES[int(c)] for c, v in bkt.items()
                   if not v["dominado"] and v["p_dominio"] < 0.50]
    sin_datos = [CAT_NOMBRES[c] for c in CAT_NOMBRES if str(c) not in bkt]

    parrafos = []

    if intentos == 0:
        return (f"Hola {nombre}, aún no has respondido ningún ejercicio. "
                f"¡Empieza a practicar para ver tu progreso aquí!")

    if precision >= 75:
        parrafos.append(
            f"Hola {nombre}, llevas {intentos} ejercicios resueltos con una precisión del "
            f"{precision}% — un resultado sólido. Estás en el nivel {nivel} y tu progreso "
            f"es consistente."
        )
    else:
        parrafos.append(
            f"Hola {nombre}, llevas {intentos} ejercicios resueltos con una precisión del "
            f"{precision}%. Hay margen de mejora, pero lo importante es que sigues practicando."
        )

    if dominadas:
        parrafos.append(
            f"Has dominado las siguientes categorías: {', '.join(dominadas)}. "
            f"¡Buen trabajo en esas áreas!"
        )

    if dificultad:
        parrafos.append(
            f"Las categorías donde más dificultad encuentras son: {', '.join(dificultad)}. "
            f"Dedica algo más de tiempo a los ejercicios de esas áreas y notarás la mejora."
        )

    if sin_datos:
        parrafos.append(
            f"Aún no has explorado estas categorías: {', '.join(sin_datos)}. "
            f"¡Anímate a probarlas!"
        )

    parrafos.append("Sigue así, ¡cada ejercicio cuenta!")
    return "\n\n".join(parrafos)