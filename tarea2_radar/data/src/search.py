"""
Tarea 2 - Fase 3: búsqueda híbrida.

Combina:

1. Filtros estructurados:
   - departamento
   - mes
   - monto mínimo
   - monto máximo
   - categoría

2. Búsqueda semántica:
   - embedding de la consulta
   - ordenamiento por similitud

El índice de Chroma ya debe existir.
Este script NO reconstruye el índice.
"""

from pathlib import Path
import re
import sys
from functools import lru_cache

import chromadb
import yaml


# ============================================================
# RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent.parent

INDEX_DIR = BASE_DIR / "data" / "index"

CONFIG_TASK1 = REPO_DIR / "tarea1_rag_normativo" / "config.yaml"
TASK1_SRC = REPO_DIR / "tarea1_rag_normativo" / "src"

sys.path.insert(0, str(TASK1_SRC))

from embeddings import get_embedding_backend


# ============================================================
# CONFIGURACIÓN
# ============================================================

COLLECTION_NAME = "procesos_procurement_local"


# ============================================================
# DEPARTAMENTOS
# ============================================================

DEPARTAMENTOS = {
    "amazonas": "AMAZONAS",
    "ancash": "ANCASH",
    "áncash": "ANCASH",
    "apurimac": "APURIMAC",
    "apurímac": "APURIMAC",
    "arequipa": "AREQUIPA",
    "ayacucho": "AYACUCHO",
    "cajamarca": "CAJAMARCA",
    "callao": "CALLAO",
    "cusco": "CUSCO",
    "cuzco": "CUSCO",
    "huancavelica": "HUANCAVELICA",
    "huanuco": "HUANUCO",
    "huánuco": "HUANUCO",
    "ica": "ICA",
    "junin": "JUNIN",
    "junín": "JUNIN",
    "la libertad": "LA LIBERTAD",
    "lambayeque": "LAMBAYEQUE",
    "lima": "LIMA",
    "loreto": "LORETO",
    "madre de dios": "MADRE DE DIOS",
    "moquegua": "MOQUEGUA",
    "pasco": "PASCO",
    "piura": "PIURA",
    "puno": "PUNO",
    "san martin": "SAN MARTIN",
    "san martín": "SAN MARTIN",
    "tacna": "TACNA",
    "tumbes": "TUMBES",
    "ucayali": "UCAYALI",
}


# ============================================================
# MESES
# ============================================================

MESES = {
    "enero": "01",
    "febrero": "02",
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "setiembre": "09",
    "octubre": "10",
    "noviembre": "11",
    "diciembre": "12",
}


# ============================================================
# CONFIG TAREA 1
# ============================================================

