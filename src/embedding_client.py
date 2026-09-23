"""OpenAI-compatible embedding client used by vector retrieval."""

import requests

import config
from src.exceptions import EmbeddingError


class EmbeddingClient:
    def __init__(self, api_key=None, base_url=None, model=None, timeout=None):
        self.api_key = api_key or config.EMBEDDING_API_KEY
        self.base_url = (base_url or config.EMBEDDING_BASE_URL or "").rstrip("/")
        self.model = model or config.EMBEDDING_MODEL
        self.timeout = timeout or config.REQUEST_TIMEOUT
        self._local_model = None

    @property
    def configured(self) -> bool:
        return config.EMBEDDING_PROVIDER == "local" or bool(
            self.api_key and self.base_url
        )

    def embed(self, text: str) -> list[float]:
        if not self.configured:
            raise EmbeddingError(
                "Vector RAG is not configured. Set EMBEDDING_API_KEY and "
                "EMBEDDING_BASE_URL for an OpenAI-compatible embeddings provider."
            )
        if config.EMBEDDING_PROVIDER == "local":
            return self._embed_local(text)
        endpoint = (
            f"{self.base_url}/embeddings"
            if self.base_url.endswith("/v1")
            else f"{self.base_url}/v1/embeddings"
        )
        try:
            response = requests.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self.model, "input": text},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            embedding = data["data"][0]["embedding"]
            if not embedding:
                raise EmbeddingError("The embedding provider returned an empty vector.")
            return [float(value) for value in embedding]
        except EmbeddingError:
            raise
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as exc:
            raise EmbeddingError(f"Embedding request failed: {exc}") from exc

    def _embed_local(self, text: str) -> list[float]:
        """Generate a free local embedding; the model is loaded only once."""
        try:
            if self._local_model is None:
                from sentence_transformers import SentenceTransformer

                self._local_model = SentenceTransformer(self.model)
            vector = self._local_model.encode(text, normalize_embeddings=True)
            return [float(value) for value in vector.tolist()]
        except ImportError as exc:
            raise EmbeddingError(
                "The local embedding model requires sentence-transformers. "
                "Install dependencies with: pip install -r requirements.txt"
            ) from exc
        except Exception as exc:
            raise EmbeddingError(f"Local embedding generation failed: {exc}") from exc