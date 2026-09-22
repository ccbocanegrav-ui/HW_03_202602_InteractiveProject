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

HALLAZGO Y DECISION DE DISEÑO — orden de lectura en layout a 2 columnas:
El DS 001-2026-EF (como el diario El Peruano en general) usa layout a
2 columnas. pdfplumber, con extract_text() por defecto, ordena las
palabras por posicion vertical SIN respetar columnas, por lo que mezcla
lineas de la columna izquierda con lineas de la columna derecha.

Solucion: por cada pagina, (1) se separa una franja superior delgada
(el encabezado del diario, que ocupa todo el ancho) y se extrae aparte;
(2) en el resto de la pagina se detecta si existe una "calle" vertical
vacia cerca del centro (pocas palabras cruzan esa banda) — si existe,
es layout a 2 columnas: se extrae la columna izquierda completa de
arriba a abajo, luego la columna derecha completa, y se concatenan en
ese orden. Si no hay esa calle vacia (ej. Ley 32069, que es a 1
columna), se extrae la pagina normal sin dividir nada.

Uso:
    python src/extract.py

Salida (por documento, en data/processed/):
    <doc_id>_raw.jsonl   — una linea por pagina: {"doc", "page", "text", "date_extracted"}
"""

import json
from datetime import date
from pathlib import Path

import pdfplumber

HEADER_BAND_RATIO = 0.06   # % del alto de pagina reservado para el encabezado del diario
CENTER_BAND_RATIO = 0.04   # % del ancho de pagina considerado "cerca del centro"
MIN_CROSSING_RATIO = 0.03  # si menos de este % de palabras cruzan el centro -> es 2 columnas


def extract_page_text_ordered(page) -> str:
    """Extrae el texto de una pagina respetando el orden de lectura real,
    incluso si la pagina tiene layout a 2 columnas."""
    width, height = page.width, page.height
    header_h = height * HEADER_BAND_RATIO

    header_text = (page.crop((0, 0, width, header_h)).extract_text() or "").strip()
    body = page.crop((0, header_h, width, height))

    words = body.extract_words()
    if not words:
        return (header_text + "\n" + (body.extract_text() or "")).strip()

    mid_x = width / 2
    band = width * CENTER_BAND_RATIO
    crossing = [w for w in words if mid_x - band <= (w["x0"] + w["x1"]) / 2 <= mid_x + band]
    crossing_ratio = len(crossing) / len(words)

    if crossing_ratio < MIN_CROSSING_RATIO:
        # Layout a 2 columnas: extraer izquierda completa, luego derecha completa.
        left = body.crop((0, header_h, mid_x, height))
        right = body.crop((mid_x, header_h, width, height))
        body_text = (left.extract_text() or "").strip() + "\n" + (right.extract_text() or "").strip()
    else:
        # 1 columna: extraer normal, sin dividir.
        body_text = (body.extract_text() or "").strip()

    return (header_text + "\n" + body_text).strip()

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
            text = extract_page_text_ordered(page)
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
