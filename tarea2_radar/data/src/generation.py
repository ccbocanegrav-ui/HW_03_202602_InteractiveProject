"""
generation.py — Fase 3, Task 1: interfaz comun para el modelo GENERADOR
(la parte que redacta la respuesta, no la de embeddings).

DECISION: se soportan 2 proveedores intercambiables por config.yaml
(generation.provider), sin tocar codigo:
  - "openai": gpt-4o-mini (de pago, requiere creditos cargados)
  - "gemini": gemini-1.5-flash / gemini-2.0-flash (Google AI Studio
    tiene un nivel GRATUITO real, sin tarjeta de credito, con cuota
    diaria generosa — suficiente para todo este proyecto)

El enunciado permite explicitamente "any provider" (DeepSeek, OpenAI,
Gemini, Anthropic, other), asi que usar Gemini gratis es una decision
valida y ahorra el problema de necesitar creditos de OpenAI.

Cada implementacion devuelve la MISMA forma de resultado:
    {"text": str, "tokens_in": int, "tokens_out": int}
para que engine.py no tenga que saber cual proveedor esta detras.
"""

from abc import ABC, abstractmethod


class GenerationBackend(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> dict:
        raise NotImplementedError


class OpenAIGenerator(GenerationBackend):
    def __init__(self, model_name: str):
        import os
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY no encontrada en el entorno (revisa tu .env).")
        self.model_name = model_name
        self._client = OpenAI(api_key=api_key)

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> dict:
        response = self._client.chat.completions.create(
            model=self.model_name,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return {
            "text": response.choices[0].message.content,
            "tokens_in": response.usage.prompt_tokens,
            "tokens_out": response.usage.completion_tokens,
        }


class GeminiGenerator(GenerationBackend):
    """Google Gemini via google-generativeai. Nivel gratuito de Google
    AI Studio: sin tarjeta de credito, cuota diaria generosa (suficiente
    para desarrollo y evaluacion de este proyecto). Conseguir API key
    gratis en: https://aistudio.google.com/apikey
    """

    def __init__(self, model_name: str):
        import os
        import google.generativeai as genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY no encontrada en el entorno (revisa tu .env).")
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self._model = genai.GenerativeModel(model_name)

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> dict:
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = self._model.generate_content(
            full_prompt,
            generation_config={"max_output_tokens": max_tokens},
        )
        usage = response.usage_metadata
        return {
            "text": response.text,
            "tokens_in": usage.prompt_token_count,
            "tokens_out": usage.candidates_token_count,
        }


class CohereGenerator(GenerationBackend):
    """command-r (Cohere). TERCER proveedor de generacion probado: se
    intento primero OpenAI (requiere creditos de pago, no disponibles),
    luego Gemini (funciono un tiempo pero el mismo bug de Google del
    endpoint de embeddings — 401 ACCESS_TOKEN_TYPE_UNSUPPORTED con
    keys nuevas "AQ." — empezo a afectar tambien a generateContent).
    Cohere ya se uso exitosamente para embeddings (Fase 4) y no tiene
    este problema, asi que se unifica todo en un solo proveedor
    confiable. Ver DECISIONES.md."""

    def __init__(self, model_name: str):
        import os
        import cohere

        api_key = os.environ.get("COHERE_API_KEY")
        if not api_key:
            raise RuntimeError("COHERE_API_KEY no encontrada en el entorno (revisa tu .env).")
        self.model_name = model_name
        self._client = cohere.ClientV2(api_key=api_key)

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int) -> dict:
        response = self._client.chat(
            model=self.model_name,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.message.content[0].text
        usage = response.usage.billed_units
        return {
            "text": text,
            "tokens_in": int(usage.input_tokens or 0),
            "tokens_out": int(usage.output_tokens or 0),
        }


def get_generation_backend(config: dict) -> GenerationBackend:
    provider = config["generation"]["provider"]
    model_name = config["generation"]["model_name"]
    if provider == "openai":
        return OpenAIGenerator(model_name)
    elif provider == "gemini":
        return GeminiGenerator(model_name)
    elif provider == "cohere":
        return CohereGenerator(model_name)
    else:
        raise ValueError(f"Proveedor de generacion desconocido: {provider}")
