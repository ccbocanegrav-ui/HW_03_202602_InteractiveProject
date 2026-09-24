"""
load_data.py — Task 2, Phase 1: Data Acquisition

HALLAZGO (igual que en Task 1): el portal de OECE
(contratacionesabiertas.oece.gob.pe) bloquea descargas automatizadas
(bot-detection), asi que — igual que con los PDFs de la Ley y el DS —
la descarga de los archivos mensuales es MANUAL. Este script verifica
lo que ya descargaste y lo prepara para las fases siguientes.

QUE DESCARGAR (manual, una sola vez):
    1. Ve a https://contratacionesabiertas.oece.gob.pe/descargas
    2. Descarga AL MENOS 3 archivos mensuales de 2026 en formato CSV
       (mas facil de procesar que el JSON OCDS completo para este
       proyecto). Ejemplo: enero, febrero, marzo 2026.
    3. Guardalos en data/raw/ con el nombre EXACTO:
       oece_2026_01.csv, oece_2026_02.csv, oece_2026_03.csv
       (ajusta el mes/año segun lo que descargues — ver MONTHS abajo)

Uso:
    python src/load_data.py
"""

import sys
import time
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Ajusta esta lista a los meses que efectivamente descargaste.
MONTHS = ["2026_01", "2026_02", "2026_03"]


def check_files() -> list[Path]:
    found = []
    missing = []
    for m in MONTHS:
        path = RAW_DIR / f"oece_{m}.csv"
        if path.exists():
            found.append(path)
        else:
            missing.append(path.name)

    print(f"Archivos encontrados: {len(found)}/{len(MONTHS)}")
    for p in found:
        size_mb = p.stat().st_size / (1024 * 1024)
        print(f"  [OK] {p.name} ({size_mb:.1f} MB)")
    if missing:
        print(f"\nFALTAN {len(missing)} archivo(s) en data/raw/:")
        for name in missing:
            print(f"  - {name}")
        print("\nDescargalos manualmente de https://contratacionesabiertas.oece.gob.pe/descargas")
    return found


def load_and_combine(files: list[Path]) -> pd.DataFrame:
    dfs = []
    t0 = time.time()
    for path in files:
        print(f"Cargando {path.name}...")
        df = pd.read_csv(path, low_memory=False)
        df["_archivo_origen"] = path.name
        dfs.append(df)
        print(f"  {len(df)} filas, {len(df.columns)} columnas")

    combined = pd.concat(dfs, ignore_index=True)
    elapsed = time.time() - t0

    log_path = LOGS_DIR / "acquisition_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Archivos procesados: {len(files)}\n")
        f.write(f"Filas totales (antes de deduplicar por ocid): {len(combined)}\n")
        f.write(f"Columnas: {list(combined.columns)}\n")
        f.write(f"Tiempo de carga: {elapsed:.1f}s\n")

    print(f"\nTotal combinado: {len(combined)} filas en {elapsed:.1f}s")
    print(f"Columnas detectadas: {list(combined.columns)[:15]}"
          f"{'...' if len(combined.columns) > 15 else ''}")
    print(f"Log guardado en: {log_path}")

    out_path = PROCESSED_DIR / "oece_raw_combined.csv"
    combined.to_csv(out_path, index=False)
    print(f"Combinado guardado en: {out_path}")
    return combined


def main():
    files = check_files()
    if not files:
        print("\nNo hay archivos para procesar. Descarga al menos 1 mes primero.")
        sys.exit(1)
    load_and_combine(files)


if __name__ == "__main__":
    main()
