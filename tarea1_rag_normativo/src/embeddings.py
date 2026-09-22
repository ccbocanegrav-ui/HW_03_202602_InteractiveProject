"""
embeddings.py — Fase 2 (Phase 2 y 4), Task 1

Interfaz comun para embeddings, con 2 implementaciones intercambiables
por configuracion (config.yaml: embeddings.local vs embeddings.api),
tal como exige el enunciado: "expose one common interface with two
implementations, so that switching models is a configuration change."

DECISION DE PREFIJOS (e5): el modelo multilingual-e5-base fue entrenado
para distinguir explicitamente el rol del texto: los queries llevan el
prefijo "query: " y los pasajes/documentos llevan "passage: ". Sin el
prefijo correcto la similitud coseno se degrada (documentado en el
model card del modelo). Por eso la interfaz separa encode_queries() de
encode_passages() en vez de un unico encode() generico — evita el bug
silencioso de usar el prefijo equivocado en un lado.

LIMITE DE TOKENS: multilingual-e5-base trunca a 512 tokens de entrada.
Nuestros chunks se generaron a ~300 caracteres (Fase 2), que en
español son tipicamente 60-90 tokens — muy por debajo del limite, asi
que ningun chunk se trunca al truncar embeddings.

Uso:
    from embeddings import get_embedding_backend
    backend = get_embedding_backend(config, which="local")  # o "api"
    vecs = backend.encode_passages(["texto 1", "texto 2"])
    qvec = backend.encode_queries(["mi pregunta"])
"""

from abc import ABC, abstractmethod


class EmbeddingBackend(ABC):
    name: str
    dimension: int

    @abstractmethod
    def encode_passages(self, texts: list[str]):
        """Embeddings para texto de DOCUMENTO/CHUNK (para indexar)."""
        raise NotImplementedError

    @abstractmethod
    def encode_queries(self, texts: list[str]):
        """Embeddings para PREGUNTAS del usuario (para buscar)."""
        raise NotImplementedError


class LocalE5Backend(EmbeddingBackend):
    """sentence-transformers, corre en CPU, sin costo por llamada."""

    def __init__(self, model_name: str, query_prefix: str, passage_prefix: str):
        from sentence_transformers import SentenceTransformer  # import perezoso

        self.name = model_name
        self.query_prefix = query_prefix
        self.passage_prefix = passage_prefix
        self._model = SentenceTransformer(model_name)
        self.dimension = self._model.get_sentence_embedding_dimension()

    def encode_passages(self, texts: list[str]):
        prefixed = [self.passage_prefix + t for t in texts]
        return self._model.encode(prefixed, normalize_embeddings=True)

    def encode_queries(self, texts: list[str]):
        prefixed = [self.query_prefix + t for t in texts]
        return self._model.encode(prefixed, normalize_embeddings=True)


class OpenAIAPIBackend(EmbeddingBackend):
    """text-embedding-3-small vía API. No requiere prefijos especiales."""

    def __init__(self, model_name: str):
        import os
        from openai import OpenAI  # import perezoso

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY no encontrada en el entorno. "
                "Definela en tu archivo .env (nunca en el codigo ni en el repo)."
            )
        self.name = model_name
        self._client = OpenAI(api_key=api_key)
        self.dimension = 1536  # text-embedding-3-small

    def _embed(self, texts: list[str]):
        resp = self._client.embeddings.create(model=self.name, input=texts)
        return [d.embedding for d in resp.data]

    def encode_passages(self, texts: list[str]):
        return self._embed(texts)

    def encode_queries(self, texts: list[str]):
        return self._embed(texts)  # OpenAI no distingue query/passage


def get_embedding_backend(config: dict, which: str = "local") -> EmbeddingBackend:
    """which: 'local' o 'api', segun config['embeddings']."""
    emb_cfg = config["embeddings"][which]
    if which == "local":
        return LocalE5Backend(
            model_name=emb_cfg["model_name"],
            query_prefix=emb_cfg["query_prefix"],
            passage_prefix=emb_cfg["passage_prefix"],
        )
    elif which == "api":
        return OpenAIAPIBackend(model_name=emb_cfg["model_name"])
    else:
        raise ValueError(f"Backend desconocido: {which}")
