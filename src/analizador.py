"""
Motor de evaluación de respuestas.
 
Responsabilidades:
  1. Comparar la respuesta del alumno con la solución correcta.
  2. Normalizar la respuesta para una comparación flexible.
  3. Construir la Traza correspondiente.
  4. Devolver feedback inmediato con explicación y pista.
"""

import re
import json
from pathlib import Path
from datetime import datetime

_BANCO_PATH = Path(__file__).parent.parent / "data" / "banco_preguntas.json"
_banco: dict[str, dict] | None = None


def _cargar_banco() -> dict[str, dict]:
    global _banco
    if _banco is None:
        with open(_BANCO_PATH, encoding="utf-8") as f:
            preguntas = json.load(f)["preguntas"]
        _banco = {p["id"]: p for p in preguntas}
    return _banco


def _normalizar(texto: str) -> str:
    """
    Normaliza una respuesta para comparación flexible:
    - Preserva indentación inicial (preguntas de indentación, cat. 2)
    - Elimina espacios internos para que x**2 == x ** 2
    - Normaliza comillas dobles a simples
    - Convierte a minúsculas
    """
    stripped = texto.rstrip()
    indent   = len(stripped) - len(stripped.lstrip())
    niveles  = indent // 4
    core     = stripped.lstrip().lower().strip("'\"")
    core     = re.sub(r'\s+', '', core)
    core     = core.replace('"', "'")
    return ('    ' * niveles) + core


def evaluar_respuesta(id_pregunta: str, respuesta: str) -> dict:
    """
    Evalúa la respuesta del alumno.
 
    Returns:
        dict con correcta, explicacion, pista, categoria, nivel, tipo
    """
    banco = _cargar_banco()
    pregunta = banco.get(id_pregunta)

    if pregunta is None:
        return {
            "correcta": False,
            "explicacion": "Pregunta no encontrada.",
            "pista": "",
            "categoria": 0,
            "subcategoria": "",
            "nivel": "",
            "tipo": "",
        }

    if pregunta["tipo"] == "prediccion_output":
        try:
            correcta = int(respuesta) == pregunta["respuesta_correcta"]
        except (ValueError, TypeError):
            correcta = False
    else:
        correcta = (
            _normalizar(respuesta) ==
            _normalizar(str(pregunta["respuesta_correcta"]))
        )

    return {
        "correcta":     correcta,
        "explicacion":  pregunta.get("explicacion", ""),
        "pista":        pregunta.get("pista", "") if not correcta else "",
        "categoria":    pregunta.get("categoria", 0),
        "subcategoria": pregunta.get("subcategoria", ""),
        "nivel":        pregunta.get("nivel", ""),
        "tipo":         pregunta.get("tipo", ""),
    }


def construir_traza(id_pregunta: str, respuesta: str, tiempo: int) -> tuple[dict, dict]:
    """
    Evalúa la respuesta y construye la Traza y el feedback.
 
    Returns:
        (traza_dict, feedback_dict)
    """
    resultado = evaluar_respuesta(id_pregunta, respuesta)
 
    traza = {
        "id_pregunta":  id_pregunta,
        "correcta":     resultado["correcta"],
        "categoria":    resultado["categoria"],
        "subcategoria": resultado["subcategoria"],
        "nivel":        resultado["nivel"],
        "tipo":         resultado["tipo"],
        "tiempo":       tiempo,
        "timestamp":    datetime.now().isoformat(),
    }
 
    feedback = {
        "correcta":    resultado["correcta"],
        "explicacion": resultado["explicacion"],
        "pista":       resultado["pista"],
        "motivacion":  (
            "¡Bien hecho! Sigue así."
            if resultado["correcta"]
            else "No pasa nada. Lee la pista y vuelve a intentarlo."
        ),
    }
 
    return traza, feedback
 