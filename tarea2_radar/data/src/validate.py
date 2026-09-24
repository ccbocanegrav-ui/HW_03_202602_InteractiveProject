"""
Tarea 2 - Fase 2

Validación y normalización territorial.

Reglas:

1. OCID duplicados.
2. Monto faltante.
3. Monto cero.
4. Descripción faltante.
5. Departamento faltante.
6. Provincias/departamentos mezclados.
7. Inconsistencias de texto.
8. Normalización a los 25 departamentos del Perú.

Nada se elimina silenciosamente.
"""

from pathlib import Path
import re
import unicodedata

import pandas as pd

from records import load_all_months


# ============================================================
# RUTAS
# ============================================================

BASE_DIR = (
    Path(__file__).resolve().parent.parent
)

PROCESSED_DIR = (
    BASE_DIR / "data" / "processed"
)

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# DEPARTAMENTOS DEL PERÚ
# ============================================================

DEPARTMENTS = {
    "AMAZONAS",
    "ANCASH",
    "APURIMAC",
    "AREQUIPA",
    "AYACUCHO",
    "CAJAMARCA",
    "CALLAO",
    "CUSCO",
    "HUANCAVELICA",
    "HUANUCO",
    "ICA",
    "JUNIN",
    "LA LIBERTAD",
    "LAMBAYEQUE",
    "LIMA",
    "LORETO",
    "MADRE DE DIOS",
    "MOQUEGUA",
    "PASCO",
    "PIURA",
    "PUNO",
    "SAN MARTIN",
    "TACNA",
    "TUMBES",
    "UCAYALI",
}


# ============================================================
# NORMALIZACIÓN DE TEXTO
# ============================================================

