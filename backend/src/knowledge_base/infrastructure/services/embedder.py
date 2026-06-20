"""Gemini embedding API client (768-dim vectors)."""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

EMBED_WORKERS = 10
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768


class Embedder:
    """Generates embeddings via the Gemini embedding API."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    def _embed_sync(self, text: str) -> list[float]:
        """Synchronous single-text embedding call."""
        from google import genai as _genai

        client = _genai.Client(api_key=self.api_key)
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config={"output_dimensionality": EMBEDDING_DIM},
        )
        return list(result.embeddings[0].values)

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._embed_sync, text)

    async def embed_many(self, texts: list[str]) -> list[list[float] | None]:
        """
        Generate embeddings for multiple texts in parallel.
        Returns list of embedding vectors (None for failed chunks).
        """
        loop = asyncio.get_event_loop()

        def _embed_all() -> list[list[float] | None]:
            results: dict[int, list[float] | None] = {}

            with ThreadPoolExecutor(max_workers=EMBED_WORKERS) as pool:
                futures = {pool.submit(self._embed_sync, text): idx for idx, text in enumerate(texts)}
                for future in futures:
                    idx = futures[future]
                    try:
                        results[idx] = future.result()
                    except Exception as exc:
                        logger.warning("Embedding failed for chunk %d, skipping: %s", idx, exc)
                        results[idx] = None

            return [results.get(i) for i in range(len(texts))]

        return await loop.run_in_executor(None, _embed_all)
