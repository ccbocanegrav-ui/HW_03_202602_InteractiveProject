"""
source_check.py — Fase 1 / Phase 1, Task 1

Verifica, ANTES de construir cualquier pipeline, que cada PDF obligatorio
sea legible: numero de paginas, caracteres por pagina, paginas sin texto
extraible, y si el texto sale en el orden correcto.

Uso:
    python src/source_check.py

Salida:
    - Imprime una tabla resumen en consola
    - Escribe logs/source_check.csv
    - Escribe logs/source_check_samples.txt (muestra de texto de cada doc,
      para verificar visualmente el orden de lectura)

Documentos esperados en data/raw/ (nombres configurables abajo en DOCS):
    - ley_32069.pdf
    - ds_001_2026_ef.pdf
"""

import csv
import sys
from pathlib import Path

import pdfplumber

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Documento -> (archivo esperado, fuente oficial, fecha de descarga)
DOCS = {
    "ley_32069": {
        "filename": "ley_32069.pdf",
        "fuente": "https://www.gob.pe/institucion/osce/colecciones/45029-ley-n-32069-ley-general-de-contrataciones-publicas",
        "fecha_descarga": "",  # completar al descargar
    },
    "ds_001_2026_ef": {
        "filename": "ds_001_2026_ef.pdf",
        "fuente": "https://busquedas.elperuano.pe/dispositivo/NL/2474920-3",
        "fecha_descarga": "",  # completar al descargar
    },
}

MIN_CHARS_PARA_CONSIDERAR_VACIA = 20  # pagina con menos de esto = "sin texto util"


def check_pdf(doc_id: str, meta: dict) -> dict:
    path = RAW_DIR / meta["filename"]
    result = {
        "doc_id": doc_id,
        "archivo": meta["filename"],
        "fuente": meta["fuente"],
        "fecha_descarga": meta["fecha_descarga"],
        "existe": path.exists(),
        "num_paginas": None,
        "chars_totales": None,
        "chars_promedio_pagina": None,
        "paginas_sin_texto": None,
        "porcentaje_paginas_vacias": None,
        "usable": False,
        "nota": "",
    }

    if not path.exists():
        result["nota"] = "ARCHIVO NO ENCONTRADO en data/raw/ — descargar manualmente."
        return result

    try:
        with pdfplumber.open(path) as pdf:
            n_pages = len(pdf.pages)
            char_counts = []
            empty_pages = []
            sample_text = None

            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                char_counts.append(len(text))
                if len(text.strip()) < MIN_CHARS_PARA_CONSIDERAR_VACIA:
                    empty_pages.append(i + 1)
                if i == n_pages // 2 and sample_text is None:
                    sample_text = text  # muestra de la pagina del medio

            total_chars = sum(char_counts)
            avg_chars = total_chars / n_pages if n_pages else 0

            result.update({
                "num_paginas": n_pages,
                "chars_totales": total_chars,
                "chars_promedio_pagina": round(avg_chars, 1),
                "paginas_sin_texto": len(empty_pages),
                "porcentaje_paginas_vacias": round(100 * len(empty_pages) / n_pages, 1) if n_pages else 0,
                "usable": avg_chars > MIN_CHARS_PARA_CONSIDERAR_VACIA and len(empty_pages) < n_pages,
            })

            # Guardar muestra para revisión visual del orden de lectura
            sample_path = LOGS_DIR / f"sample_{doc_id}.txt"
            sample_path.write_text(sample_text or "(sin texto extraido)", encoding="utf-8")

            if empty_pages:
                result["nota"] = f"Paginas sin texto util: {empty_pages}"

    except Exception as e:
        result["nota"] = f"ERROR al procesar: {e}"

    return result


def main():
    rows = [check_pdf(doc_id, meta) for doc_id, meta in DOCS.items()]

    # CSV
    csv_path = LOGS_DIR / "source_check.csv"
    fieldnames = list(rows[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Tabla en consola
    print("\n=== SOURCE CHECK — Task 1, Phase 1 ===\n")
    header = f"{'doc_id':<18}{'existe':<8}{'paginas':<9}{'chars/pag':<11}{'pag.vacias':<12}{'usable':<8}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['doc_id']:<18}"
            f"{str(r['existe']):<8}"
            f"{str(r['num_paginas']):<9}"
            f"{str(r['chars_promedio_pagina']):<11}"
            f"{str(r['paginas_sin_texto']):<12}"
            f"{str(r['usable']):<8}"
        )
        if r["nota"]:
            print(f"   nota: {r['nota']}")
    print(f"\nCSV guardado en: {csv_path}")
    print("Revisa logs/sample_<doc_id>.txt para verificar el orden de lectura visualmente.\n")

    faltantes = [r for r in rows if not r["existe"]]
    if faltantes:
        print("ACCION REQUERIDA: descarga los PDFs faltantes en data/raw/ y vuelve a correr este script.")
        sys.exit(1)


if __name__ == "__main__":
    main()
