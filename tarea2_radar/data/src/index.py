"""
Tarea 2 - Fase 3: índice semántico híbrido.

Lee:
    data/data/processed/procesos.csv

Crea:
    data/data/index/

Cada proceso = un documento/vector.

Los campos estructurados se guardan como metadata para poder aplicar
filtros exactos ANTES de la búsqueda semántica:
    - departamento
    - monto_pen
    - fecha_publicacion
    - categoria
    - comprador
    - ocid
    - procedimiento

El texto utilizado para embedding es principalmente la descripción del
proceso.

IMPORTANTE:
- No usamos embeddings para decidir departamento.
- No usamos embeddings para decidir monto.
- Esas condiciones se aplican como filtros estructurados.
"""

from pathlib import Path
import sys
import time

import chromadb
import pandas as pd
import yaml
from dotenv import load_dotenv


# ============================================================
# RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent.parent

PROCESSED_DIR = BASE_DIR / "data" / "processed"
INDEX_DIR = BASE_DIR / "data" / "index"

PROCESSES_FILE = PROCESSED_DIR / "procesos.csv"

CONFIG_TASK1 = REPO_DIR / "tarea1_rag_normativo" / "config.yaml"

# Importamos el mismo sistema de embeddings de Tarea 1
TASK1_SRC = REPO_DIR / "tarea1_rag_normativo" / "src"

sys.path.insert(0, str(TASK1_SRC))

from embeddings import get_embedding_backend


# ============================================================
# ENV
# ============================================================

ENV_PATH = REPO_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)


# ============================================================
# CONFIG
# ============================================================

