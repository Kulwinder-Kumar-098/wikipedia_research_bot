"""Small OpenAI-compatible client for grounded RAG answers."""

import re
import unicodedata

import requests

import config
from src.exceptions import LLMError


class LLMClient:
    def __init__(self, api_key=None, base_url=None, model=None, timeout=None):
        self.api_key = api_key or config.LLM_API_KEY
        self.base_url = (base_url or config.LLM_BASE_URL or "").rstrip("/")
        self.model = model or config.LLM_MODEL
        self.timeout = timeout or config.REQUEST_TIMEOUT

    def answer(self, question: str, context: str) -> str:
        if not self.api_key or not self.base_url:
            raise LLMError(
                "LLM is not configured. Set LLM_API_KEY and LLM_BASE_URL, "
                "or configure NEON_AI_GATEWAY_TOKEN and NEON_AI_GATEWAY_BASE_URL."
            )
        endpoint = f"{self.base_url}/chat/completions" if self.base_url.endswith("/v1") else f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Answer only from the supplied knowledge base. If the answer "
                        "is not supported by it, say you could not find it. Cite the "
                        "source titles in square brackets. Do not invent facts."
                    ),
                },
                {"role": "user", "content": f"Knowledge base:\n{context}\n\nQuestion: {question}"},
            ],
        }
        try:
            response = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            answer = normalize_answer(
                data.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            if not answer:
                raise LLMError("The language model returned an empty answer.")
            return answer
        except LLMError:
            raise
        except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc


def normalize_answer(answer: str) -> str:
    """Make model output readable and consistent across providers."""
    normalized = unicodedata.normalize("NFKC", answer)
    normalized = normalized.translate(
        str.maketrans({
            "\u00a0": " ",
            "\u202f": " ",
            "\u2011": "-",
            "\u2010": "-",
            "\u2013": "-",
            "\u2014": "-",
            "\u3010": "[",
            "\u3011": "]",
        })
    )
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()