def normalize_text(value) -> str | None:

    if pd.isna(value):
        return None

    text = str(value).strip().upper()

    text = unicodedata.normalize(
        "NFD",
        text,
    )

    text = "".join(
        ch
        for ch in text
        if unicodedata.category(ch) != "Mn"
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


# ============================================================
# NORMALIZACIÓN DE DEPARTAMENTO
# ============================================================

DEPARTMENT_ALIASES = {
    "ANCASH": "ANCASH",
    "ÁNCASH": "ANCASH",
    "ANCAH": "ANCASH",

    "APURIMAC": "APURIMAC",
    "APURÍMAC": "APURIMAC",

    "CUSCO": "CUSCO",
    "CUZCO": "CUSCO",

    "JUNIN": "JUNIN",
    "JUNÍN": "JUNIN",

    "HUANUCO": "HUANUCO",
    "HUÁNUCO": "HUANUCO",

    "SAN MARTIN": "SAN MARTIN",
    "SAN MARTÍN": "SAN MARTIN",

    "LIMA METROPOLITANA": "LIMA",

    "CALLAO": "CALLAO",
    "PROVINCIA CONSTITUCIONAL DEL CALLAO": "CALLAO",
}


def normalize_department(
    value,
) -> str | None:

    text = normalize_text(value)

    if text is None:
        return None

    if text in DEPARTMENT_ALIASES:
        return DEPARTMENT_ALIASES[text]

    if text in DEPARTMENTS:
        return text

    return None


# ============================================================
# NORMALIZACIÓN DE PROVINCIA
# ============================================================

# Mapa mínimo para recuperar departamentos cuando OECE
# entrega una provincia en lugar del departamento.
#
# Se puede ampliar posteriormente con las 196 provincias.

PROVINCE_TO_DEPARTMENT = {

    # Amazonas
    "CHACHAPOYAS": "AMAZONAS",
    "BAGUA": "AMAZONAS",
    "BONGARA": "AMAZONAS",
    "CONDORCANQUI": "AMAZONAS",
    "LUYA": "AMAZONAS",
    "RODRIGUEZ DE MENDOZA": "AMAZONAS",
    "UTCUBAMBA": "AMAZONAS",

    # Ancash
    "HUARAZ": "ANCASH",
    "AIJA": "ANCASH",
    "ANTONIO RAYMONDI": "ANCASH",
    "ASUNCION": "ANCASH",
    "BOLOGNESI": "ANCASH",
    "CARHUAZ": "ANCASH",
    "CARLOS FERMIN FITZCARRALD": "ANCASH",
    "CASMA": "ANCASH",
    "CORONGO": "ANCASH",
    "HUARI": "ANCASH",
    "HUARMEY": "ANCASH",
    "HUAYLAS": "ANCASH",
    "MARISCAL LUZURIAGA": "ANCASH",
    "OCROS": "ANCASH",
    "PALLASCA": "ANCASH",
    "POMABAMBA": "ANCASH",
    "RECUAY": "ANCASH",
    "SANTA": "ANCASH",
    "SIHUAS": "ANCASH",
    "YUNGAY": "ANCASH",

    # Arequipa
    "AREQUIPA": "AREQUIPA",
    "CAMANA": "AREQUIPA",
    "CARAVELI": "AREQUIPA",
    "CASTILLA": "AREQUIPA",
    "CAYLLOMA": "AREQUIPA",
    "CONDESUYOS": "AREQUIPA",
    "ISLAY": "AREQUIPA",
    "LA UNION": "AREQUIPA",

    # Cusco
    "CUSCO": "CUSCO",
    "ACOMAYO": "CUSCO",
    "ANTA": "CUSCO",
    "CALCA": "CUSCO",
    "CANAS": "CUSCO",
    "CANCHIS": "CUSCO",
    "CHUMBIVILCAS": "CUSCO",
    "ESPINAR": "CUSCO",
    "LA CONVENCION": "CUSCO",
    "PARURO": "CUSCO",
    "PAUCARTAMBO": "CUSCO",
    "QUISPICANCHI": "CUSCO",
    "URUBAMBA": "CUSCO",

    # Lima
    "LIMA": "LIMA",
    "BARRANCA": "LIMA",
    "CAJATAMBO": "LIMA",
    "CANTA": "LIMA",
    "CAÑETE": "LIMA",
    "CANTA": "LIMA",
    "HUARAL": "LIMA",
    "HUAROCHIRI": "LIMA",
    "OYON": "LIMA",
    "YAUYOS": "LIMA",

    # Callao
    "CALLAO": "CALLAO",

    # Piura
    "PIURA": "PIURA",
    "AYABACA": "PIURA",
    "HUANCABAMBA": "PIURA",
    "MORROPON": "PIURA",
    "PAITA": "PIURA",
    "SECHURA": "PIURA",
    "SULLANA": "PIURA",
    "TALARA": "PIURA",

    # Puno
    "PUNO": "PUNO",
    "AZANGARO": "PUNO",
    "CARABAYA": "PUNO",
    "CHUCUITO": "PUNO",
    "EL COLLAO": "PUNO",
    "HUANCANE": "PUNO",
    "LAMPA": "PUNO",
    "MELGAR": "PUNO",
    "MOHO": "PUNO",
    "SAN ANTONIO DE PUTINA": "PUNO",
    "SAN ROMAN": "PUNO",
    "SANDIA": "PUNO",
    "YUNGUYO": "PUNO",
}


def resolve_department(
    department,
    region,
) -> str | None:

    # Primero intentamos el departamento declarado.
    dept = normalize_department(
        department
    )

    if dept:
        return dept

    # Si OECE puso una provincia en ese campo,
    # intentamos recuperarla mediante el mapa.
    dept_from_province = (
        PROVINCE_TO_DEPARTMENT.get(
            normalize_text(department)
        )
        if department is not None
        else None
    )

    if dept_from_province:
        return dept_from_province

    # Finalmente intentamos con region.
    region_norm = normalize_text(
        region
    )

    if region_norm in PROVINCE_TO_DEPARTMENT:

        return PROVINCE_TO_DEPARTMENT[
            region_norm
        ]

    return None


# ============================================================
# VALIDACIÓN
# ============================================================

def validate_and_normalize(
    df: pd.DataFrame,
):

    report = []

    n_before = len(df)

    # --------------------------------------------------------
    # 1. OCID faltante
    # --------------------------------------------------------

    missing_ocid = (
        df["ocid"]
        .isna()
        | (
            df["ocid"]
            .astype(str)
            .str.strip()
            == ""
        )
    )

    report.append({
        "regla": "OCID faltante",
        "flagged": int(
            missing_ocid.sum()
        ),
        "accion": (
            "descartado: no es posible identificar "
            "el proceso sin OCID"
            if missing_ocid.any()
            else
            "ninguno encontrado"
        ),
    })

    if missing_ocid.any():

        df = df[
            ~missing_ocid
        ].copy()

    # --------------------------------------------------------
    # 2. Duplicados
    # --------------------------------------------------------

    duplicate_mask = (
        df.duplicated(
            subset="ocid",
            keep="first",
        )
    )

    n_duplicates = int(
        duplicate_mask.sum()
    )

    report.append({
        "regla": "OCID duplicado",
        "flagged": n_duplicates,
        "accion": (
            "eliminado: se conserva "
            "la primera aparición"
            if n_duplicates
            else
            "ninguno encontrado"
        ),
    })

    if n_duplicates:

        df = df[
            ~duplicate_mask
        ].copy()

    # --------------------------------------------------------
    # 3. Monto
    # --------------------------------------------------------

    df["monto_pen"] = pd.to_numeric(
        df["monto_pen"],
        errors="coerce",
    )

    missing_amount = (
        df["monto_pen"].isna()
    )

    zero_amount = (
        df["monto_pen"].eq(0)
    )

    df["monto_valido"] = (
        ~missing_amount
        & ~zero_amount
    )

    report.append({
        "regla": "Monto faltante",
        "flagged": int(
            missing_amount.sum()
        ),
        "accion": (
            "mantenido con advertencia; "
            "excluido de agregados monetarios"
        ),
    })

    report.append({
        "regla": "Monto igual a cero",
        "flagged": int(
            zero_amount.sum()
        ),
        "accion": (
            "mantenido con advertencia; "
            "excluido de agregados monetarios"
        ),
    })

    # --------------------------------------------------------
    # 4. Descripción
    # --------------------------------------------------------

    description_missing = (
        df["descripcion"].isna()
        | (
            df["descripcion"]
            .fillna("")
            .astype(str)
            .str.strip()
            == ""
        )
    )

    df["descripcion_valida"] = (
        ~description_missing
    )

    # Usamos título como respaldo.
    df.loc[
        description_missing,
        "descripcion"
    ] = df.loc[
        description_missing,
        "titulo"
    ]

    report.append({
        "regla": "Descripción faltante",
        "flagged": int(
            description_missing.sum()
        ),
        "accion": (
            "corregido: se utiliza el título "
            "como respaldo; queda marcado "
            "descripcion_valida=False"
        ),
    })

    # --------------------------------------------------------
    # 5. Departamento
    # --------------------------------------------------------

    df["departamento"] = df.apply(
        lambda row: resolve_department(
            row["departamento_raw"],
            row["region_raw"],
        ),
        axis=1,
    )

    missing_department = (
        df["departamento"].isna()
    )

    report.append({
        "regla": "Departamento no identificable",
        "flagged": int(
            missing_department.sum()
        ),
        "accion": (
            "mantenido con advertencia; "
            "no se elimina del corpus, "
            "pero queda fuera del mapa"
        ),
    })

    # --------------------------------------------------------
    # 6. Normalización de texto
    # --------------------------------------------------------

    df["comprador_normalizado"] = (
        df["comprador"]
        .apply(normalize_text)
    )

    df["categoria_normalizada"] = (
        df["categoria"]
        .apply(normalize_text)
    )

    unique_before = (
        df["comprador"]
        .fillna("")
        .astype(str)
        .nunique()
    )

    unique_after = (
        df["comprador_normalizado"]
        .fillna("")
        .nunique()
    )

    report.append({
        "regla": (
            "Inconsistencias de mayúsculas/"
            "acentos/espacios"
        ),
        "flagged": max(
            0,
            unique_before
            - unique_after,
        ),
        "accion": (
            "corregido en columnas normalizadas; "
            "se conserva el nombre original "
            "para mostrarlo al usuario"
        ),
    })

    # --------------------------------------------------------
    # Resultado
    # --------------------------------------------------------

    n_after = len(df)

    report.append({
        "regla": "TOTAL",
        "flagged": f"{n_before} -> {n_after}",
        "accion": (
            "una fila por proceso identificado "
            "por OCID"
        ),
    })

    return df, report


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("TAREA 2 - FASE 2: VALIDACIÓN")
    print("=" * 60)

    # --------------------------------------------------------
    # Cargar corpus
    # --------------------------------------------------------

    df = load_all_months(
        months=[
            "01",
            "02",
            "03",
        ],
        year="2026",
    )

    n_raw = len(df)

    print()
    print(
        f"Filas crudas: {n_raw:,}"
    )

    # --------------------------------------------------------
    # Validar
    # --------------------------------------------------------

    df, report = (
        validate_and_normalize(df)
    )

    # --------------------------------------------------------
    # Guardar dataset
    # --------------------------------------------------------

    output_csv = (
        PROCESSED_DIR
        / "procesos.csv"
    )

    df.to_csv(
        output_csv,
        index=False,
        encoding="utf-8-sig",
    )

    # --------------------------------------------------------
    # Reporte Markdown
    # --------------------------------------------------------

    lines = []

    lines.append(
        "# Reporte de calidad de datos — "
        "Tarea 2, Fase 2"
    )

    lines.append("")

    lines.append(
        f"Filas crudas: **{n_raw:,}**"
    )

    lines.append(
        f"Filas finales: **{len(df):,}**"
    )

    lines.append("")

    lines.append(
        "## Reglas de validación"
    )

    lines.append("")

    lines.append(
        "| Regla | Registros marcados | Acción |"
    )

    lines.append(
        "|---|---:|---|"
    )

    for item in report:

        lines.append(
            f"| {item['regla']} | "
            f"{item['flagged']} | "
            f"{item['accion']} |"
        )

    # --------------------------------------------------------
    # Distribución territorial
    # --------------------------------------------------------

    lines.append("")

    lines.append(
        "## Distribución por departamento"
    )

    lines.append("")

    lines.append(
        "| Departamento | Procesos |"
    )

    lines.append(
        "|---|---:|"
    )

    counts = (
        df["departamento"]
        .value_counts(
            dropna=False
        )
    )

    for department, count in counts.items():

        label = (
            department
            if pd.notna(department)
            else "(sin ubicar)"
        )

        lines.append(
            f"| {label} | {count:,} |"
        )

    # --------------------------------------------------------
    # Distribución mensual
    # --------------------------------------------------------

    lines.append("")

    lines.append(
        "## Procesos por mes"
    )

    lines.append("")

    lines.append(
        "| Mes | Procesos |"
    )

    lines.append(
        "|---|---:|"
    )

    monthly = (
        df["mes_origen"]
        .value_counts()
        .sort_index()
    )

    for month, count in monthly.items():

        lines.append(
            f"| {month} | {count:,} |"
        )

    # --------------------------------------------------------
    # Guardar reporte
    # --------------------------------------------------------

    report_path = (
        PROCESSED_DIR
        / "data_quality_report.md"
    )

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Consola
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("RESULTADO")
    print("=" * 60)

    print(
        f"Filas antes:  {n_raw:,}"
    )

    print(
        f"Filas después: {len(df):,}"
    )

    print()

    for item in report:

        print(
            f"[{item['flagged']}] "
            f"{item['regla']}: "
            f"{item['accion']}"
        )

    print()
    print(
        f"Dataset guardado en:\n"
        f"{output_csv}"
    )

    print()
    print(
        f"Reporte guardado en:\n"
        f"{report_path}"
    )


if __name__ == "__main__":
    main()