def load_task1_config():
    """
    Reutiliza la configuración de embeddings de Tarea 1.
    """
    if not CONFIG_TASK1.exists():
        raise FileNotFoundError(
            f"No se encontró la configuración de Tarea 1:\n{CONFIG_TASK1}"
        )

    with open(CONFIG_TASK1, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ============================================================
# LIMPIEZA
# ============================================================

def clean_text(value):
    if pd.isna(value):
        return ""

    value = str(value).strip()

    return value


def safe_metadata(value):
    """
    Chroma no acepta NaN/None como metadata en algunos escenarios.
    """
    if pd.isna(value):
        return ""

    return str(value)


def safe_float(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (ValueError, TypeError):
        return None


# ============================================================
# TEXTO PARA EMBEDDING
# ============================================================

def build_embedding_text(row):
    """
    Construye el texto semántico.

    La idea es que el embedding represente de qué trata el proceso,
    mientras que departamento/monto/fecha quedan como filtros exactos.
    """

    descripcion = clean_text(row.get("descripcion"))
    titulo = clean_text(row.get("titulo"))
    categoria = clean_text(row.get("categoria"))
    procedimiento = clean_text(row.get("procedimiento"))
    comprador = clean_text(row.get("comprador"))

    # Si hay descripción, la priorizamos.
    # El título sirve como contexto adicional.
    parts = []

    if titulo:
        parts.append(f"Título: {titulo}")

    if descripcion:
        parts.append(f"Descripción: {descripcion}")

    if categoria:
        parts.append(f"Categoría: {categoria}")

    if procedimiento:
        parts.append(f"Procedimiento: {procedimiento}")

    if comprador:
        parts.append(f"Comprador: {comprador}")

    return "\n".join(parts)


# ============================================================
# INDEXACIÓN
# ============================================================

def build_index():

    print("=" * 60)
    print("TAREA 2 - FASE 3: CONSTRUCCIÓN DEL ÍNDICE")
    print("=" * 60)

    # --------------------------------------------------------
    # Verificar dataset
    # --------------------------------------------------------

    if not PROCESSES_FILE.exists():
        raise FileNotFoundError(
            f"No existe:\n{PROCESSES_FILE}\n\n"
            "Primero ejecuta validate.py."
        )

    print(f"\nDataset:")
    print(PROCESSES_FILE)

    t0 = time.time()

    df = pd.read_csv(PROCESSES_FILE)

    print(f"\nProcesos cargados: {len(df):,}")
    print(f"Columnas: {len(df.columns)}")

    # --------------------------------------------------------
    # Configuración de embeddings
    # --------------------------------------------------------

    config = load_task1_config()

    print("\nCargando modelo local de embeddings...")

    embedding_backend = get_embedding_backend(
        config,
        which="local",
    )

    print(f"Modelo: {embedding_backend.name}")
    print(f"Dimensión: {embedding_backend.dimension}")

    # --------------------------------------------------------
    # Chroma
    # --------------------------------------------------------

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(
        path=str(INDEX_DIR)
    )

    collection_name = "procesos_procurement_local"

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "hnsw:space": "cosine"
        },
    )

    print(f"\nColección: {collection_name}")
    print(f"Índice: {INDEX_DIR}")

    # --------------------------------------------------------
    # Procesar documentos
    # --------------------------------------------------------

    BATCH_SIZE = 64

    total = len(df)
    indexed = 0
    skipped = 0

    start_index = time.time()

    for start in range(0, total, BATCH_SIZE):

        batch_df = df.iloc[start:start + BATCH_SIZE]

        texts = []
        ids = []
        metadatas = []

        for _, row in batch_df.iterrows():

            ocid = clean_text(row.get("ocid"))

            if not ocid:
                skipped += 1
                continue

            text = build_embedding_text(row)

            if not text.strip():
                skipped += 1
                continue

            # ------------------------------------------------
            # ID determinista
            # ------------------------------------------------

            process_id = f"process_{ocid}"

            # ------------------------------------------------
            # Metadata
            # ------------------------------------------------

            metadata = {
                "ocid": ocid,

                "departamento": safe_metadata(
                    row.get("departamento")
                ),

                "categoria": safe_metadata(
                    row.get("categoria")
                ),

                "comprador": safe_metadata(
                    row.get("comprador")
                ),

                "procedimiento": safe_metadata(
                    row.get("procedimiento")
                ),

                "fecha_publicacion": safe_metadata(
                    row.get("fecha_publicacion")
                ),

                "mes_origen": safe_metadata(
                    row.get("mes_origen")
                ),

                "monto_pen": safe_float(
                    row.get("monto_pen")
                ),

                "num_postores": safe_float(
                    row.get("num_postores")
                ),
            }

            # Chroma no acepta None en metadata.
            metadata = {
                k: v
                for k, v in metadata.items()
                if v is not None
            }

            ids.append(process_id)
            texts.append(text)
            metadatas.append(metadata)

        if not texts:
            continue

        # ------------------------------------------------
        # Embeddings
        # ------------------------------------------------

        embeddings = embedding_backend.encode_passages(
            texts
        )

        embeddings = [
            list(map(float, vector))
            for vector in embeddings
        ]

        # ------------------------------------------------
        # UPSERT
        # ------------------------------------------------
        #
        # Si ejecutamos el script nuevamente, no duplica procesos.
        # Actualiza el mismo ID.
        #

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        indexed += len(ids)

        print(
            f"  indexados {indexed:,}/{total:,}",
            end="\r",
        )

    elapsed = time.time() - start_index

    print("\n")
    print("=" * 60)
    print("RESULTADO")
    print("=" * 60)

    print(f"Procesos del CSV:       {total:,}")
    print(f"Procesos indexados:     {indexed:,}")
    print(f"Procesos omitidos:      {skipped:,}")
    print(f"Procesos en Chroma:     {collection.count():,}")
    print(f"Tiempo:                 {elapsed:.2f} s")

    if elapsed > 0:
        print(
            f"Velocidad:              "
            f"{indexed / elapsed:.2f} procesos/s"
        )

    print(f"\nÍndice guardado en:")
    print(INDEX_DIR)

    print("\nColección:")
    print(collection_name)

    print("\nOK: índice construido.")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    build_index()
