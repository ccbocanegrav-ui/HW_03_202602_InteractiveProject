"""
load_data.py — Task 2, Phase 1: Data Acquisition

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

Uso:
    python src/load_data.py
"""

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


def main():
    files = check_files()
    if not files:
        print("\nNo hay archivos para procesar. Descarga al menos 1 mes primero.")
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
