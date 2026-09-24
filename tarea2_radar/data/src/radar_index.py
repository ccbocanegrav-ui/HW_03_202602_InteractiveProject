"""
radar_index.py — Task 2, Phase 3: construye el indice hibrido.

Indexa la DESCRIPCION de cada proceso (busqueda semantica) y guarda
department/amount/date/category/buyer/ocid como METADATA (filtros
estructurados, no semanticos — ver DECISIONES.md sobre por que
"monto > 1M" nunca debe ir al embedding).

Uso:
    python src/radar_index.py
"""

import sys
from pathlib import Path

import chromadb
import pandas as pd
import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
from embeddings import get_embedding_backend  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"

_ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)
if not _ENV_PATH.exists():
    load_dotenv(dotenv_path=BASE_DIR / ".env")


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    processed_dir = BASE_DIR / config["paths"]["processed_dir"]
    index_dir = BASE_DIR / config["paths"]["index_dir"]
    index_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(processed_dir / "oece_clean.csv", low_memory=False)
    print(f"Indexando {len(df)} procesos...")

    backend = get_embedding_backend(config, which="local")
    client = chromadb.PersistentClient(path=str(index_dir))
    collection = client.get_or_create_collection(
        name=config["vector_store"]["collection_name"], metadata={"hnsw:space": "cosine"},
    )

    BATCH = 64
    for i in range(0, len(df), BATCH):
        batch = df.iloc[i : i + BATCH]
        texts = batch["description"].astype(str).tolist()
        ids = batch["ocid"].astype(str).tolist()
        metadatas = [
            {
                "ocid": str(row["ocid"]),
                "department": str(row.get("department_normalizado") or ""),
                "amount": float(row["amount"]) if pd.notna(row["amount"]) else 0.0,
                "buyer": str(row.get("buyer") or ""),
                "category": str(row.get("category") or ""),
                "date": str(row.get("date") or ""),
            }
            for _, row in batch.iterrows()
        ]
        embeddings = [list(map(float, e)) for e in backend.encode_passages(texts)]
        collection.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        print(f"  indexados {min(i+BATCH, len(df))}/{len(df)}...", end="\r")

    print(f"\n[OK] {len(df)} procesos indexados en '{config['vector_store']['collection_name']}'")


if __name__ == "__main__":
    main()
