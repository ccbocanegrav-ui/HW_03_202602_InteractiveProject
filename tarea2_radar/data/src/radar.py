from pathlib import Path
import sys

# ============================================================
# RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(BASE_DIR))

from search import search
from radar_engine import run_radar


# ============================================================
# FORMATEO
# ============================================================

def print_radar(response, radar_response):

    print()
    print("=" * 75)
    print("RADAR DE PROCESOS")
    print("=" * 75)

    print()
    print("Consulta:")
    print(response["query"])

    print()
    print("Consulta semántica:")
    print(response["semantic_query"])

    print()
    print("Filtros:")

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
        print("  Monto mínimo: ninguno")

    if filters["monto_max"] is not None:
        print(
            f"  Monto máximo: "
            f"S/ {filters['monto_max']:,.2f}"
        )
    else:
        print("  Monto máximo: ninguno")

    results = radar_response["results"]

    print()
    print(
        f"Procesos analizados: "
        f"{len(results)}"
    )

    threshold = radar_response[
        "amount_threshold"
    ]

    if threshold is not None:
        print(
            f"Umbral de monto alto: "
            f"S/ {threshold:,.2f}"
        )

    print()
    print("-" * 75)

    for result in results:

        print()

        print(
            f"#{result['rank']} | "
            f"Radar={result['radar_score']}"
        )

        print(
            f"OCID: "
            f"{result['ocid']}"
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

        monto = result.get("monto_pen")

        if monto is not None:
            print(
                f"Monto: "
                f"S/ {float(monto):,.2f}"
            )
        else:
            print(
                "Monto: No disponible"
            )

        postores = result.get(
            "num_postores"
        )

        if postores is not None:
            print(
                f"Postores: "
                f"{postores}"
            )
        else:
            print(
                "Postores: No disponible"
            )

        similarity = result.get(
            "similarity"
        )

        if similarity is not None:
            print(
                f"Similitud: "
                f"{similarity:.4f}"
            )

        signals = result.get(
            "signals",
            []
        )

        print()

        if not signals:
            print(
                "Señales: ninguna"
            )
        else:
            print(
                "Señales:"
            )

            for signal in signals:

                print(
                    f"  - "
                    f"[{signal['severity']}] "
                    f"{signal['message']}"
                )

        print("-" * 75)


# ============================================================
# EJECUCIÓN
# ============================================================

def run_query(query):

    response = search(
        query,
        top_k=5,
    )

    radar_response = run_radar(
        response["results"]
    )

    print_radar(
        response,
        radar_response,
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
        run_query(query)


if __name__ == "__main__":
    main()
