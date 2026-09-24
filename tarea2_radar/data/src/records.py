"""
Carga y normalización de los ZIP mensuales de OECE.

Tarea 2 - Fase 1:
- Lee directamente los ZIP descargados manualmente.
- Usa Registros.csv como tabla principal.
- Usa Ent_PartesInvolucradas.csv para localizar al comprador.
- Trabaja con Open Contracting ID (ocid).
- Produce una fila por proceso dentro de cada corte mensual.
"""

from pathlib import Path
from zipfile import ZipFile

import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

# IMPORTANTE:
# Los ZIP están realmente en:
#
# tarea2_radar/data/data/raw/
#
# Este archivo está en:
#
# tarea2_radar/data/src/records.py

RAW_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
)


# ============================================================
# NOMBRES DE COLUMNAS REALES DE OECE
# ============================================================

COL_OCID = "Open Contracting ID"

COL_BUYER_ID = (
    "Entrega compilada:Comprador:ID de Organización"
)

COL_BUYER_NAME = (
    "Entrega compilada:Comprador:Nombre de la Organización"
)

COL_TITLE = (
    "Entrega compilada:Licitación:Título de la licitación"
)

COL_DESCRIPTION = (
    "Entrega compilada:Licitación:Descripción de la licitación"
)

COL_CATEGORY = (
    "Entrega compilada:Licitación:"
    "Categoría principal de contratación"
)

COL_METHOD = (
    "Entrega compilada:Licitación:Método de contratación"
)

COL_METHOD_DETAILS = (
    "Entrega compilada:Licitación:"
    "Detalles del método de contratación"
)

COL_AMOUNT = (
    "Entrega compilada:Licitación:Valor:Monto"
)

COL_CURRENCY = (
    "Entrega compilada:Licitación:Valor:Moneda"
)

COL_AMOUNT_PEN = (
    "compiledRelease/tender/value/amount_PEN"
)

COL_DATE = (
    "compiledRelease/tender/datePublished"
)

COL_BIDDERS = (
    "Entrega compilada:Licitación:Número de licitantes"
)

COL_PARTY_NAME = (
    "Entrega compilada:Partes involucradas:Nombre común"
)

COL_PARTY_ID = (
    "Entrega compilada:Partes involucradas:ID de Entidad"
)

COL_PARTY_REGION = (
    "Entrega compilada:Partes involucradas:Dirección:Región"
)

COL_PARTY_DEPARTMENT = (
    "Entrega compilada:Partes involucradas:Dirección:Departamento"
)

COL_PARTY_ROLES = (
    "Entrega compilada:Partes involucradas:Roles de las partes"
)


# ============================================================
# UTILIDADES
# ============================================================

def find_member(
    z: ZipFile,
    filename: str,
) -> str:
    """
    Busca un archivo dentro del ZIP ignorando mayúsculas,
    espacios y posibles rutas internas.
    """

    target = filename.lower().strip()

    for member in z.namelist():

        name = Path(member).name.lower().strip()

        if name == target:
            return member

    raise FileNotFoundError(
        f"No se encontró '{filename}' dentro del ZIP.\n\n"
        "Archivos disponibles:\n"
        + "\n".join(z.namelist())
    )


def read_csv_from_zip(
    zip_path: Path,
    member: str,
) -> pd.DataFrame:
    """
    Lee un CSV directamente desde el ZIP.
    No descomprime físicamente el archivo.
    """

    with ZipFile(zip_path) as z:

        with z.open(member) as f:

            return pd.read_csv(
                f,
                low_memory=False,
            )


