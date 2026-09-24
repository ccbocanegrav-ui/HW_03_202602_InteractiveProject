"""
Tarea 2 - Fase 3: Radar de procesos.

Recibe resultados de búsqueda híbrida y calcula:

- señales de alerta
- severidad de cada señal
- Radar Score

El motor NO realiza búsqueda.
El motor NO genera embeddings.
El motor NO reconstruye índices.

Entrada:
    resultado de search.py

Salida:
    resultados enriquecidos con:
        - radar_score
        - signals
"""

from typing import Any, Dict, List


# ============================================================
# CONFIGURACIÓN
# ============================================================

# Puntajes por tipo de señal.
SCORE_HIGH_AMOUNT = 15
SCORE_FEW_BIDDERS = 15

# Umbral para considerar una similitud alta.
HIGH_SIMILARITY_THRESHOLD = 0.85

# Número de postores considerado bajo.
FEW_BIDDERS_THRESHOLD = 2


# ============================================================
# UTILIDADES
# ============================================================

def safe_float(value):
    """
    Convierte un valor a float de forma segura.
    """

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def percentile_90(values):
    """
    Calcula aproximadamente el percentil 90.

    Se utiliza únicamente para detectar montos
    relativamente altos dentro del conjunto analizado.

    No requiere numpy.
    """

    if not values:
        return None

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    position = 0.90 * (len(values) - 1)

    lower = int(position)
    upper = min(lower + 1, len(values) - 1)

    fraction = position - lower

    return (
        values[lower]
        + (values[upper] - values[lower]) * fraction
    )


# ============================================================
# UMBRAL DE MONTO
# ============================================================

def calculate_high_amount_threshold(results):
    """
    Calcula el umbral de monto alto del conjunto.

    Se utiliza el percentil 90 de los montos disponibles.
    """

    amounts = []

    for result in results:

        amount = safe_float(
            result.get("monto_pen")
        )

        if amount is not None:
            amounts.append(amount)

    return percentile_90(amounts)


# ============================================================
# SEÑALES
# ============================================================

def check_high_amount(result, threshold):
    """
    Detecta si el proceso tiene un monto relativamente alto
    respecto al conjunto analizado.
    """

    if threshold is None:
        return None

    amount = safe_float(
        result.get("monto_pen")
    )

    if amount is None:
        return None

    if amount >= threshold:

        return {
            "type": "high_amount",
            "severity": "medio",
            "score": SCORE_HIGH_AMOUNT,
            "message": (
                "El monto está dentro del 10% superior "
                "del conjunto de procesos."
            ),
        }

    return None


def check_few_bidders(result):
    """
    Detecta procesos con pocos postores.

    Regla:
        <= 2 postores
    """

    bidders = safe_float(
        result.get("num_postores")
    )

    if bidders is None:
        return None

    if bidders <= FEW_BIDDERS_THRESHOLD:

        return {
            "type": "few_bidders",
            "severity": "medio",
            "score": SCORE_FEW_BIDDERS,
            "message": (
                f"El proceso registra {int(bidders)} "
                "postores en los datos disponibles."
            ),
        }

    return None


def check_high_similarity(result):
    """
    La similitud NO suma puntos al Radar.

    Solo genera una señal informativa para indicar
    que el resultado es semánticamente relevante.
    """

    similarity = safe_float(
        result.get("similarity")
    )

    if similarity is None:
        return None

    if similarity >= HIGH_SIMILARITY_THRESHOLD:

        return {
            "type": "high_similarity",
            "severity": "informativo",
            "score": 0,
            "message": (
                "El proceso presenta alta similitud "
                "con la consulta realizada."
            ),
        }

    return None


# ============================================================
# ANALIZAR PROCESO
# ============================================================

def analyze_process(result, amount_threshold=None):
    """
    Analiza un proceso individual.

    Devuelve el proceso original enriquecido.
    """

    signals: List[Dict[str, Any]] = []

    score = 0

    # --------------------------------------------------------
    # MONTO
    # --------------------------------------------------------

    signal = check_high_amount(
        result,
        amount_threshold,
    )

    if signal is not None:
        signals.append(signal)
        score += signal["score"]

    # --------------------------------------------------------
    # POSTORES
    # --------------------------------------------------------

    signal = check_few_bidders(
        result
    )

    if signal is not None:
        signals.append(signal)
        score += signal["score"]

    # --------------------------------------------------------
    # SIMILITUD
    # --------------------------------------------------------

    signal = check_high_similarity(
        result
    )

    if signal is not None:
        signals.append(signal)

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    enriched = dict(result)

    enriched["radar_score"] = score

    enriched["signals"] = signals

    return enriched


# ============================================================
# ORDENAMIENTO
# ============================================================

def radar_sort_key(result):
    """
    Orden:

    1. Radar Score descendente
    2. similitud descendente
    """

    score = safe_float(
        result.get("radar_score")
    ) or 0

    similarity = safe_float(
        result.get("similarity")
    ) or 0

    return (
        score,
        similarity,
    )


# ============================================================
# RADAR COMPLETO
# ============================================================

def run_radar(results):
    """
    Ejecuta el Radar sobre los resultados de búsqueda.

    Parámetros:
        results:
            lista proveniente de search.py

    Retorna:
        {
            "amount_threshold": ...,
            "results": [...]
        }
    """

    if not results:
        return {
            "amount_threshold": None,
            "results": [],
        }

    # --------------------------------------------------------
    # Umbral de monto
    # --------------------------------------------------------

    amount_threshold = calculate_high_amount_threshold(
        results
    )

    # --------------------------------------------------------
    # Analizar procesos
    # --------------------------------------------------------

    analyzed = []

    for result in results:

        analyzed.append(
            analyze_process(
                result,
                amount_threshold,
            )
        )

    # --------------------------------------------------------
    # Ordenar
    # --------------------------------------------------------

    analyzed.sort(
        key=radar_sort_key,
        reverse=True,
    )

    # --------------------------------------------------------
    # Reasignar ranking
    # --------------------------------------------------------

    for index, result in enumerate(
        analyzed,
        start=1,
    ):
        result["rank"] = index

    return {
        "amount_threshold": amount_threshold,
        "results": analyzed,
    }
