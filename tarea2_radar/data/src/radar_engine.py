"""
radar_engine.py — Task 2, Phase 3: motor RAG hibrido

ARQUITECTURA: igual que Task 1 — una funcion, answer_question(), que
el dashboard de Streamlit (Fase 4) llama. Nunca reconstruye el indice.

DECISION HIBRIDA: preguntas como "obras de agua en Cusco mayores a 1M"
combinan 2 tipos de condicion. "Cusco" y "> 1M" son FILTROS
ESTRUCTURADOS (se aplican como where-clause de ChromaDB sobre la
metadata), no texto para el embedding — un embedding no entiende
numeros ("mayor a 1 millon" no tiene una representacion vectorial
confiable de la comparacion numerica). Solo la parte descriptiva
("obras de agua") pasa por busqueda semantica.

Uso:
    from radar_engine import answer_question, load_config
    config = load_config()
    result = answer_question(
        "obras de agua potable",
        config,
        filters={"department": "CUSCO", "min_amount": 1_000_000},
    )
"""

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import chromadb
import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embeddings import get_embedding_backend  # noqa: E402
from generation import get_generation_backend  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"

_ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)
if not _ENV_PATH.exists():
    load_dotenv(dotenv_path=BASE_DIR / ".env")

PRICING_USD_PER_1M_TOKENS = {
    "command-r-08-2024": {"input": 0.0, "output": 0.0, "verified_on": "2026-09-24"},
}

_backend_cache = {}


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_backend(config: dict):
    if "local" not in _backend_cache:
        _backend_cache["local"] = get_embedding_backend(config, which="local")
    return _backend_cache["local"]


def _get_collection(config: dict):
    index_dir = BASE_DIR / config["paths"]["index_dir"]
    client = chromadb.PersistentClient(path=str(index_dir))
    return client.get_collection(config["vector_store"]["collection_name"])


def _build_where(filters: dict) -> dict | None:
    """Traduce los filtros del dashboard a un where-clause de ChromaDB."""
    if not filters:
        return None
    clauses = []
    if filters.get("department"):
        clauses.append({"department": filters["department"]})
    if filters.get("category"):
        clauses.append({"category": filters["category"]})
    if filters.get("min_amount") is not None:
        clauses.append({"amount": {"$gte": float(filters["min_amount"])}})
    if filters.get("max_amount") is not None:
        clauses.append({"amount": {"$lte": float(filters["max_amount"])}})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def retrieve(question: str, config: dict, filters: dict = None, top_k: int = None) -> list[dict]:
    backend = _get_backend(config)
    collection = _get_collection(config)
    top_k = top_k or config["retrieval"]["top_k"]
    where = _build_where(filters or {})

    qvec = list(map(float, backend.encode_queries([question])[0]))
    kwargs = {"query_embeddings": [qvec], "n_results": top_k}
    if where:
        kwargs["where"] = where
    results = collection.query(**kwargs)

    sources = []
    if results["ids"] and results["ids"][0]:
        for doc_text, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
            sources.append({
                "ocid": meta["ocid"], "department": meta["department"], "amount": meta["amount"],
                "buyer": meta["buyer"], "category": meta["category"], "similarity": round(1 - dist, 4),
                "text": doc_text,
            })
    return sources


def _compute_cost(model, tokens_in, tokens_out):
    p = PRICING_USD_PER_1M_TOKENS.get(model)
    if not p:
        return 0.0
    return (tokens_in / 1_000_000) * p["input"] + (tokens_out / 1_000_000) * p["output"]


def _log_cost(config, model, tokens_in, tokens_out, cost, latency_ms, success):
    log_path = BASE_DIR / config["costs"]["log_file"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["timestamp", "model", "tokens_in", "tokens_out", "cost_usd", "latency_ms", "success"])
        w.writerow([datetime.now(timezone.utc).isoformat(), model, tokens_in, tokens_out,
                    round(cost, 6), round(latency_ms, 1), success])


def answer_question(question: str, config: dict = None, filters: dict = None, top_k: int = None) -> dict:
    config = config or load_config()
    result = {"answer": None, "sources": [], "abstained": False,
              "tokens": {"input": 0, "output": 0}, "cost_usd": 0.0, "error": None}

    try:
        sources = retrieve(question, config, filters=filters, top_k=top_k)
    except Exception as e:
        result["error"] = f"Error en retrieval: {e}"
        return result

    result["sources"] = sources
    threshold = config["retrieval"]["similarity_threshold"]
    best_sim = sources[0]["similarity"] if sources else 0.0

    if not sources or best_sim < threshold:
        result["abstained"] = True
        result["answer"] = ("No encuentro procesos que respondan esta pregunta con los filtros aplicados. "
                             "Prueba ampliando el rango de fechas/monto o quitando algún filtro.")
        return result

    context = "\n\n".join(
        f"[ocid: {s['ocid']} | {s['department']} | S/ {s['amount']:,.0f} | {s['buyer']}]\n{s['text']}"
        for s in sources
    )
    gen_cfg = config["generation"]
    model = gen_cfg["model_name"]
    user_prompt = f"Procesos:\n{context}\n\nPregunta: {question}"

    try:
        backend = get_generation_backend(config)
        t0 = time.time()
        gen_result = backend.generate(gen_cfg["system_prompt"], user_prompt, gen_cfg["max_output_tokens"])
        latency_ms = (time.time() - t0) * 1000

        result["answer"] = gen_result["text"]
        result["tokens"] = {"input": gen_result["tokens_in"], "output": gen_result["tokens_out"]}
        result["cost_usd"] = _compute_cost(model, gen_result["tokens_in"], gen_result["tokens_out"])
        _log_cost(config, model, gen_result["tokens_in"], gen_result["tokens_out"], result["cost_usd"], latency_ms, True)
    except Exception as e:
        result["error"] = f"Error al generar respuesta: {e}"
        _log_cost(config, model, 0, 0, 0.0, 0.0, False)

    return result
