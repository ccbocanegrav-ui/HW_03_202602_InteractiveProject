"""
engine.py — Fase 3, Task 1: RAG Engine (Phase 3)

ARQUITECTURA (requisito del enunciado):
- Este modulo NO importa streamlit, telegram, ni ninguna libreria de UI.
  Verificable con: grep -E "^import|^from" src/engine.py que no
  contenga streamlit ni telegram.
- Expone UNA funcion, `answer_question()`, que recibe una pregunta y
  devuelve un resultado ESTRUCTURADO. La app de Streamlit (Fase 5) y
  cualquier otra interfaz (ej. un bot de Telegram) solo llaman a esta
  funcion — nunca hablan directo con ChromaDB ni con la API del LLM.
- El proceso ONLINE (este modulo) nunca reconstruye el indice ni vuelve
  a leer los PDFs: solo lee el indice ya construido por build_index.py.

DECISION DE THRESHOLD (Phase 3): si la similitud del mejor fragmento
recuperado es menor al umbral configurado, el engine se ABSTIENE sin
llamar al LLM (ahorra costo y evita alucinar con contexto irrelevante).
El valor en config.yaml es PROVISIONAL — se calibra con el sweep de
threshold en Fase 4 contra el set de evaluacion real.

DECISION DE VERSIONES/ALCANCE: cada fragmento recuperado trae su
`documento` (ley_32069 o ds_001_2026_ef) en la metadata. El prompt
instruye al modelo a SIEMPRE indicar de que documento proviene cada
afirmacion, y a decir explicitamente cuando la pregunta cae fuera de
lo indexado (ej. preguntas que solo el Reglamento completo podria
responder) en vez de improvisar con el fragmento mas cercano.

Uso:
    from engine import answer_question, load_config
    config = load_config()
    result = answer_question("¿Cual es el plazo para pagar al contratista?", config)
"""

import csv
import os
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

load_dotenv()  # carga OPENAI_API_KEY / GEMINI_API_KEY desde .env, nunca hardcodeada

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"

# Precios por 1M tokens, verificados el 2026-09-22 en la pagina oficial
# de precios de cada proveedor. IMPORTANTE: actualizar esta fecha y
# estos valores si cambian los precios — nunca asumir que siguen
# vigentes.
PRICING_USD_PER_1M_TOKENS = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "verified_on": "2026-09-22"},
    # Gemini 1.5/2.0 Flash: gratis dentro de la cuota diaria del nivel
    # free de Google AI Studio. Costo 0 mientras no se exceda esa cuota
    # (documentar esto explicitamente en el video/README, no asumir
    # que "gratis" significa "sin limite").
    "gemini-1.5-flash": {"input": 0.0, "output": 0.0, "verified_on": "2026-09-22"},
    "gemini-2.0-flash": {"input": 0.0, "output": 0.0, "verified_on": "2026-09-22"},
    "gemini-3.6-flash": {"input": 0.0, "output": 0.0, "verified_on": "2026-09-22"},
}

_backend_cache = {}  # evita recargar el modelo de embeddings en cada llamada


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_backend(config: dict):
    key = "local"  # el engine SIEMPRE usa el backend local en produccion;
    # la comparacion contra la API es exclusiva de la Fase 4 (script aparte)
    if key not in _backend_cache:
        _backend_cache[key] = get_embedding_backend(config, which=key)
    return _backend_cache[key]


def _get_collection(config: dict):
    index_dir = BASE_DIR / config["paths"]["index_dir"]
    client = chromadb.PersistentClient(path=str(index_dir))
    collection_name = f"{config['vector_store']['collection_name']}_local"
    return client.get_collection(collection_name)


def _log_cost(config: dict, model: str, tokens_in: int, tokens_out: int,
               cost_usd: float, latency_ms: float, success: bool):
    log_path = BASE_DIR / config["costs"]["log_file"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "model", "tokens_in", "tokens_out",
                              "cost_usd", "latency_ms", "success"])
        writer.writerow([datetime.now(timezone.utc).isoformat(), model, tokens_in,
                          tokens_out, round(cost_usd, 6), round(latency_ms, 1), success])


def _compute_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    if model not in PRICING_USD_PER_1M_TOKENS:
        return 0.0
    p = PRICING_USD_PER_1M_TOKENS[model]
    return (tokens_in / 1_000_000) * p["input"] + (tokens_out / 1_000_000) * p["output"]


