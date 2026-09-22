"""
chunk.py — Fase 2, Task 1: Chunking, Phase 2

DECISIONES DE DISEÑO (documentadas, ver DECISIONES.md):

1. Se hace chunking POR PAGINA, nunca concatenando todo el documento
   primero. Motivo: si concatenas todo y luego divides, un chunk puede
   nacer a mitad de una pagina y terminar en la siguiente, y ya no
   puedes decir con certeza de que pagina vino. Aqui cada chunk nace
   atado a exactamente 1 pagina.

2. El split respeta limites de palabra (nunca corta una palabra a la
   mitad), usando una ventana deslizante sobre las palabras de la
   pagina, con overlap opcional.

3. El ID de cada fragmento es determinista: {doc_id}_p{pagina}_c{indice}.
   Esto garantiza:
   - IDEMPOTENCIA: correr el script 2 veces no duplica nada (mismo
     texto de entrada -> mismos IDs de salida, se sobreescriben).
   - Unicidad entre documentos: el doc_id siempre esta en el ID.
   - Agregar un documento nuevo nunca pisa ni corre los IDs de otro,
     porque cada ID solo depende de su propio doc_id + pagina + indice,
     nunca de un contador global.

4. Antes de fijar un tamaño de chunk "final", se corre un SWEEP
   (100/200/300/500 caracteres, con y sin overlap del 20%) y se reporta
   fragmentos y longitudes resultantes -> chunking_sweep.csv. El tamaño
   definitivo se valida con Recall@k contra el set de evaluacion en la
   Fase 4 (ver nota en DECISIONES.md); por ahora se elige el que de
   fragmentos de longitud mas pareja y sin demasiados fragmentos
   minusculos (ruido) ni demasiado grandes (pierden precision de cita).

Uso:
    python src/chunk.py            # corre el sweep y reporta
    python src/chunk.py --build    # ademas construye data/processed/<doc>_chunks.jsonl
                                      con el tamaño elegido en CHOSEN_SIZE/CHOSEN_OVERLAP
"""

import csv
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

DOCS = ["ley_32069", "ds_001_2026_ef"]

SWEEP_SIZES = [100, 200, 300, 500]      # caracteres objetivo por chunk
SWEEP_OVERLAPS = [0.0, 0.2]              # 0% y 20% de overlap

# Tamaño elegido para construir el indice real (Fase 3+). Se puede
# ajustar despues de ver chunking_sweep.csv y, mas adelante, el
# Recall@k de la Fase 4.
CHOSEN_SIZE = 300
CHOSEN_OVERLAP = 0.2


MIN_CHUNK_RATIO = 0.3  # un chunk final menor a 30% del tamaño objetivo se fusiona con el anterior


def chunk_words(words: list[str], target_chars: int, overlap_ratio: float) -> list[str]:
    """Ventana deslizante sobre palabras, respetando limites de palabra.

    El ultimo fragmento de una pagina, si queda muy chico (menos del
    MIN_CHUNK_RATIO del tamaño objetivo), se fusiona con el fragmento
    anterior en vez de quedar como un chunk minusculo casi vacio
    (ruido que no aporta nada util al embedding)."""
    if not words:
        return []

    chunks = []
    start = 0
    n = len(words)

    while start < n:
        current = []
        current_len = 0
        i = start
        while i < n and current_len < target_chars:
            current.append(words[i])
            current_len += len(words[i]) + 1  # +1 por el espacio
            i += 1

        chunk_text_str = " ".join(current)
        chunks.append(chunk_text_str)

        if i >= n:
            break

        # overlap: retrocedemos una fraccion de las palabras ya usadas
        overlap_words = max(1, int(len(current) * overlap_ratio)) if overlap_ratio > 0 else 0
        start = i - overlap_words if overlap_ratio > 0 else i

    # Fusionar el ultimo chunk si quedo demasiado chico
    if len(chunks) >= 2 and len(chunks[-1]) < target_chars * MIN_CHUNK_RATIO:
        chunks[-2] = chunks[-2] + " " + chunks[-1]
        chunks.pop()

    return chunks


def load_pages(doc_id: str) -> list[dict]:
    path = PROCESSED_DIR / f"{doc_id}_clean.jsonl"
    if not path.exists():
        print(f"[SKIP] {doc_id}: falta {path.name} (corre clean.py primero)")
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def run_sweep():
    rows = []
    for doc_id in DOCS:
        pages = load_pages(doc_id)
        if not pages:
            continue
        for size in SWEEP_SIZES:
            for overlap in SWEEP_OVERLAPS:
                all_chunks = []
                for page in pages:
                    words = page["text"].split()
                    all_chunks.extend(chunk_words(words, size, overlap))
                lengths = [len(c) for c in all_chunks] or [0]
                rows.append({
                    "doc_id": doc_id,
                    "target_size": size,
                    "overlap": overlap,
                    "n_chunks": len(all_chunks),
                    "avg_len": round(sum(lengths) / len(lengths), 1),
                    "min_len": min(lengths),
                    "max_len": max(lengths),
                })

    csv_path = LOGS_DIR / "chunking_sweep.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("\n=== CHUNKING SWEEP — Fase 2 ===\n")
    header = f"{'doc_id':<18}{'size':<7}{'overlap':<9}{'n_chunks':<10}{'avg_len':<9}{'min':<6}{'max':<6}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['doc_id']:<18}{r['target_size']:<7}{r['overlap']:<9}{r['n_chunks']:<10}"
              f"{r['avg_len']:<9}{r['min_len']:<6}{r['max_len']:<6}")
    print(f"\nCSV guardado en: {csv_path}\n")


def build_chunks():
    for doc_id in DOCS:
        pages = load_pages(doc_id)
        if not pages:
            continue

        records = []
        for page in pages:
            words = page["text"].split()
            page_chunks = chunk_words(words, CHOSEN_SIZE, CHOSEN_OVERLAP)
            for idx, chunk_text_str in enumerate(page_chunks):
                records.append({
                    "id": f"{doc_id}_p{page['page']}_c{idx}",
                    "documento": doc_id,
                    "version": page.get("date_extracted", ""),
                    "pagina": page["page"],
                    "text": chunk_text_str,
                    "n_chars": len(chunk_text_str),
                })

        out_path = PROCESSED_DIR / f"{doc_id}_chunks.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        print(f"[OK] {doc_id}: {len(records)} chunks -> {out_path} "
              f"(size={CHOSEN_SIZE}, overlap={CHOSEN_OVERLAP})")


def main():
    run_sweep()
    if "--build" in sys.argv:
        print("\n=== Construyendo chunks finales ===\n")
        build_chunks()


if __name__ == "__main__":
    main()
