"""
validate.py — Task 2, Phase 2: Validation and Territorial Normalization

IMPORTANTE: ajusta COLUMN_MAP a los nombres REALES de columnas de tu
CSV de OECE (correlos con: python src/load_data.py, que imprime las
columnas detectadas). Toda la logica de aqui en adelante usa los
nombres CANONICOS (columna derecha), asi que solo hay que tocar este
diccionario si el archivo real usa nombres distintos.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Nombres reales confirmados en el archivo "Registros" del export de OECE.
COLUMN_MAP = {
    "ocid": "Open Contracting ID",
    "description": "Entrega compilada:Licitación:Descripción de la licitación",
    "amount": "compiledRelease/tender/value/amount_PEN",
    "buyer": "Entrega compilada:Comprador:Nombre de la Organización",
    "buyer_id": "Entrega compilada:Comprador:ID de Organización",
    "category": "Entrega compilada:Licitación:Categoría principal de contratación",
    "date": "compiledRelease/tender/datePublished",
}

# El departamento NO esta en "Registros" — viene de "Ent_PartesInvolucradas"
# (archivo distinto, 1 fila = 1 organizacion). Se cruza por ID de
# entidad = buyer_id de Registros.
PARTES_COLUMN_MAP = {
    "entity_id": "Entrega compilada:Partes involucradas:ID de Entidad",
    "department_raw": "Entrega compilada:Partes involucradas:Dirección:Departamento",
}

# Los 25 departamentos oficiales del Peru (incluye Callao).
DEPARTAMENTOS_PERU = {
    "AMAZONAS", "ANCASH", "APURIMAC", "AREQUIPA", "AYACUCHO", "CAJAMARCA",
    "CALLAO", "CUSCO", "HUANCAVELICA", "HUANUCO", "ICA", "JUNIN",
    "LA LIBERTAD", "LAMBAYEQUE", "LIMA", "LORETO", "MADRE DE DIOS",
    "MOQUEGUA", "PASCO", "PIURA", "PUNO", "SAN MARTIN", "TACNA", "TUMBES",
    "UCAYALI",
}

# Alias/variantes comunes -> nombre oficial (se amplia segun lo que
# aparezca realmente en los datos).
DEPARTAMENTO_ALIASES = {
    "LIMA METROPOLITANA": "LIMA",
    "PROV. CONST. DEL CALLAO": "CALLAO",
    "PROVINCIA CONSTITUCIONAL DEL CALLAO": "CALLAO",
    "SAN MARTÍN": "SAN MARTIN",
    "APURÍMAC": "APURIMAC",
    "JUNÍN": "JUNIN",
    "HUÁNUCO": "HUANUCO",
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normalize_departamento(raw: str) -> str | None:
    """Devuelve el nombre oficial del departamento, o None si no se puede mapear."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    clean = strip_accents(raw.strip().upper())
    clean = re.sub(r"\s+", " ", clean)
    if clean in DEPARTAMENTOS_PERU:
        return clean
    if clean in DEPARTAMENTO_ALIASES:
        return DEPARTAMENTO_ALIASES[clean]
    # a veces viene como "LIMA - LIMA - JESUS MARIA" (departamento-provincia-distrito)
    first_part = clean.split(" - ")[0].strip()
    if first_part in DEPARTAMENTOS_PERU:
        return first_part
    return None


def load_raw() -> pd.DataFrame:
    path = PROCESSED_DIR / "oece_raw_combined.csv"
    if not path.exists():
        print(f"No existe {path}. Corre src/load_data.py primero.")
        sys.exit(1)
    # oece_raw_combined.csv ya fue re-guardado en UTF-8 limpio por
    # load_data.py (read_csv_robust), asi que aqui basta UTF-8 normal.
    return pd.read_csv(path, low_memory=False, encoding="utf-8")


