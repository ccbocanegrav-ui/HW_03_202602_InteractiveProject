"""
Tarea 2 - Fase 1: adquisición.

Los ZIP de OECE se descargan manualmente y se colocan en:

tarea2_radar/data/data/raw/
=======
HALLAZGO 1 (igual que en Task 1): el portal de OECE
(contratacionesabiertas.oece.gob.pe) bloquea descargas automatizadas
(bot-detection), asi que la descarga de los archivos mensuales es
MANUAL — igual que con los PDFs de la Ley y el DS.

HALLAZGO 2: el archivo que el portal entrega con extension .csv NO es
un CSV plano — es en realidad un ZIP (verificado con la firma de bytes
PK\\x03\\x04) que contiene VARIAS tablas relacionadas (comprador,
licitantes, items, adjudicaciones, proveedores adjudicados, etc.),
todas enlazadas por "ocid". Este script detecta eso automaticamente
(no confia en la extension) y extrae cada tabla por separado.

QUE DESCARGAR (manual, una sola vez por mes):
    1. Ve a https://contratacionesabiertas.oece.gob.pe/descargas
    2. Descarga AL MENOS 3 archivos mensuales de 2026 (formato CSV)
    3. Guardalos en data/raw/ con el nombre EXACTO:
       oece_2026_01.csv, oece_2026_02.csv, oece_2026_03.csv
       (ajusta MONTHS abajo a los meses que realmente descargaste;
       aunque el portal los llame .csv, este script funciona igual si
       en realidad es un zip)


Este script NO descarga desde Internet.

Hace lo siguiente:
- encuentra los ZIP;
- identifica enero, febrero y marzo de 2026;
- verifica que contienen Registros.csv;
- verifica que contienen Ent_PartesInvolucradas.csv;
- registra tamaño y tiempo;
- no modifica los ZIP.
"""

from pathlib import Path
from zipfile import ZipFile, BadZipFile
import logging
import re
import time
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
EXTRACTED_DIR = RAW_DIR / "extracted"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Ajusta esta lista a los meses que efectivamente descargaste.
MONTHS = ["2026_06", "2026_07", "2026_08"]
# ============================================================
# RUTAS
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = (
    PROJECT_DIR
    / "data"
    / "raw"
)

LOG_DIR = PROJECT_DIR / "logs"
LOG_FILE = LOG_DIR / "acquire.log"

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN
# ============================================================

def extract_if_zip(path: Path) -> tuple[Path, list[Path]]:
    """Devuelve la carpeta con las tablas de este mes y la lista de
    archivos CSV encontrados dentro. Si el archivo NO es un zip (es un
    CSV plano de verdad), lo trata como una unica tabla llamada
    'registros' para que el resto del pipeline funcione igual."""
    month_dir = EXTRACTED_DIR / path.stem
    month_dir.mkdir(parents=True, exist_ok=True)

    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            names_before = set(month_dir.glob("*"))
            zf.extractall(month_dir)
            csvs = sorted(month_dir.rglob("*.csv"))
        return month_dir, csvs
    else:
        # No es zip pese al nombre .csv del portal: es un CSV plano real.
        dest = month_dir / "registros.csv"
        dest.write_bytes(path.read_bytes())
        return month_dir, [dest]


def inventory_tables(files: list[Path]) -> dict[str, list[tuple[str, Path]]]:
    """Para cada mes, extrae y devuelve {mes: [(nombre_tabla, path), ...]}."""
    inventory = {}
    for path in files:
        month = path.stem.replace("oece_", "")
        _, csvs = extract_if_zip(path)
        inventory[month] = [(c.stem, c) for c in csvs]
    return inventory


