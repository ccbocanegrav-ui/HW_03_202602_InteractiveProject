"""
extract.py — Fase 1 / Phase 1, Task 1

Extrae texto de cada PDF, conservando el numero de pagina desde el
PRIMER paso (requisito del enunciado: nunca unir todo el documento en un
solo string y luego intentar recuperar la pagina).

Por que no unir todo primero: si concatenas todo el texto en un solo
string y luego divides en chunks, pierdes la frontera de pagina exacta
(un chunk puede empezar a mitad de una pagina y terminar a mitad de
otra), y ya no puedes reconstruir con certeza de que pagina vino cada
fragmento. Aqui cada registro nace atado a su pagina.

Uso:
    python src/extract.py

Salida (por documento, en data/processed/):
    <doc_id>_raw.jsonl   — una linea por pagina: {"doc", "page", "text", "date_extracted"}
"""

import json
from datetime import date
from pathlib import Path

import pdfplumber

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

DOCS = {
    "ley_32069": "ley_32069.pdf",
    "ds_001_2026_ef": "ds_001_2026_ef.pdf",
}

TODAY = date.today().isoformat()


def extract_doc(doc_id: str, filename: str) -> int:
    path = RAW_DIR / filename
    if not path.exists():
        print(f"[SKIP] {doc_id}: no encontrado en data/raw/")
        return 0

    out_path = PROCESSED_DIR / f"{doc_id}_raw.jsonl"
    n_written = 0
    with pdfplumber.open(path) as pdf, open(out_path, "w", encoding="utf-8") as out:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            record = {
                "doc": doc_id,
                "page": i + 1,
                "text": text,
                "date_extracted": TODAY,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            n_written += 1

    print(f"[OK] {doc_id}: {n_written} paginas -> {out_path}")
    return n_written


def main():
    total = 0
    for doc_id, filename in DOCS.items():
        total += extract_doc(doc_id, filename)
    print(f"\nTotal de paginas extraidas: {total}")


if __name__ == "__main__":
    main()
