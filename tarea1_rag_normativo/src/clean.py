"""
clean.py — Fase 1 / Phase 1, Task 1

Limpia el encabezado de pagina que El Peruano pega al inicio del texto
(numero de pagina, seccion "NORMAS LEGALES", fecha, "El Peruano /").

REGLA DOCUMENTADA:
Se detecta y elimina la PRIMERA linea de cada pagina si esa linea
contiene simultaneamente "El Peruano" y "NORMAS LEGALES" (con o sin un
numero de pagina pegado). Solo se toca la primera linea de cada pagina:
nunca se borra texto de en medio de un articulo, porque el encabezado
del diario SIEMPRE aparece como la primera linea extraida de la pagina
(nunca en medio de un parrafo).

Documentos que no tengan ese patron (por ejemplo si el PDF fue
tipografiado por otra entidad sin el encabezado del diario) simplemente
no sufren ningun cambio: la regla es condicional, no agresiva.

Uso:
    python src/clean.py

Salida:
    data/processed/<doc_id>_clean.jsonl
    logs/extraction_quality_report_<doc_id>.txt   (paginas, chars, antes/despues)
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

DOCS = ["ley_32069", "ds_001_2026_ef"]

# Header de El Peruano: contiene "El Peruano" y "NORMAS LEGALES" en la misma
# linea, en CUALQUIER orden (el diario imprime el encabezado espejado en
# paginas pares vs impares):
#   impares: "El Peruano / Jueves 8 de enero de 2026 NORMAS LEGALES 33"
#   pares:   "34 NORMAS LEGALES Jueves 8 de enero de 2026/ El Peruano"
# Se usa un lookahead doble para que el orden no importe.
HEADER_PATTERN = re.compile(
    r"(?=.*El Peruano)(?=.*NORMAS LEGALES)", re.IGNORECASE
)

MIN_CHARS_UTIL = 20


def clean_page_text(text: str) -> tuple[str, bool]:
    """Devuelve (texto_limpio, se_removio_header)."""
    if not text:
        return text, False

    lines = text.split("\n")
    if lines and HEADER_PATTERN.search(lines[0]):
        cleaned = "\n".join(lines[1:]).lstrip("\n")
        return cleaned, True

    return text, False


def process_doc(doc_id: str):
    raw_path = PROCESSED_DIR / f"{doc_id}_raw.jsonl"
    if not raw_path.exists():
        print(f"[SKIP] {doc_id}: corre extract.py primero (no existe {raw_path.name})")
        return None

    clean_path = PROCESSED_DIR / f"{doc_id}_clean.jsonl"
    records_out = []
    pages_with_header = 0
    pages_discarded = []
    total_chars_raw = 0
    total_chars_clean = 0
    before_after_example = None

    with open(raw_path, "r", encoding="utf-8") as f:
        raw_records = [json.loads(line) for line in f]

    for rec in raw_records:
        raw_text = rec["text"]
        clean_text, had_header = clean_page_text(raw_text)

        total_chars_raw += len(raw_text)
        total_chars_clean += len(clean_text)

        if had_header:
            pages_with_header += 1
            if before_after_example is None:
                before_after_example = {
                    "doc": doc_id,
                    "page": rec["page"],
                    "antes": raw_text[:300],
                    "despues": clean_text[:300],
                }

        if len(clean_text.strip()) < MIN_CHARS_UTIL:
            pages_discarded.append(rec["page"])

        records_out.append({
            "doc": rec["doc"],
            "page": rec["page"],
            "text": clean_text,
            "date_extracted": rec["date_extracted"],
        })

    with open(clean_path, "w", encoding="utf-8") as out:
        for rec in records_out:
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Reporte de calidad de extraccion
    report_path = LOGS_DIR / f"extraction_quality_report_{doc_id}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"REPORTE DE CALIDAD DE EXTRACCION — {doc_id}\n")
        f.write("=" * 60 + "\n")
        f.write(f"Paginas totales: {len(raw_records)}\n")
        f.write(f"Caracteres totales (antes de limpiar): {total_chars_raw}\n")
        f.write(f"Caracteres totales (despues de limpiar): {total_chars_clean}\n")
        f.write(f"Caracteres removidos por limpieza: {total_chars_raw - total_chars_clean}\n")
        f.write(f"Paginas con encabezado de El Peruano detectado y removido: {pages_with_header}\n")
        f.write(f"Paginas descartadas (menos de {MIN_CHARS_UTIL} chars utiles): {pages_discarded}\n")
        f.write("\n" + "-" * 60 + "\n")
        if before_after_example:
            f.write(f"EJEMPLO ANTES / DESPUES (pagina {before_after_example['page']})\n\n")
            f.write("ANTES:\n")
            f.write(before_after_example["antes"] + "\n\n")
            f.write("DESPUES:\n")
            f.write(before_after_example["despues"] + "\n")
        else:
            f.write("No se detecto el patron de encabezado de El Peruano en ninguna "
                    "pagina de este documento (el PDF no lo trae pegado al texto).\n")

        # Muestra de la pagina del medio, ya limpia
        mid = records_out[len(records_out) // 2]
        f.write("\n" + "-" * 60 + "\n")
        f.write(f"MUESTRA DE TEXTO LIMPIO — pagina {mid['page']} (pagina del medio)\n\n")
        f.write(mid["text"][:800])

    print(f"[OK] {doc_id}: {pages_with_header}/{len(raw_records)} paginas con header removido")
    print(f"     Reporte: {report_path}")
    return {
        "doc_id": doc_id,
        "pages_with_header": pages_with_header,
        "total_pages": len(raw_records),
        "pages_discarded": pages_discarded,
    }


def main():
    print("\n=== CLEAN — Task 1, Phase 1 ===\n")
    for doc_id in DOCS:
        process_doc(doc_id)
    print("\nListo. Revisa logs/extraction_quality_report_<doc_id>.txt para cada documento.\n")


if __name__ == "__main__":
    main()