def print_inventory(inventory: dict[str, list[tuple[str, Path]]]) -> None:
    print("\n=== TABLAS ENCONTRADAS POR MES ===")
    for month, tables in inventory.items():
        print(f"\n{month}:")
        for name, path in tables:
            try:
                df = pd.read_csv(path, low_memory=False, nrows=5)
                # cuenta filas reales sin cargar todo en memoria dos veces
                n_rows = sum(1 for _ in open(
                    path, encoding="utf-8", errors="ignore")) - 1
                print(f"  - {name}: {n_rows} filas, {len(df.columns)} columnas")
                print(f"      columnas: {list(df.columns)[:8]}"
                      f"{'...' if len(df.columns) > 8 else ''}")
            except Exception as e:
                print(f"  - {name}: (no se pudo leer: {e})")


def combine_by_table(inventory: dict[str, list[tuple[str, Path]]]) -> dict[str, pd.DataFrame]:
    """Combina, PARA CADA NOMBRE DE TABLA, los archivos de todos los
    meses entre si (nunca mezcla 'registros' de un mes con 'partes' de
    otro — eso corromperia los datos)."""
    by_table: dict[str, list[pd.DataFrame]] = {}
    for month, tables in inventory.items():
        for name, path in tables:
            df = pd.read_csv(path, low_memory=False)
            df["_mes_origen"] = month
            by_table.setdefault(name, []).append(df)

    combined = {}
    for name, dfs in by_table.items():
        combined[name] = pd.concat(dfs, ignore_index=True)
    return combined


def save_and_log(combined: dict[str, pd.DataFrame], elapsed: float) -> None:
    log_path = LOGS_DIR / "acquisition_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Tiempo total de adquisicion: {elapsed:.1f}s\n\n")
        for name, df in combined.items():
            f.write(
                f"Tabla '{name}': {len(df)} filas, {len(df.columns)} columnas\n")
            f.write(f"  columnas: {list(df.columns)}\n\n")

    print(f"\nLog guardado en: {log_path}")

    for name, df in combined.items():
        out_path = PROCESSED_DIR / f"oece_{name}_combined.csv"
        df.to_csv(out_path, index=False)
        print(f"Guardado: {out_path} ({len(df)} filas)")


YEAR = "2026"
REQUIRED_MONTHS = ["01", "02", "03"]


# ============================================================
# FUNCIONES
# ============================================================

def detect_month(filename: str) -> str | None:

    patterns = [
        r"2026[-_](01|02|03)",
        r"(01|02|03)[-_]2026",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            filename,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1)

    return None


def human_size(size_bytes: int) -> str:

    return (
        f"{size_bytes / (1024 * 1024):.2f} MB"
    )


