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
    insignias: list[str] = []


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


def comprobar_insignias(gami: PerfilGamificacion, total_correctas: int, categorias_dominadas: list[int]) -> list[str]:
    """
    Comprueba si el alumno ha desbloqueado nuevas insignias.

    Insignias disponibles:
      - primer_acierto — primera respuesta correcta
      - racha_3/5/10 — rachas de aciertos consecutivos
      - nivel_2/5/10 — alcanzar niveles
      - 10/25/50_correctas — hitos de respuestas correctas
      - domina_cat_N — dominar una categoría (N = 1..8)
    """
    nuevas = []

    def desbloquear(nombre):
        if nombre not in gami.insignias:
            gami.insignias.append(nombre)
            nuevas.append(nombre)

    if total_correctas >= 1: desbloquear('primer_acierto')
    if total_correctas >= 10: desbloquear('10_correctas')
    if total_correctas >= 25: desbloquear('25_correctas')
    if total_correctas >= 50: desbloquear('50_correctas')

    if gami.racha_maxima >= 3: desbloquear('racha_3')
    if gami.racha_maxima >= 5: desbloquear('racha_5')
    if gami.racha_maxima >= 10: desbloquear('racha_10')

    if gami.nivel >= 2: desbloquear('nivel_2')
    if gami.nivel >= 5: desbloquear('nivel_5')
    if gami.nivel >= 10: desbloquear('nivel_10')

    for cat in categorias_dominadas:
        desbloquear(f'domina_cat_{cat}')

    return nuevas


def actualizar_gamificacion(gami: PerfilGamificacion, correcta: bool, pistas_usadas: int = 0) -> tuple[PerfilGamificacion, list[str]]:
    """
    Actualiza el perfil de gamificación tras una respuesta.

    Args:
        gami:          estado actual de gamificación
        correcta:      si la respuesta fue correcta
        pistas_usadas: número de pistas vistas antes de responder (0-3)

    Sistema de penalización por pistas:
        1 pista  → -1 punto
        2 pistas → -1 -2 = -3 puntos
        3 pistas → -1 -2 -3 = -6 puntos

    Returns:
        (perfil_actualizado, lista_de_eventos)
        Eventos posibles: '+N puntos', 'pistas:-N', 'racha_3', 'racha_5', 'nivel_N'
    """
    eventos = []

    if not correcta:
        gami.racha_actual = 0
        return gami, eventos

    # Puntos base con penalización progresiva por pistas
    penalizacion = sum(range(1, pistas_usadas + 1))  # 0, 1, 3, 6
    puntos_ganados = max(10 - penalizacion, 1)

    if penalizacion > 0:
        eventos.append(f"pistas:-{penalizacion}")

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