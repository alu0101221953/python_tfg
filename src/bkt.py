"""
Bayesian Knowledge Tracing (BKT)
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

UMBRALES_TIEMPO = {
    "basico": {"rapido": 10, "lento": 30},
    "intermedio": {"rapido": 15, "lento": 45},
    "avanzado": {"rapido": 20, "lento": 60},
}
P_S_MAX_LENTO = 0.45


def _p_s_efectivo(tiempo: int | None, nivel: str | None) -> float:
    """
    Calcula la probabilidad de slip efectiva en función del tiempo de
    respuesta y el nivel de la pregunta.

    Una respuesta correcta pero lenta es tratada con más escepticismo:
    el modelo sube P(S) de forma progresiva entre los umbrales "rapido"
    y "lento" definidos para ese nivel, alcanzando P_S_MAX_LENTO cuando
    el tiempo iguala o supera el umbral lento.

    Si no se dispone de tiempo o nivel (p. ej. trazas antiguas), se
    devuelve el P(S) base sin modificar.
    """
    if tiempo is None or not nivel or nivel not in UMBRALES_TIEMPO:
        return P_S

    umbral = UMBRALES_TIEMPO[nivel]
    rapido, lento = umbral["rapido"], umbral["lento"]

    if tiempo <= rapido:
        return P_S
    if tiempo >= lento:
        return P_S_MAX_LENTO

    frac = (tiempo - rapido) / (lento - rapido)
    return P_S + frac * (P_S_MAX_LENTO - P_S)


def actualizar_dominio(p_dominio: float, correcta: bool, tiempo: int | None = None, nivel: str | None = None) -> float:
    """
    Actualiza la estimación de dominio tras una respuesta.

    Aplica el filtro de Bayes:
      1. Calcular P(correcta | conoce) y P(correcta | no conoce)
      2. Actualizar la probabilidad de conocimiento (posterior)
      3. Aplicar la probabilidad de transición (aprendizaje)

    Si la respuesta es correcta pero lenta, se usa un P(S) efectivo más
    alto (ver _p_s_efectivo): un acierto lento aporta menos confianza en
    el dominio real que un acierto rápido.

    Args:
        p_dominio: probabilidad actual de dominio [0, 1]
        correcta:  si la respuesta fue correcta o no
        tiempo:    segundos empleados en responder (opcional)
        nivel:     nivel de dificultad de la pregunta (opcional)

    Returns:
        Nueva probabilidad de dominio [0, 1]
    """
    p_s = _p_s_efectivo(tiempo, nivel) if correcta else P_S

    if correcta:
        p_correcto_conoce = 1 - p_s
        p_correcto_no_conoce = P_G
    else:
        p_correcto_conoce = p_s
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
        correcta = traza.correcta  if hasattr(traza, 'correcta')  else traza['correcta']
        tiempo = traza.tiempo    if hasattr(traza, 'tiempo')    else traza.get('tiempo')
        nivel = traza.nivel     if hasattr(traza, 'nivel')     else traza.get('nivel')

        if cat not in estado:
            estado[cat] = {
                "p_dominio": P_L0,
                "dominado": False,
                "num_intentos": 0,
                "nombre": CATEGORIAS.get(cat, f"Cat {cat}"),
            }

        estado[cat]["p_dominio"] = actualizar_dominio(estado[cat]["p_dominio"], correcta, tiempo, nivel)
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