def load_department_lookup() -> pd.Series | None:
    """Construye un lookup entity_id -> department_raw desde
    partes_raw_combined.csv (archivo "Ent_PartesInvolucradas"). Cada
    entidad puede aparecer muchas veces (1 vez por entrega en la que
    participo) con el mismo departamento — se deduplica quedandose con
    el primer valor no vacio por entity_id."""
    path = PROCESSED_DIR / "partes_raw_combined.csv"
    if not path.exists():
        print("(Opcional) No se encontro partes_raw_combined.csv — el departamento quedara vacio. "
              "Corre load_data.py con los archivos 'partes_AAAA_MM.csv' para incluirlo.")
        return None

    partes = pd.read_csv(path, low_memory=False, encoding="utf-8")
    missing = [c for c in PARTES_COLUMN_MAP.values() if c not in partes.columns]
    if missing:
        print(f"\n⚠️  ADVERTENCIA: estas columnas de PARTES_COLUMN_MAP no existen en partes_raw_combined.csv: {missing}")
        print(f"Columnas disponibles: {list(partes.columns)}")
        print("Ajusta PARTES_COLUMN_MAP en src/validate.py.\n")
        return None

    partes = partes.rename(columns={v: k for k, v in PARTES_COLUMN_MAP.items()})
    partes = partes.dropna(subset=["entity_id", "department_raw"])
    lookup = partes.drop_duplicates(subset=["entity_id"], keep="first").set_index("entity_id")["department_raw"]
    print(f"Lookup de departamento construido: {len(lookup)} entidades unicas con ubicacion conocida.")
    return lookup


def validate_and_normalize(df: pd.DataFrame, dept_lookup: pd.Series = None) -> tuple[pd.DataFrame, dict]:
    report = {}
    n_before = len(df)
    report["filas_antes"] = n_before

    missing_cols = [c for c in COLUMN_MAP.values() if c not in df.columns]
    if missing_cols:
        print(f"\n⚠️  ADVERTENCIA: estas columnas de COLUMN_MAP no existen en el CSV real: {missing_cols}")
        print(f"Columnas disponibles en el archivo: {list(df.columns)}")
        print("Ajusta COLUMN_MAP en src/validate.py con los nombres correctos y vuelve a correr.\n")
        sys.exit(1)

    rename = {v: k for k, v in COLUMN_MAP.items()}
    df = df.rename(columns=rename)

    # 1. Registros duplicados (mismo ocid exacto)
    dup_mask = df.duplicated(subset=["ocid"], keep="first")
    report["duplicados_ocid"] = int(dup_mask.sum())
    df = df[~dup_mask].copy()

    # 2. Monto faltante o cero
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    zero_or_null_amount = df["amount"].isna() | (df["amount"] == 0)
    report["monto_cero_o_nulo"] = int(zero_or_null_amount.sum())
    df["amount_flag"] = zero_or_null_amount  # se mantiene, solo se marca (no se descarta)

    # 3. Descripcion faltante
    missing_desc = df["description"].isna() | (df["description"].astype(str).str.strip() == "")
    report["descripcion_faltante"] = int(missing_desc.sum())
    df = df[~missing_desc].copy()

    # 4. Cruce con el departamento (viene de otro archivo, ver
    # load_department_lookup) y normalizacion territorial
    if dept_lookup is not None:
        df["department"] = df["buyer_id"].map(dept_lookup)
    else:
        df["department"] = None
    df["department_normalizado"] = df["department"].apply(normalize_departamento)
    no_localizados = df["department_normalizado"].isna()
    report["procesos_no_localizados"] = int(no_localizados.sum())
    report["procesos_no_localizados_pct"] = round(100 * no_localizados.sum() / len(df), 2) if len(df) else 0

    # 5. Encoding/tildes en texto (ej. JUNÍN vs JUNIN) — ya resuelto por
    # normalize_departamento via strip_accents; se reporta cuantos
    # valores distintos existian ANTES de normalizar como evidencia.
    valores_unicos_antes = df["department"].nunique()
    valores_unicos_despues = df["department_normalizado"].nunique()
    report["valores_unicos_department_antes"] = int(valores_unicos_antes)
    report["valores_unicos_department_despues"] = int(valores_unicos_despues)

    report["filas_despues"] = len(df)

    return df, report


def main():
    df = load_raw()
    print(f"Cargadas {len(df)} filas de {PROCESSED_DIR / 'oece_raw_combined.csv'}")
    print(f"Columnas: {list(df.columns)}\n")

    dept_lookup = load_department_lookup()
    df_clean, report = validate_and_normalize(df, dept_lookup)

    report_path = LOGS_DIR / "data_quality_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=== REPORTE DE CALIDAD DE DATOS ===")
    for k, v in report.items():
        print(f"  {k}: {v}")

    out_path = PROCESSED_DIR / "oece_clean.csv"
    df_clean.to_csv(out_path, index=False)
    print(f"\nGuardado: {out_path} ({len(df_clean)} filas, 1 fila = 1 proceso)")
    print(f"Reporte: {report_path}")


if __name__ == "__main__":
    main()