def retrieve(question: str, config: dict, top_k: int = None) -> list[dict]:
    """Busca los fragmentos mas similares a la pregunta. No llama al LLM."""
    backend = _get_backend(config)
    collection = _get_collection(config)
    top_k = top_k or config["retrieval"]["top_k"]

    qvec = backend.encode_queries([question])[0]
    qvec = list(map(float, qvec))

    results = collection.query(query_embeddings=[qvec], n_results=top_k)

    sources = []
    for doc_text, meta, dist, chunk_id in zip(
        results["documents"][0], results["metadatas"][0],
        results["distances"][0], results["ids"][0],
    ):
        # ChromaDB devuelve distancia (menor = mas similar); se convierte
        # a similitud coseno para que sea comparable con el threshold.
        similarity = 1 - dist
        sources.append({
            "id": chunk_id,
            "documento": meta["documento"],
            "pagina": meta["pagina"],
            "similarity": round(similarity, 4),
            "text": doc_text,
        })
    return sources


def answer_question(question: str, config: dict = None, top_k: int = None) -> dict:
    """FUNCION UNICA que expone el engine. Devuelve SIEMPRE esta forma:
    {
      "answer": str | None,
      "sources": [{"documento", "pagina", "similarity"}, ...],
      "abstained": bool,
      "tokens": {"input": int, "output": int},
      "cost_usd": float,
      "error": str | None,
    }
    """
    config = config or load_config()
    result = {
        "answer": None, "sources": [], "abstained": False,
        "tokens": {"input": 0, "output": 0}, "cost_usd": 0.0, "error": None,
    }

    try:
        sources = retrieve(question, config, top_k=top_k)
    except Exception as e:
        result["error"] = f"Error en retrieval: {e}"
        return result

    result["sources"] = sources
    threshold = config["retrieval"]["similarity_threshold"]
    best_similarity = sources[0]["similarity"] if sources else 0.0

    # DECISION ANTES DE LLAMAR AL LLM (Phase 3): si no hay suficiente
    # similitud, no se gasta en la API.
    if best_similarity < threshold:
        result["abstained"] = True
        result["answer"] = (
            "No encuentro esta informacion en los documentos indexados "
            "(Ley N.º 32069 y Decreto Supremo N.º 001-2026-EF). Puede que "
            "la respuesta este en el Reglamento completo, que no forma "
            "parte de este corpus."
        )
        return result

    context = "\n\n".join(
        f"[Fuente: {s['documento']}, pagina {s['pagina']}]\n{s['text']}"
        for s in sources
    )
    system_prompt = config["generation"]["system_prompt"]
    user_prompt = f"Contexto:\n{context}\n\nPregunta: {question}"

    gen_cfg = config["generation"]
    model = gen_cfg["model_name"]

    try:
        backend = get_generation_backend(config)
        t0 = time.time()
        gen_result = backend.generate(system_prompt, user_prompt, gen_cfg["max_output_tokens"])
        latency_ms = (time.time() - t0) * 1000

        tokens_in = gen_result["tokens_in"]
        tokens_out = gen_result["tokens_out"]
        cost = _compute_cost(model, tokens_in, tokens_out)

        result["answer"] = gen_result["text"]
        result["tokens"] = {"input": tokens_in, "output": tokens_out}
        result["cost_usd"] = cost

        _log_cost(config, model, tokens_in, tokens_out, cost, latency_ms, True)

    except Exception as e:
        # Requisito: los errores de la API se devuelven como error,
        # NUNCA como una respuesta normal.
        result["error"] = f"Error al generar respuesta: {e}"
        _log_cost(config, model, 0, 0, 0.0, 0.0, False)

    return result


if __name__ == "__main__":
    # Prueba rapida desde linea de comandos
    cfg = load_config()
    q = sys.argv[1] if len(sys.argv) > 1 else "¿Cual es el plazo maximo para pagar al contratista?"
    r = answer_question(q, cfg)
    print("PREGUNTA:", q)
    print("ABSTAINED:", r["abstained"])
    print("ANSWER:", r["answer"])
    print("SOURCES:")
    for s in r["sources"]:
        print(f"  - {s['documento']} p.{s['pagina']} (sim={s['similarity']})")
    print("COST:", r["cost_usd"], "| TOKENS:", r["tokens"], "| ERROR:", r["error"])
