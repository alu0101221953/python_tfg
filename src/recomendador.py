"""
Planificador instruccional de PyTutor.

Selecciona la siguiente pregunta según el estado BKT del alumno,
priorizando las categorías con menor dominio estimado.

Estrategia de selección:
  1. Categorías con dificultad (p < 0.50) — refuerzo urgente
  2. Categorías en progreso (0.50 <= p < 0.80) — consolidación
  3. Categorías sin datos — exploración de nuevas áreas
  4. Categorías dominadas — repaso ocasional
  5. Último recurso — cualquier pregunta no vista
"""

import json
import random
from pathlib import Path

from src.bkt import calcular_bkt_alumno, resumen_bkt, P_L0

_BANCO_PATH  = Path(__file__).parent.parent / "data" / "banco_preguntas.json"
_banco_cache: list[dict] | None = None


def cargar_banco() -> list[dict]:
    """Carga el banco de preguntas con caché en memoria."""
    global _banco_cache
    if _banco_cache is None:
        with open(_BANCO_PATH, encoding="utf-8") as f:
            _banco_cache = json.load(f)["preguntas"]
    return _banco_cache


def _nivel_por_dominio(p_dominio: float) -> str:
    """Determina el nivel de dificultad apropiado según el dominio estimado."""
    if p_dominio >= 0.80:
        return "avanzado"
    if p_dominio >= 0.50:
        return "intermedio"
    return "basico"


def _candidatas(cat: int, nivel: str, vistas: set) -> list[dict]:
    """Devuelve preguntas disponibles para una categoría y nivel."""
    banco = cargar_banco()
    return [
        p for p in banco
        if p["categoria"] == cat
        and p["nivel"]     == nivel
        and p["id"]        not in vistas
    ]


def seleccionar_siguiente_pregunta(alumno) -> dict | None:
    """
    Selecciona la siguiente pregunta para el alumno usando el BKT.

    Args:
        alumno: objeto Alumno con sus trazas

    Returns:
        Dict con los datos de la pregunta, o None si no hay disponibles
    """
    banco  = cargar_banco()
    vistas = alumno.preguntas_vistas()
    bkt    = calcular_bkt_alumno(alumno.trazas)
    resumen = resumen_bkt(bkt)

    # Orden de prioridad de categorías
    orden = (
        resumen["dificultad"]   +   # 1. refuerzo urgente
        resumen["en_progreso"]  +   # 2. consolidación
        resumen["sin_datos"]    +   # 3. exploración
        resumen["dominadas"]        # 4. repaso
    )

    for cat in orden:
        p_dominio = bkt.get(cat, {}).get("p_dominio", P_L0)
        nivel     = _nivel_por_dominio(p_dominio)

        # Intentar con el nivel apropiado
        candidatas = _candidatas(cat, nivel, vistas)

        # Si no hay, probar con cualquier nivel de esa categoría
        if not candidatas:
            candidatas = [
                p for p in banco
                if p["categoria"] == cat and p["id"] not in vistas
            ]

        if candidatas:
            return random.choice(candidatas)

    # Último recurso: cualquier pregunta no vista
    disponibles = [p for p in banco if p["id"] not in vistas]
    return random.choice(disponibles) if disponibles else None