"""
Tarea 2 - Fase 1: adquisición.

Los ZIP de OECE se descargan manualmente y se colocan en:

tarea2_radar/data/data/raw/

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


if __name__ == "__main__":
    main()
