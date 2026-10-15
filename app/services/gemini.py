import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from app.config import Settings
from app.schemas import AppError


class Gemini:
    """The only module allowed to call the Gemini API."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def generate(self, prompt: str, *, schema: type[BaseModel] | None = None) -> str:
        key = self.settings.gemini_api_key.get_secret_value()
        if not key:
            raise AppError(503, "GEMINI_API_KEY não configurada.")
        config = types.GenerateContentConfig(temperature=0)
        if schema is not None:
            config.response_mime_type = "application/json"
            config.response_schema = schema
        try:
            with genai.Client(
                api_key=key,
                http_options=types.HttpOptions(
                    timeout=int(self.settings.gemini_timeout_seconds * 1000),
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            ) as client:
                response = client.models.generate_content(
                    model=self.settings.gemini_model, contents=prompt, config=config
                )
                text = response.text
        except httpx.TimeoutException as exc:
            raise AppError(504, "Tempo limite na chamada ao Gemini.") from exc
        except errors.APIError as exc:
            status = 504 if exc.code == 504 else 502
            raise AppError(status, "Não foi possível obter resposta do Gemini.") from exc
        except httpx.HTTPError as exc:
            raise AppError(502, "Falha de conexão com o Gemini.") from exc
        if not text or not text.strip():
            raise AppError(502, "O Gemini retornou uma resposta vazia ou bloqueada.")
        return text.strip()