def find_month_zip(
    month: str,
    year: str = "2026",
) -> Path:
    """
    Encuentra el ZIP correspondiente al mes.
    """

    month = str(month).zfill(2)

    if not RAW_DIR.exists():

        raise FileNotFoundError(
            f"No existe la carpeta de datos:\n{RAW_DIR}"
        )

    candidates = []

    for path in RAW_DIR.glob("*.zip"):

        name = path.name

        if (
            f"{year}-{month}" in name
            or f"{year}_{month}" in name
        ):
            candidates.append(path)

    if not candidates:

        raise FileNotFoundError(
            f"No se encontró ZIP para {year}-{month} en:\n"
            f"{RAW_DIR}"
        )

    if len(candidates) > 1:

        raise RuntimeError(
            f"Hay más de un ZIP para {year}-{month}:\n"
            + "\n".join(
                p.name for p in candidates
            )
        )

    return candidates[0]


# ============================================================
# BUYERS / PARTES
# ============================================================

def extract_buyers(
    parties: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extrae la parte que cumple el rol de buyer/comprador.

    Ent_PartesInvolucradas.csv contiene múltiples partes por OCID,
    por lo que primero filtramos por rol.
    """

    required = [
        COL_OCID,
        COL_PARTY_DEPARTMENT,
        COL_PARTY_REGION,
        COL_PARTY_ROLES,
        COL_PARTY_NAME,
        COL_PARTY_ID,
    ]

    missing = [
        c for c in required
        if c not in parties.columns
    ]

    if missing:

        raise KeyError(
            "Faltan columnas en "
            "Ent_PartesInvolucradas.csv:\n"
            + "\n".join(missing)
        )

    roles = (
        parties[COL_PARTY_ROLES]
        .fillna("")
        .astype(str)
        .str.lower()
    )

    # Buscamos buyer/comprador.
    buyer_mask = (
        roles.str.contains("buyer", na=False)
        | roles.str.contains("comprador", na=False)
    )

    buyers = parties.loc[
        buyer_mask,
        [
            COL_OCID,
            COL_PARTY_ID,
            COL_PARTY_NAME,
            COL_PARTY_DEPARTMENT,
            COL_PARTY_REGION,
        ],
    ].copy()

    # Si hay varios registros buyer para un mismo OCID,
    # conservamos el primero.
    buyers = buyers.drop_duplicates(
        subset=COL_OCID,
        keep="first",
    )

    buyers = buyers.rename(
        columns={
            COL_PARTY_ID: "buyer_id_parties",
            COL_PARTY_NAME: "buyer_name_parties",
            COL_PARTY_DEPARTMENT: "departamento_raw",
            COL_PARTY_REGION: "region_raw",
        }
    )

    return buyers


# ============================================================
# CARGA DE UN MES
# ============================================================

def load_month(
    zip_path: Path,
) -> pd.DataFrame:

    print()
    print("=" * 60)
    print(f"Procesando: {zip_path.name}")
    print("=" * 60)

    # --------------------------------------------------------
    # Localizar archivos
    # --------------------------------------------------------

    with ZipFile(zip_path) as z:

        records_member = find_member(
            z,
            "Registros.csv",
        )

        parties_member = find_member(
            z,
            "Ent_PartesInvolucradas.csv",
        )

    print(
        f"Registros: {records_member}"
    )

    print(
        f"Partes: {parties_member}"
    )

    # --------------------------------------------------------
    # Leer
    # --------------------------------------------------------

    records = read_csv_from_zip(
        zip_path,
        records_member,
    )

    parties = read_csv_from_zip(
        zip_path,
        parties_member,
    )

    print(
        f"Filas Registros.csv: "
        f"{len(records):,}"
    )

    print(
        f"Filas Ent_PartesInvolucradas.csv: "
        f"{len(parties):,}"
    )

    # --------------------------------------------------------
    # Comprobar OCID
    # --------------------------------------------------------

    if COL_OCID not in records.columns:

        raise KeyError(
            f"No existe la columna '{COL_OCID}' "
            "en Registros.csv"
        )

    # --------------------------------------------------------
    # Diagnóstico de duplicados dentro del mes
    # --------------------------------------------------------

    duplicates = records.duplicated(
        subset=COL_OCID,
        keep=False,
    )

    n_duplicates = int(
        duplicates.sum()
    )

    n_unique = records[
        COL_OCID
    ].nunique()

    print(
        f"OCID únicos: {n_unique:,}"
    )

    print(
        f"Filas duplicadas por OCID: "
        f"{n_duplicates:,}"
    )

    # --------------------------------------------------------
    # Extraer compradores
    # --------------------------------------------------------

    buyers = extract_buyers(
        parties
    )

    print(
        f"OCID con buyer identificado: "
        f"{buyers[COL_OCID].nunique():,}"
    )

    # --------------------------------------------------------
    # Seleccionar columnas disponibles
    # --------------------------------------------------------

    columns_map = {
        COL_OCID: "ocid",
        COL_BUYER_ID: "buyer_id",
        COL_BUYER_NAME: "comprador",
        COL_TITLE: "titulo",
        COL_DESCRIPTION: "descripcion",
        COL_CATEGORY: "categoria",
        COL_METHOD: "metodo_contratacion",
        COL_METHOD_DETAILS: "procedimiento",
        COL_AMOUNT: "monto",
        COL_CURRENCY: "moneda",
        COL_AMOUNT_PEN: "monto_pen",
        COL_DATE: "fecha_publicacion",
        COL_BIDDERS: "num_postores",
    }

    available = {
        original: normalized
        for original, normalized
        in columns_map.items()
        if original in records.columns
    }

    df = records[
        list(available.keys())
    ].copy()

    df = df.rename(
        columns=available
    )

    # --------------------------------------------------------
    # Garantizar columnas
    # --------------------------------------------------------

    expected = [
        "ocid",
        "buyer_id",
        "comprador",
        "titulo",
        "descripcion",
        "categoria",
        "metodo_contratacion",
        "procedimiento",
        "monto",
        "moneda",
        "monto_pen",
        "fecha_publicacion",
        "num_postores",
    ]

    for column in expected:

        if column not in df.columns:

            df[column] = pd.NA

    # --------------------------------------------------------
    # Unir territorio
    # --------------------------------------------------------

    df = df.merge(
        buyers[
            [
                COL_OCID,
                "departamento_raw",
                "region_raw",
            ]
        ],
        left_on="ocid",
        right_on=COL_OCID,
        how="left",
    )

    df = df.drop(
        columns=[COL_OCID],
        errors="ignore",
    )

    # --------------------------------------------------------
    # Mes
    # --------------------------------------------------------

    month = zip_path.name[:7]

    df["mes_origen"] = month

    # --------------------------------------------------------
    # Conversión numérica
    # --------------------------------------------------------

    for column in [
        "monto",
        "monto_pen",
        "num_postores",
    ]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    # --------------------------------------------------------
    # Fechas
    # --------------------------------------------------------

    df["fecha_publicacion"] = pd.to_datetime(
        df["fecha_publicacion"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Orden
    # --------------------------------------------------------

    preferred_order = [
        "ocid",
        "comprador",
        "buyer_id",
        "titulo",
        "descripcion",
        "categoria",
        "metodo_contratacion",
        "procedimiento",
        "monto",
        "monto_pen",
        "moneda",
        "fecha_publicacion",
        "num_postores",
        "departamento_raw",
        "region_raw",
        "mes_origen",
    ]

    existing = [
        c for c in preferred_order
        if c in df.columns
    ]

    df = df[existing]

    return df


# ============================================================
# CARGAR TODOS LOS MESES
# ============================================================

def load_all_months(
    months: list[str],
    year: str = "2026",
) -> pd.DataFrame:

    frames = []

    for month in months:

        zip_path = find_month_zip(
            month,
            year,
        )

        df = load_month(
            zip_path
        )

        frames.append(df)

    if not frames:

        raise ValueError(
            "No se cargó ningún mes."
        )

    result = pd.concat(
        frames,
        ignore_index=True,
    )

    return result
