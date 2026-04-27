"""
Motor de gamificación.

Implementa puntos, niveles y rachas de aciertos para motivar
al alumno durante el aprendizaje.

Sistema de puntos:
  - 10 puntos base por respuesta correcta
  - +5 puntos bonus por racha de 3 aciertos consecutivos
  - +10 puntos bonus por racha de 5 aciertos consecutivos

Sistema de niveles:
  - Cada nivel requiere nivel * 100 puntos
  - Nivel 1: 100 pts, Nivel 2: 200 pts, Nivel 3: 300 pts...
"""

from pydantic import BaseModel, Field


class PerfilGamificacion(BaseModel):
    """Estado de gamificación de un alumno."""
    puntos: int = 0
    nivel: int = 1
    racha_actual: int = 0
    racha_maxima: int = 0


def calcular_nivel(puntos: int) -> int:
    """Calcula el nivel según los puntos acumulados."""
    nivel = 1
    while puntos >= nivel * 100:
        puntos -= nivel * 100
        nivel  += 1
    return nivel


def puntos_siguiente_nivel(puntos: int, nivel: int) -> int:
    """Devuelve los puntos que faltan para el siguiente nivel."""
    acumulado = sum(n * 100 for n in range(1, nivel))
    return nivel * 100 - (puntos - acumulado)


def actualizar_gamificacion(gami: PerfilGamificacion, correcta: bool) -> tuple[PerfilGamificacion, list[str]]:
    """
    Actualiza el perfil de gamificación tras una respuesta.

    Args:
        gami:     estado actual de gamificación
        correcta: si la respuesta fue correcta

    Returns:
        (perfil_actualizado, lista_de_eventos)
        Eventos posibles: 'puntos', 'racha_3', 'racha_5', 'subida_nivel'
    """
    eventos = []

    if not correcta:
        gami.racha_actual = 0
        return gami, eventos

    # Puntos base
    puntos_ganados = 10
    gami.racha_actual += 1

    # Bonus por racha
    if gami.racha_actual % 5 == 0:
        puntos_ganados += 10
        eventos.append(f"racha_{gami.racha_actual}")
    elif gami.racha_actual % 3 == 0:
        puntos_ganados += 5
        eventos.append(f"racha_{gami.racha_actual}")

    # Actualizar racha máxima
    if gami.racha_actual > gami.racha_maxima:
        gami.racha_maxima = gami.racha_actual

    # Actualizar puntos y nivel
    nivel_antes = gami.nivel
    gami.puntos += puntos_ganados
    gami.nivel = calcular_nivel(gami.puntos)

    eventos.append(f"+{puntos_ganados} puntos")

    if gami.nivel > nivel_antes:
        eventos.append(f"nivel_{gami.nivel}")

    return gami, eventos