def load_task1_config():

    if not CONFIG_TASK1.exists():
        raise FileNotFoundError(
            f"No se encontró:\n{CONFIG_TASK1}"
        )

    with open(CONFIG_TASK1, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# EMBEDDINGS
# ============================================================

@lru_cache(maxsize=1)
def get_backend():

    config = load_task1_config()

    print("\nCargando modelo de embeddings...")

    backend = get_embedding_backend(
        config,
        which="local",
    )

    print(f"Modelo: {backend.name}")
    print(f"Dimensión: {backend.dimension}")

    return backend


# ============================================================
# UTILIDADES
# ============================================================

def normalize_text(value):

    if value is None:
        return ""

    return str(value).strip()


def parse_money(value):

    """
    Convierte expresiones como:

        500000
        500,000
        500 mil
        1 millón
        1.5 millones
        1 millón de soles

    a soles.
    """

    if value is None:
        return None

    text = str(value).lower().strip()

    text = text.replace("s/", "")
    text = text.replace("soles", "")
    text = text.replace("sol", "")
    text = text.strip()

    # --------------------------------------------------------
    # MILLONES
    # --------------------------------------------------------

    match = re.search(
        r"([\d]+(?:[.,]\d+)?)\s*mill[oó]n(?:es)?",
        text,
    )

    if match:

        number = match.group(1)

        # 1.5 -> 1.5
        # 1,5 -> 1.5
        if "," in number and "." not in number:
            number = number.replace(",", ".")
        else:
            number = number.replace(",", "")

        try:
            return float(number) * 1_000_000
        except ValueError:
            return None

    # --------------------------------------------------------
    # MILES
    # --------------------------------------------------------

    match = re.search(
        r"([\d]+(?:[.,]\d+)?)\s*mil",
        text,
    )

    if match:

        number = match.group(1)

        if "," in number and "." not in number:
            number = number.replace(",", ".")
        else:
            number = number.replace(",", "")

        try:
            return float(number) * 1_000
        except ValueError:
            return None

    # --------------------------------------------------------
    # NÚMERO NORMAL
    # --------------------------------------------------------

    match = re.search(
        r"[\d]+(?:[.,]\d+)*",
        text,
    )

    if not match:
        return None

    number = match.group(0)

    if "," in number:
        number = number.replace(",", "")

    try:
        return float(number)

    except ValueError:
        return None


# ============================================================
# DETECCIÓN DE DEPARTAMENTO
# ============================================================

def detect_department(query):

    q = query.lower()

    for name in sorted(
        DEPARTAMENTOS,
        key=len,
        reverse=True,
    ):

        if re.search(
            rf"\b{re.escape(name)}\b",
            q,
        ):
            return DEPARTAMENTOS[name]

    return None


# ============================================================
# DETECCIÓN DE MES
# ============================================================

def detect_month(query):

    q = query.lower()

    for month, number in MESES.items():

        if re.search(
            rf"\b{month}\b",
            q,
        ):
            return number

    return None


# ============================================================
# DETECCIÓN DE MONTO
# ============================================================

def detect_amount_filters(query):

    q = query.lower()

    min_amount = None
    max_amount = None

    # --------------------------------------------------------
    # MÍNIMO
    # --------------------------------------------------------

    patterns_min = [
        r"más de\s+(.+?)(?=\s+(?:en|durante|para|de)\b|$)",
        r"mayor(?:es)? a\s+(.+?)(?=\s+(?:en|durante|para|de)\b|$)",
        r"superior a\s+(.+?)(?=\s+(?:en|durante|para|de)\b|$)",
        r"por encima de\s+(.+?)(?=\s+(?:en|durante|para|de)\b|$)",
        r"desde\s+(.+?)(?=\s+(?:en|durante|para|de)\b|$)",
    ]

    for pattern in patterns_min:

        match = re.search(
            pattern,
            q,
        )

        if match:

            amount = parse_money(
                match.group(1)
            )

            if amount is not None:
                min_amount = amount
                break

    # --------------------------------------------------------
    # MÁXIMO
    # --------------------------------------------------------

    patterns_max = [
        r"menos de\s+(.+?)(?=\s+(?:en|durante|para|de)\b|$)",
        r"menor(?:es)? a\s+(.+?)(?=\s+(?:en|durante|para|de)\b|$)",
        r"inferior a\s+(.+?)(?=\s+(?:en|durante|para|de)\b|$)",
        r"hasta\s+(.+?)(?=\s+(?:en|durante|para|de)\b|$)",
    ]

    for pattern in patterns_max:

        match = re.search(
            pattern,
            q,
        )

        if match:

            amount = parse_money(
                match.group(1)
            )

            if amount is not None:
                max_amount = amount
                break

    return min_amount, max_amount


# ============================================================
# DETECCIÓN DE CATEGORÍA
# ============================================================

def detect_category(query):

    q = query.lower()

    if any(
        word in q
        for word in [
            "servicio",
            "servicios",
            "limpieza",
            "consultoría",
            "consultoria",
            "mantenimiento",
        ]
    ):
        return "services"

    if any(
        word in q
        for word in [
            "compra",
            "compras",
            "adquisición",
            "adquisicion",
            "medicamentos",
            "equipos",
            "materiales",
            "bienes",
        ]
    ):
        return "goods"

    if any(
        word in q
        for word in [
            "obra",
            "obras",
            "construcción",
            "construccion",
        ]
    ):
        return "works"

    return None


# ============================================================
# DETECTAR TODOS LOS FILTROS
# ============================================================

def detect_filters(query):

    min_amount, max_amount = detect_amount_filters(query)

    return {
        "departamento": detect_department(query),
        "mes_origen": detect_month(query),
        "monto_min": min_amount,
        "monto_max": max_amount,
        "categoria": detect_category(query),
    }


# ============================================================
# FILTRO CHROMA
# ============================================================

def build_chroma_filter(filters):

    conditions = []

    if filters["departamento"]:

        conditions.append({
            "departamento": filters["departamento"]
        })

    if filters["mes_origen"]:

        conditions.append({
            "mes_origen": (
                f"2026-{filters['mes_origen']}"
            )
        })

    if filters["categoria"]:

        conditions.append({
            "categoria": filters["categoria"]
        })

    if filters["monto_min"] is not None:

        conditions.append({
            "monto_pen": {
                "$gte": filters["monto_min"]
            }
        })

    if filters["monto_max"] is not None:

        conditions.append({
            "monto_pen": {
                "$lte": filters["monto_max"]
            }
        })

    if not conditions:
        return None

    if len(conditions) == 1:
        return conditions[0]

    return {
        "$and": conditions
    }


# ============================================================
# LIMPIEZA DE CONSULTA SEMÁNTICA
# ============================================================

def semantic_query(query, filters):

    text = query.lower()

    # --------------------------------------------------------
    # 1. Quitar departamentos
    # --------------------------------------------------------

    for name in sorted(
        DEPARTAMENTOS,
        key=len,
        reverse=True,
    ):

        text = re.sub(
            rf"\b{re.escape(name)}\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )

    # --------------------------------------------------------
    # 2. Quitar meses
    # --------------------------------------------------------

    for month in MESES:

        text = re.sub(
            rf"\b{re.escape(month)}\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )

    # --------------------------------------------------------
    # 3. Quitar expresiones monetarias completas
    #
    # Ejemplos:
    #
    # más de 1 millón de soles
    # más de 500 mil soles
    # menos de 2 millones
    # mayor a 500000
    # --------------------------------------------------------

    money_patterns = [

        r"(?:más de|mayor(?:es)? a|superior a|"
        r"por encima de|desde)"
        r"\s+[\d.,]+\s*(?:mill[oó]n(?:es)?|mil)?"
        r"(?:\s+de)?\s*(?:soles|s/)?",

        r"(?:menos de|menor(?:es)? a|inferior a|hasta)"
        r"\s+[\d.,]+\s*(?:mill[oó]n(?:es)?|mil)?"
        r"(?:\s+de)?\s*(?:soles|s/)?",
    ]

    for pattern in money_patterns:

        text = re.sub(
            pattern,
            " ",
            text,
            flags=re.IGNORECASE,
        )

    # --------------------------------------------------------
    # 4. Quitar palabras que solamente sirven para filtros
    # --------------------------------------------------------

    filter_words = [
        "en",
        "durante",
        "del",
        "desde",
        "por",
    ]

    for word in filter_words:

        text = re.sub(
            rf"\b{word}\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )

    # --------------------------------------------------------
    # 5. Limpiar espacios
    # --------------------------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    # --------------------------------------------------------
    # Evitar consulta vacía
    # --------------------------------------------------------

    if not text:
        text = query.strip()

    return text


# ============================================================
# BÚSQUEDA
# ============================================================

def search(
    query,
    top_k=5,
):

    backend = get_backend()

    # --------------------------------------------------------
    # Chroma
    # --------------------------------------------------------

    client = chromadb.PersistentClient(
        path=str(INDEX_DIR)
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    # --------------------------------------------------------
    # Filtros
    # --------------------------------------------------------

    filters = detect_filters(query)

    chroma_filter = build_chroma_filter(
        filters
    )

    semantic_text = semantic_query(
        query,
        filters,
    )

    # --------------------------------------------------------
    # Embedding
    # --------------------------------------------------------

    query_embedding = backend.encode_queries(
        [semantic_text]
    )[0]

    query_embedding = list(
        map(float, query_embedding)
    )

    # --------------------------------------------------------
    # Query Chroma
    # --------------------------------------------------------

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
    }

    if chroma_filter is not None:
        kwargs["where"] = chroma_filter

    results = collection.query(
        **kwargs
    )

    # --------------------------------------------------------
    # Resultados
    # --------------------------------------------------------

    output = []

    if not results["ids"]:
        return {
            "query": query,
            "semantic_query": semantic_text,
            "filters": filters,
            "results": [],
        }

    for i in range(
        len(results["ids"][0])
    ):

        metadata = results["metadatas"][0][i]

        distance = results["distances"][0][i]

        similarity = 1 - distance

        output.append({

            "rank": i + 1,

            "similarity": round(
                similarity,
                4,
            ),

            "ocid": metadata.get(
                "ocid",
                "",
            ),

            "departamento": metadata.get(
                "departamento",
                "",
            ),

            "categoria": metadata.get(
                "categoria",
                "",
            ),

            "comprador": metadata.get(
                "comprador",
                "",
            ),

            "procedimiento": metadata.get(
                "procedimiento",
                "",
            ),

            "fecha_publicacion": metadata.get(
                "fecha_publicacion",
                "",
            ),

            "mes_origen": metadata.get(
                "mes_origen",
                "",
            ),

            "monto_pen": metadata.get(
                "monto_pen",
                None,
            ),

            "num_postores": metadata.get(
                "num_postores",
                None,
            ),

            "texto": results["documents"][0][i],
        })

    return {
        "query": query,
        "semantic_query": semantic_text,
        "filters": filters,
        "results": output,
    }


# ============================================================
# FORMATEO
# ============================================================

def print_results(response):

    print()
    print("=" * 70)
    print("BÚSQUEDA HÍBRIDA")
    print("=" * 70)

    print()
    print("Consulta:")
    print(response["query"])

    print()
    print("Texto utilizado para búsqueda semántica:")
    print(response["semantic_query"])

    print()
    print("Filtros detectados:")

    filters = response["filters"]

    print(
        f"  Departamento: "
        f"{filters['departamento'] or 'ninguno'}"
    )

    print(
        f"  Mes: "
        f"{filters['mes_origen'] or 'todos'}"
    )

    print(
        f"  Categoría: "
        f"{filters['categoria'] or 'todas'}"
    )

    if filters["monto_min"] is not None:

        print(
            f"  Monto mínimo: "
            f"S/ {filters['monto_min']:,.2f}"
        )

    else:

        print(
            "  Monto mínimo: ninguno"
        )

    if filters["monto_max"] is not None:

        print(
            f"  Monto máximo: "
            f"S/ {filters['monto_max']:,.2f}"
        )

    else:

        print(
            "  Monto máximo: ninguno"
        )

    print()
    print(
        f"Resultados: "
        f"{len(response['results'])}"
    )

    print()
    print("-" * 70)

    for result in response["results"]:

        print(
            f"\n#{result['rank']} | "
            f"similitud={result['similarity']:.4f}"
        )

        print(
            f"OCID: {result['ocid']}"
        )

        print(
            f"Departamento: "
            f"{result['departamento']}"
        )

        print(
            f"Categoría: "
            f"{result['categoria']}"
        )

        print(
            f"Comprador: "
            f"{result['comprador']}"
        )

        monto = result["monto_pen"]

        if monto is not None:

            print(
                f"Monto PEN: "
                f"S/ {float(monto):,.2f}"
            )

        else:

            print(
                "Monto PEN: No disponible"
            )

        print(
            f"Fecha publicación: "
            f"{result['fecha_publicacion']}"
        )

        print(
            f"Procedimiento: "
            f"{result['procedimiento']}"
        )

        print(
            f"Postores: "
            f"{result['num_postores']}"
        )

        print(
            f"Texto: "
            f"{result['texto'][:700]}"
        )


# ============================================================
# PRUEBAS
# ============================================================

def main():

    queries = [
        "compra de medicamentos en Cusco",
        "servicios de limpieza en Lima por más de 1 millón de soles",
        "adquisición de equipos informáticos en Arequipa durante marzo",
        "procesos de construcción en enero",
    ]

    for query in queries:

        response = search(
            query,
            top_k=5,
        )

        print_results(response)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    main()
