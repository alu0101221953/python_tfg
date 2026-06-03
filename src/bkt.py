"""
Bayesian Knowledge Tracing (BKT) — PyTutor
Basado en: González et al. (2010) - Error detection and personalized learning

El BKT estima la probabilidad de que un alumno domine una categoría
a partir de su historial de respuestas correctas e incorrectas.

Parámetros del modelo:
  P(L0) — probabilidad inicial de conocimiento (prior)
  P(T)  — probabilidad de aprender en cada intento (transit)
  P(G)  — probabilidad de acertar sin saber (guess)
  P(S)  — probabilidad de fallar sabiendo (slip)
"""

P_L0 = 0.10  # conocimiento inicial
P_T  = 0.10  # probabilidad de transición
P_G  = 0.25  # probabilidad de acierto por azar
P_S  = 0.20  # probabilidad de error al saber

UMBRAL_DOMINIO = 0.90


def actualizar_dominio(p_dominio: float, correcta: bool) -> float:
    """
    Actualiza la estimación de dominio tras una respuesta.

    Aplica el filtro de Bayes:
      1. Calcular P(correcta | conoce) y P(correcta | no conoce)
      2. Actualizar la probabilidad de conocimiento (posterior)
      3. Aplicar la probabilidad de transición (aprendizaje)

    Args:
        p_dominio: probabilidad actual de dominio [0, 1]
        correcta:  si la respuesta fue correcta o no

    Returns:
        Nueva probabilidad de dominio [0, 1]
    """
    if correcta:
        p_correcto_conoce = 1 - P_S
        p_correcto_no_conoce = P_G
    else:
        p_correcto_conoce = P_S
        p_correcto_no_conoce = 1 - P_G

    # Posterior: P(conoce | respuesta)
    numerador = p_correcto_conoce * p_dominio
    denominador = numerador + p_correcto_no_conoce * (1 - p_dominio)

    if denominador == 0:
        p_posterior = p_dominio
    else:
        p_posterior = numerador / denominador

    # Transición: puede haber aprendido en este intento
    p_nuevo = p_posterior + (1 - p_posterior) * P_T

    return round(p_nuevo, 4)


def calcular_bkt_alumno(trazas: list) -> dict:
    """
    Calcula el estado BKT actual del alumno por categoría.

    Args:
        trazas: lista de objetos Traza del alumno

    Returns:
        Dict con el estado BKT por categoría:
        {
            1: {
                "p_dominio":    0.85,
                "dominado":     True,
                "num_intentos": 5,
                "nombre":       "Sintaxis"
            },
            ...
        }
    """
    from src.modelos import CATEGORIAS

    # Inicializar estado por categoría
    estado = {}

    for traza in trazas:
        cat = traza.categoria if hasattr(traza, 'categoria') else traza['categoria']
        correcta = traza.correcta if hasattr(traza, 'correcta') else traza['correcta']

        if cat not in estado:
            estado[cat] = {
                "p_dominio": P_L0,
                "dominado": False,
                "num_intentos": 0,
                "nombre": CATEGORIAS.get(cat, f"Cat {cat}"),
            }

        estado[cat]["p_dominio"] = actualizar_dominio(estado[cat]["p_dominio"], correcta)
        estado[cat]["num_intentos"] += 1
        estado[cat]["dominado"] = estado[cat]["p_dominio"] >= UMBRAL_DOMINIO

    return estado


def resumen_bkt(bkt: dict) -> dict:
    """
    Clasifica las categorías por estado de dominio.

    Returns:
        {
            "dominadas":   [1, 3],      # p >= 0.80
            "en_progreso": [2, 4],      # 0.50 <= p < 0.80
            "dificultad":  [5],         # p < 0.50 con intentos
            "sin_datos":   [6, 7, 8],   # sin intentos aún
        }
    """
    from src.modelos import CATEGORIAS

    todas = set(CATEGORIAS.keys())
    con_datos = set(bkt.keys())
    sin_datos = sorted(todas - con_datos)

    dominadas = sorted([c for c, v in bkt.items() if v["dominado"]])
    en_progreso = sorted([c for c, v in bkt.items() if 0.50 <= v["p_dominio"] < UMBRAL_DOMINIO])
    dificultad = sorted([c for c, v in bkt.items() if v["p_dominio"] < 0.50])

    return {
        "dominadas": dominadas,
        "en_progreso": en_progreso,
        "dificultad": dificultad,
        "sin_datos": sin_datos,
    }