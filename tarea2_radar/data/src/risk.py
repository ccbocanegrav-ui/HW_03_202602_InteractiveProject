"""
risk.py — Task 2, Phase 5: Single-Bidder Awards (indicador de riesgo)

Entre los procesos ADJUDICADOS, calcula el % que recibio exactamente
UNA oferta, por entidad compradora (buyer). Un red flag es motivo para
mirar mas de cerca, NO evidencia de irregularidad (ver referencias del
enunciado: Open Contracting Partnership, Ojo Publico).

Requiere una columna con el NUMERO DE POSTORES/OFERTAS por proceso.
AJUSTAR N_BIDDERS_COL si el nombre real de esa columna en tu CSV es
distinto (correr load_data.py para ver las columnas disponibles).

Uso:
    python src/risk.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"
OUTPUTS_DIR = BASE_DIR / "data" / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Confirmado en el archivo "Registros" del export de OECE.
N_BIDDERS_COL = "n_bidders"  # ya renombrado por COLUMN_MAP de validate.py — ver ahi el nombre original

MIN_PROCESOS_POR_BUYER = 5  # umbral minimo de procesos para incluir un buyer en el ranking (evita ruido de muestras chicas)


def load_clean() -> pd.DataFrame:
    path = PROCESSED_DIR / "oece_clean.csv"
    if not path.exists():
        print(f"No existe {path}. Corre src/validate.py primero.")
        sys.exit(1)
    return pd.read_csv(path, low_memory=False)


def compute_risk(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if N_BIDDERS_COL not in df.columns:
        print(f"\n⚠️  ADVERTENCIA: no existe la columna '{N_BIDDERS_COL}' en oece_clean.csv.")
        print(f"Columnas disponibles: {list(df.columns)}")
        print(f"Ajusta N_BIDDERS_COL en src/risk.py con el nombre correcto.\n")
        sys.exit(1)

    df = df.copy()
    df["is_single_bidder"] = df[N_BIDDERS_COL] == 1

    by_buyer = df.groupby("buyer").agg(
        n_procesos=("ocid", "count"),
        n_single_bidder=("is_single_bidder", "sum"),
    )
    by_buyer["pct_single_bidder"] = (100 * by_buyer["n_single_bidder"] / by_buyer["n_procesos"]).round(1)

    by_buyer_filtered = by_buyer[by_buyer["n_procesos"] >= MIN_PROCESOS_POR_BUYER]
    top10 = by_buyer_filtered.sort_values("pct_single_bidder", ascending=False).head(10)

    by_department = df.groupby("department_normalizado").agg(
        n_procesos=("ocid", "count"),
        n_single_bidder=("is_single_bidder", "sum"),
    )
    by_department["pct_single_bidder"] = (100 * by_department["n_single_bidder"] / by_department["n_procesos"]).round(1)

    summary = {
        "min_procesos_por_buyer_para_ranking": MIN_PROCESOS_POR_BUYER,
        "pct_single_bidder_global": round(100 * df["is_single_bidder"].sum() / len(df), 1) if len(df) else 0,
        "n_buyers_en_ranking": len(by_buyer_filtered),
    }

    return top10.reset_index(), summary, by_department.reset_index()


def main():
    df = load_clean()
    top10, summary, by_department = compute_risk(df)

    print("=== INDICADOR DE RIESGO — Single-Bidder Awards ===\n")
    print(f"% single-bidder global: {summary['pct_single_bidder_global']}%")
    print(f"Buyers en el ranking (>= {summary['min_procesos_por_buyer_para_ranking']} procesos): "
          f"{summary['n_buyers_en_ranking']}\n")
    print("Top 10 buyers por % single-bidder:")
    print(top10.to_string(index=False))

    top10.to_csv(OUTPUTS_DIR / "risk_top_buyers.csv", index=False)
    by_department.to_csv(OUTPUTS_DIR / "risk_by_department.csv", index=False)
    with open(LOGS_DIR / "risk_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado: {OUTPUTS_DIR / 'risk_top_buyers.csv'}")
    print(f"Guardado: {OUTPUTS_DIR / 'risk_by_department.csv'}")


if __name__ == "__main__":
    main()
