"""
build_index.py — Fase 2, Task 1: Chunking, Embeddings e Index (Phase 2)

Este es el PROCESO OFFLINE: lee los chunks (Fase 2), calcula embeddings
(local por defecto) y los guarda en ChromaDB, persistido en disco.
El proceso ONLINE (el motor de Fase 3) solo LEE este índice — nunca
vuelve a leer los PDFs ni a llamar al modelo de embeddings sobre el
corpus completo.

IDEMPOTENCIA: se usa collection.upsert() con el id determinista de
cada chunk ({doc}_p{pagina}_c{indice}, definido en chunk.py). Correr
este script 2 veces sobre el mismo corpus NO duplica nada: el segundo
upsert simplemente sobreescribe los mismos IDs con el mismo contenido.
Agregar un documento nuevo tampoco pisa los IDs de otro, porque cada
ID incluye su propio doc_id.

Uso:
    python src/build_index.py                 # embeddings locales (default, config.yaml)
    python src/build_index.py --backend api    # embeddings via OpenAI (Fase 4, comparacion)
"""

import argparse
import json
import sys
import time
from pathlib import Path

import chromadb
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embeddings import get_embedding_backend  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_chunks(processed_dir: Path, doc_ids: list[str]) -> list[dict]:
    chunks = []
    for doc_id in doc_ids:
        path = processed_dir / f"{doc_id}_chunks.jsonl"
        if not path.exists():
            print(f"[SKIP] {doc_id}: falta {path.name} (corre chunk.py --build primero)")
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                chunks.append(json.loads(line))
    return chunks


def build_index(config: dict, backend_name: str):
    processed_dir = BASE_DIR / config["paths"]["processed_dir"]
    index_dir = BASE_DIR / config["paths"]["index_dir"]
    index_dir.mkdir(parents=True, exist_ok=True)

    doc_ids = [d["id"] for d in config["documents"]]
    chunks = load_all_chunks(processed_dir, doc_ids)
    if not chunks:
        print("No hay chunks para indexar. Corre extract.py, clean.py y chunk.py --build primero.")
        return

    print(f"Cargando modelo de embeddings ({backend_name})...")
    t0 = time.time()
    backend = get_embedding_backend(config, which=backend_name)
    print(f"Modelo listo en {time.time()-t0:.1f}s | dimension: {backend.dimension} | nombre: {backend.name}")

    # Un vector store distinto por backend, para poder compararlos en Fase 4
    # sin que se pisen entre si.
    collection_name = f"{config['vector_store']['collection_name']}_{backend_name}"
    client = chromadb.PersistentClient(path=str(index_dir))
    # hnsw:space="cosine" es OBLIGATORIO aqui: sin esto, ChromaDB usa
    # distancia euclidiana (l2) por defecto, y el threshold de Fase 3
    # (calibrado en escala de similitud coseno 0-1) dejaria de tener
    # sentido.
    collection = client.get_or_create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"}
    )

    BATCH = 64
    t0 = time.time()
    n_indexed = 0
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadatas = [
            {"documento": c["documento"], "pagina": c["pagina"], "version": c["version"]}
            for c in batch
        ]
        embeddings = backend.encode_passages(texts)
        # chromadb necesita listas planas de floats, no arrays numpy
        embeddings = [list(map(float, e)) for e in embeddings]

        collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        n_indexed += len(batch)
        print(f"  indexados {n_indexed}/{len(chunks)}...", end="\r")

    elapsed = time.time() - t0
    print(f"\n[OK] {n_indexed} chunks indexados en '{collection_name}' ({elapsed:.1f}s, "
          f"{n_indexed/elapsed:.1f} chunks/s)")
    print(f"Indice persistido en: {index_dir}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=["local", "api"], default="local")
    args = parser.parse_args()

    config = load_config()
    build_index(config, args.backend)


if __name__ == "__main__":
    main()
