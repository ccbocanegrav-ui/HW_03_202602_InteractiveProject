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
        self.dimension = self._model.get_embedding_dimension()


    def encode_passages(self, texts: list[str]):
        prefixed = [self.passage_prefix + t for t in texts]
        return self._model.encode(prefixed, normalize_embeddings=True)

    def encode_queries(self, texts: list[str]):
        prefixed = [self.query_prefix + t for t in texts]
        return self._model.encode(prefixed, normalize_embeddings=True)


class GeminiAPIBackend(EmbeddingBackend):
    """text-embedding-004 (Google AI Studio). SUSTITUYE a text-embedding-3-small
    de OpenAI para la comparacion de Fase 4: decision documentada por
    falta de presupuesto para creditos de OpenAI (ver DECISIONES.md).
    Gemini distingue query vs. documento via el parametro task_type,
    similar en espiritu a los prefijos query/passage de e5.

    NOTA: usa el SDK NUEVO (paquete "google-genai", import "from google
    import genai"), no el deprecado "google-generativeai". El paquete
    viejo tiene un bug conocido: no soporta las API keys nuevas de
    Google AI Studio (prefijo "AQ.") para el endpoint de embeddings,
    y falla con 401 ACCESS_TOKEN_TYPE_UNSUPPORTED sin importar el
    transporte (rest o grpc). El SDK nuevo si las soporta.
    """

    def __init__(self, model_name: str):
        import os
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY no encontrada en el entorno. "
                "Definela en tu archivo .env (nunca en el codigo ni en el repo)."
            )
        self._client = genai.Client(api_key=api_key)
        self.name = model_name
        self.dimension = 768  # text-embedding-004

    def _embed(self, texts: list[str], task_type: str):
        from google.genai import types

        vectors = []
        for t in texts:  # la API de Gemini embebe de a un texto por llamada
            result = self._client.models.embed_content(
                model=self.name,
                contents=t,
                config=types.EmbedContentConfig(task_type=task_type),
            )
            vectors.append(result.embeddings[0].values)
        return vectors

    def encode_passages(self, texts: list[str]):
        return self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    def encode_queries(self, texts: list[str]):
        return self._embed(texts, task_type="RETRIEVAL_QUERY")


class CohereAPIBackend(EmbeddingBackend):
    """embed-multilingual-v3.0 (Cohere). SEGUNDA sustitucion documentada
    de Fase 4: se intento primero con Gemini (text-embedding-004), pero
    su endpoint de embeddings tiene un bug confirmado del lado de Google
    con las API keys nuevas (prefijo "AQ."): rechaza la autenticacion
    con 401 ACCESS_TOKEN_TYPE_UNSUPPORTED en el endpoint de embeddings
    especificamente, aunque el mismo key SI funciona para generacion de
    texto. Es un problema reportado activamente en el foro oficial de
    Google AI, no controlable desde este codigo. Cohere ofrece nivel
    gratuito sin tarjeta y no tiene este problema. Ver DECISIONES.md.
    """

    def __init__(self, model_name: str):
        import os
        import cohere

        api_key = os.environ.get("COHERE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "COHERE_API_KEY no encontrada en el entorno. "
                "Definela en tu archivo .env (nunca en el codigo ni en el repo)."
            )
        self._client = cohere.ClientV2(api_key=api_key)
        self.name = model_name
        self.dimension = 1024  # embed-multilingual-v3.0

    def _embed(self, texts: list[str], input_type: str):
        response = self._client.embed(
            texts=texts, model=self.name, input_type=input_type, embedding_types=["float"],
        )
        return response.embeddings.float_

    def encode_passages(self, texts: list[str]):
        return self._embed(texts, input_type="search_document")

    def encode_queries(self, texts: list[str]):
        return self._embed(texts, input_type="search_query")


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
        provider = emb_cfg.get("provider", "openai")
        if provider == "cohere":
            return CohereAPIBackend(model_name=emb_cfg["model_name"])
        if provider == "gemini":
            return GeminiAPIBackend(model_name=emb_cfg["model_name"])
        return OpenAIAPIBackend(model_name=emb_cfg["model_name"])
    else:
        raise ValueError(f"Backend desconocido: {which}")
