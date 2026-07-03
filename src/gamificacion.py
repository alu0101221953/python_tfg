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


# Puntos base por nivel de dificultad
PUNTOS_POR_NIVEL = {"basico": 10, "intermedio": 15, "avanzado": 20}

# Umbral de tiempo rápido por nivel (segundos)
UMBRAL_RAPIDO = {"basico": 10, "intermedio": 15, "avanzado": 20}

# Umbral de dominio para considerar una categoría difícil
UMBRAL_CATEGORIA_DIFICIL = 0.50


def actualizar_gamificacion(gami: PerfilGamificacion, correcta: bool, pistas_usadas: int = 0, nivel: str = "basico",
    tiempo: int = 0, p_dominio_cat: float = 1.0) -> tuple[PerfilGamificacion, list[str]]:
    """
    Actualiza el perfil de gamificación tras una respuesta.

    Args:
        gami:          estado actual de gamificación
        correcta:      si la respuesta fue correcta
        pistas_usadas: pistas vistas antes de responder (0-3)
        nivel:         nivel de la pregunta (basico/intermedio/avanzado)
        tiempo:        segundos empleados en responder
        p_dominio_cat: dominio BKT estimado de la categoría (0-1)

    Sistema de puntos:
        Base:            básico=10, intermedio=15, avanzado=20
        Bonus velocidad: +2 pts si responde por debajo del umbral rápido del nivel
        Bonus dificultad:+5 pts si la categoría tiene dominio BKT < 0.50
        Bonus racha:     +5 pts cada 3 aciertos, +10 pts cada 5
        Penalización:    -1/-3/-6 pts según pistas usadas
        Desglose:        evento 'desglose:...' para mostrar en el feedback

    Returns:
        (perfil_actualizado, lista_de_eventos)
    """
    eventos = []

    if not correcta:
        gami.racha_actual = 0
        return gami, eventos

    # Puntos base según dificultad
    base = PUNTOS_POR_NIVEL.get(nivel, 10)
    bonus_vel = 0
    bonus_dif = 0
    bonus_racha = 0
    penalizacion  = sum(range(1, pistas_usadas + 1))

    # Bonus velocidad
    umbral_rap = UMBRAL_RAPIDO.get(nivel, 10)
    if tiempo > 0 and tiempo <= umbral_rap:
        bonus_vel = 2
        eventos.append("velocidad:+2")

    # Bonus categoría difícil
    if p_dominio_cat < UMBRAL_CATEGORIA_DIFICIL:
        bonus_dif = 5
        eventos.append("dificultad:+5")

    # Penalización pistas
    if penalizacion > 0:
        eventos.append(f"pistas:-{penalizacion}")

    gami.racha_actual += 1

    # Bonus racha
    if gami.racha_actual % 5 == 0:
        bonus_racha = 10
        eventos.append(f"racha_{gami.racha_actual}")
    elif gami.racha_actual % 3 == 0:
        bonus_racha = 5
        eventos.append(f"racha_{gami.racha_actual}")

    # Total
    puntos_ganados = max(base + bonus_vel + bonus_dif + bonus_racha - penalizacion, 1)
    partes = [f"+{base} ({nivel})"]
    if bonus_vel: partes.append(f"+{bonus_vel} (velocidad)")
    if bonus_dif: partes.append(f"+{bonus_dif} (categoría difícil)")
    if bonus_racha: partes.append(f"+{bonus_racha} (racha)")
    if penalizacion: partes.append(f"-{penalizacion} (pistas)")
    partes.append(f"= +{puntos_ganados} pts")
    eventos.append("desglose:" + " | ".join(partes))

    # Actualizar racha máxima
    if gami.racha_actual > gami.racha_maxima:
        gami.racha_maxima = gami.racha_actual

    # Actualizar puntos y nivel
    nivel_antes = gami.nivel
    gami.puntos += puntos_ganados
    gami.nivel = calcular_nivel(gami.puntos)

    if gami.nivel > nivel_antes:
        eventos.append(f"nivel_{gami.nivel}")

    return gami, eventos


def comprobar_insignias_comportamiento( gami: PerfilGamificacion, racha_sin_pistas: int, racha_rapida: int, racha_dificiles: int ) -> list[str]:
    """
    Comprueba insignias basadas en comportamiento.

    - sin_pistas_5:   5 aciertos consecutivos sin usar ninguna pista
    - velocista_3:    3 respuestas rápidas consecutivas
    - perseverante_3: 3 aciertos consecutivos en categorías difíciles
    """
    nuevas = []

    def desbloquear(nombre):
        if nombre not in gami.insignias:
            gami.insignias.append(nombre)
            nuevas.append(nombre)

    if racha_sin_pistas >= 5: desbloquear('sin_pistas_5')
    if racha_rapida >= 3: desbloquear('velocista_3')
    if racha_dificiles  >= 3: desbloquear('perseverante_3')

    return nuevas