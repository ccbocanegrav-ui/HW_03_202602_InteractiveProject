"""
compare_embeddings.py — Fase 4, Task 1: comparación de embeddings (Phase 4, mandatorio)

Construye 2 indices con exactamente los mismos chunks (uno por
backend: local y api) y compara: Recall@k, tiempo de indexacion,
costo, latencia promedio de consulta, y dimension del vector.

SUSTITUCION DOCUMENTADA: el enunciado pide comparar contra
text-embedding-3-small (OpenAI), pero eso requiere creditos de pago
no disponibles. Se compara contra text-embedding-004 (Gemini) en su
lugar — mismo patron de comparacion (local vs. API en la nube), ver
DECISIONES.md.

Uso:
    python eval/compare_embeddings.py
"""

import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import build_index  # noqa: E402
from embeddings import get_embedding_backend  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
EVAL_PATH = BASE_DIR / "eval" / "preguntas.csv"
LOGS_DIR = BASE_DIR / "logs"


def load_eval_set():
    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        return [q for q in csv.DictReader(f) if q["tipo"] == "in_domain"]


def doc_hit_at_k(sources, expected_doc, k):
    if not expected_doc:
        return False
    return any(s["documento"] == expected_doc for s in sources[:k])


def retrieve_with_backend(question, backend, collection, top_k=5):
    qvec = list(map(float, backend.encode_queries([question])[0]))
    results = collection.query(query_embeddings=[qvec], n_results=top_k)
    sources = []
    for doc_text, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
        sources.append({"documento": meta["documento"], "pagina": meta["pagina"], "similarity": 1 - dist})
    return sources


def evaluate_backend(which: str, config: dict, questions: list[dict]) -> dict:
    import chromadb

    print(f"\n--- Backend: {which} ---")
    t0 = time.time()
    build_index.build_index(config, which)
    indexing_time = time.time() - t0

    backend = get_embedding_backend(config, which=which)

    index_dir = BASE_DIR / config["paths"]["index_dir"]
    client = chromadb.PersistentClient(path=str(index_dir))
    collection_name = f"{config['vector_store']['collection_name']}_{which}"
    collection = client.get_collection(collection_name)

    hits = {1: 0, 3: 0, 5: 0}
    latencies = []
    for q in questions:
        t0 = time.time()
        sources = retrieve_with_backend(q["pregunta"], backend, collection, top_k=5)
        latencies.append((time.time() - t0) * 1000)
        for k in (1, 3, 5):
            if doc_hit_at_k(sources, q["documento_esperado"], k):
                hits[k] += 1

    n = len(questions)
    return {
        "backend": which,
        "model": backend.name,
        "dimension": backend.dimension,
        "indexing_time_s": round(indexing_time, 1),
        "avg_query_latency_ms": round(sum(latencies) / len(latencies), 1),
        "recall@1": round(hits[1] / n, 4),
        "recall@3": round(hits[3] / n, 4),
        "recall@5": round(hits[5] / n, 4),
        "cost_usd": 0.0,  # ambos backends son gratuitos en este proyecto (local: sin costo; Gemini: nivel free)
    }


def main():
    config = build_index.load_config()
    questions = load_eval_set()
    print(f"Comparando embeddings con {len(questions)} preguntas in-domain...")

    results = [
        evaluate_backend("local", config, questions),
        evaluate_backend("api", config, questions),
    ]

    print("\n=== COMPARACION DE EMBEDDINGS (Fase 4) ===\n")
    header = f"{'backend':<8}{'modelo':<28}{'dim':<6}{'idx_time(s)':<13}{'latencia(ms)':<14}{'R@1':<8}{'R@3':<8}{'R@5':<8}{'costo':<8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r['backend']:<8}{r['model']:<28}{r['dimension']:<6}{r['indexing_time_s']:<13}"
              f"{r['avg_query_latency_ms']:<14}{r['recall@1']:<8}{r['recall@3']:<8}{r['recall@5']:<8}"
              f"${r['cost_usd']:<7}")

    out_path = LOGS_DIR / "embeddings_comparison.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"\nGuardado en: {out_path}")


if __name__ == "__main__":
    main()