def inspect_zip(zip_path: Path) -> dict:

    result = {
        "path": zip_path,
        "month": detect_month(zip_path.name),
        "size": zip_path.stat().st_size,
        "valid": False,
        "records": False,
        "parties": False,
        "error": None,
    }

    try:

        with ZipFile(zip_path, "r") as z:

            members = z.namelist()

            # OECE español
            result["records"] = any(
                Path(x).name.lower()
                == "registros.csv"
                for x in members
            )

            result["parties"] = any(
                Path(x).name.lower()
                == "ent_partesinvolucradas.csv"
                for x in members
            )

            result["valid"] = (
                result["records"]
                and result["parties"]
            )

    except BadZipFile as exc:

        result["error"] = (
            f"ZIP inválido: {exc}"
        )

    except Exception as exc:

        result["error"] = str(exc)

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    start = time.perf_counter()

    logger.info(
        "========== INICIO =========="
    )

    logger.info(
        "RAW_DIR=%s",
        RAW_DIR,
    )

    print()
    print("=" * 50)
    print("TAREA 2 - FASE 1: ADQUISICIÓN")
    print("=" * 50)

    print()
    print(
        f"Buscando ZIP en:\n{RAW_DIR}"
    )

    zip_files = sorted(
        RAW_DIR.glob("*.zip")
    )

    if not zip_files:

        print()
        print(
            "ERROR: no hay ZIP en la carpeta."
        )

        logger.error(
            "No se encontraron ZIP."
        )

        return

    print()
    print(
        f"ZIP encontrados: {len(zip_files)}"
    )

    found = {}

    valid = 0
    invalid = 0

    for zip_path in zip_files:

        result = inspect_zip(
            zip_path
        )

        month = result["month"]

        print()
        print(
            f"ZIP: {zip_path.name}"
        )

        print(
            f"  Tamaño: "
            f"{human_size(result['size'])}"
        )

        print(
            f"  Mes: "
            f"{month or 'NO DETECTADO'}"
        )

        print(
            "  Registros.csv: "
            f"{'OK' if result['records'] else 'FALTA'}"
        )

        print(
            "  Ent_PartesInvolucradas.csv: "
            f"{'OK' if result['parties'] else 'FALTA'}"
        )

        if result["error"]:

            print(
                f"  ERROR: {result['error']}"
            )

            invalid += 1

            logger.error(
                "ZIP ERROR | %s | %s",
                zip_path.name,
                result["error"],
            )

            continue

        if result["valid"]:

            valid += 1

            logger.info(
                "ZIP OK | %s | mes=%s | "
                "size=%s",
                zip_path.name,
                month,
                human_size(result["size"]),
            )

        else:

            invalid += 1

            logger.warning(
                "ZIP INCOMPLETO | %s",
                zip_path.name,
            )

        if (
            result["valid"]
            and month in REQUIRED_MONTHS
        ):

            if month not in found:

                found[month] = zip_path

            else:

                logger.warning(
                    "Más de un ZIP para "
                    "2026-%s",
                    month,
                )

    # ========================================================
    # CORPUS
    # ========================================================

    print()
    print("=" * 50)
    print("VERIFICACIÓN DEL CORPUS")
    print("=" * 50)

    missing = []

    for month in REQUIRED_MONTHS:

        if month in found:

            print(
                f"[OK] 2026-{month} → "
                f"{found[month].name}"
            )

        else:

            print(
                f"[FALTA] 2026-{month}"
            )

            missing.append(month)

    # ========================================================
    # RESUMEN
    # ========================================================

    elapsed = (
        time.perf_counter()
        - start
    )

    print()
    print("=" * 50)
    print("RESUMEN")
    print("=" * 50)

    print(
        f"ZIP encontrados: {len(zip_files)}"
    )

    print(
        f"ZIP válidos:     {valid}"
    )

    print(
        f"ZIP inválidos:   {invalid}"
    )

    print(
        f"Meses encontrados: "
        f"{len(found)}/{len(REQUIRED_MONTHS)}"
    )

    print(
        f"Tiempo: {elapsed:.3f} s"
    )

    print(
        f"Log: {LOG_FILE}"
    )

    logger.info(
        "RESUMEN | encontrados=%s | "
        "validos=%s | invalidos=%s | "
        "meses=%s | faltantes=%s | "
        "elapsed=%.3f",
        len(zip_files),
        valid,
        invalid,
        len(found),
        ",".join(missing),
        elapsed,
    )

    if missing:

        print()
        print(
            "⚠️ Corpus incompleto."
        )

    else:

        print()
        print(
            "✓ Corpus completo."
        )

        print(
            "✓ Enero, febrero y marzo 2026."
        )

files = sorted(RAW_DIR.glob("*.zip"))

if not files:
    print("\nNo hay archivos ZIP en data/raw.")
    sys.exit(1)

t0 = time.time()

inventory = inventory_tables(files)
print_inventory(inventory)

combined = combine_by_table(inventory)

elapsed = time.time() - t0
save_and_log(combined, elapsed)

print("\n=== SIGUIENTE PASO ===")
print("Revisa los nombres de tabla de arriba e identifica cual es:")
print("  - la tabla PRINCIPAL de procesos (ocid, descripcion, monto, fecha, comprador)")
print("  - la tabla de PARTES/ENTIDADES (para sacar el departamento)")
print("  - la tabla de POSTORES/ADJUDICACIONES (para el indicador de riesgo)")
print("Con esos 3 nombres reales, actualizamos COLUMN_MAP en validate.py.")


if __name__ == "__main__":
    main()
