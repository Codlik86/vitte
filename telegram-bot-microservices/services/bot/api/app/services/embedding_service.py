"""
Embedding service for vector memory with Qdrant

Uses OpenRouter API for text-embedding-3-small embeddings
"""

import httpx
import logging
from typing import Optional
from datetime import datetime

from app.config import config

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1"


class EmbeddingService:
    """Service for creating embeddings and managing Qdrant vectors"""

    def __init__(self):
        self.api_key = config.openrouter_api_key
        self.model = config.embedding_model
        self.qdrant_url = config.qdrant_url.rstrip("/")
        self.collection = config.qdrant_collection
        self.vector_size = 1536  # text-embedding-3-small dimension

    async def create_embedding(self, text: str) -> Optional[list[float]]:
        """
        Create embedding vector for text using OpenRouter.

        Args:
            text: Text to embed

        Returns:
            List of floats (embedding vector) or None if failed
        """
        if not self.api_key:
            logger.error("OPENROUTER_API_KEY not configured")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "input": text,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{OPENROUTER_API_URL}/embeddings",
                    headers=headers,
                    json=payload,
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.error(
                        f"OpenRouter embedding error: {response.status_code} - {response.text}"
                    )
                    return None

                data = response.json()
                embeddings = data.get("data", [])

                if not embeddings:
                    logger.error("OpenRouter returned empty embeddings")
                    return None

                return embeddings[0].get("embedding")

        except httpx.RequestError as e:
            logger.error(f"OpenRouter request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating embedding: {e}")
            return None

    async def ensure_collection(self) -> bool:
        """Ensure Qdrant collection exists."""
        try:
            async with httpx.AsyncClient() as client:
                # Check if collection exists
                response = await client.get(
                    f"{self.qdrant_url}/collections/{self.collection}",
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return True

                # Create collection
                payload = {
                    "vectors": {
                        "size": self.vector_size,
                        "distance": "Cosine",
                    }
                }

                response = await client.put(
                    f"{self.qdrant_url}/collections/{self.collection}",
                    json=payload,
                    timeout=10.0,
                )

                if response.status_code in (200, 201):
                    logger.info(f"Created Qdrant collection: {self.collection}")
                    return True

                logger.error(f"Failed to create collection: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error ensuring collection: {e}")
            return False

    async def store_memory(
        self,
        user_id: int,
        dialog_id: int,
        persona_id: int,
        text: str,
        role: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """
        Store a memory (message) in Qdrant.

        Args:
            user_id: Telegram user ID
            dialog_id: Dialog ID
            persona_id: Persona ID
            text: Message text to store
            role: Message role (user/assistant)
            metadata: Additional metadata

        Returns:
            True if stored successfully
        """
        embedding = await self.create_embedding(text)
        if not embedding:
            return False

        await self.ensure_collection()

        point_id = f"{user_id}_{dialog_id}_{datetime.utcnow().timestamp()}"

        payload = {
            "user_id": user_id,
            "dialog_id": dialog_id,
            "persona_id": persona_id,
            "text": text,
            "role": role,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.qdrant_url}/collections/{self.collection}/points",
                    json={
                        "points": [
                            {
                                "id": hash(point_id) & 0xFFFFFFFFFFFFFFFF,  # Qdrant needs uint64
                                "vector": embedding,
                                "payload": payload,
                            }
                        ]
                    },
                    timeout=10.0,
                )

                if response.status_code in (200, 201):
                    return True

                logger.error(f"Failed to store memory: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return False

    async def search_memories(
        self,
        user_id: int,
        persona_id: int,
        query: str,
        limit: int = 5,
        min_score: float = 0.7,
    ) -> list[dict]:
        """
        Search for relevant memories using semantic similarity.

        Args:
            user_id: Telegram user ID
            persona_id: Persona ID
            query: Query text to search for
            limit: Maximum number of results
            min_score: Minimum similarity score

        Returns:
            List of memory dicts with text, role, score
        """
        embedding = await self.create_embedding(query)
        if not embedding:
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.qdrant_url}/collections/{self.collection}/points/search",
                    json={
                        "vector": embedding,
                        "limit": limit,
                        "score_threshold": min_score,
                        "filter": {
                            "must": [
                                {"key": "user_id", "match": {"value": user_id}},
                                {"key": "persona_id", "match": {"value": persona_id}},
                            ]
                        },
                        "with_payload": True,
                    },
                    timeout=10.0,
                )

                if response.status_code != 200:
                    logger.error(f"Search failed: {response.text}")
                    return []

                data = response.json()
                results = []

                for hit in data.get("result", []):
                    payload = hit.get("payload", {})
                    results.append({
                        "text": payload.get("text", ""),
                        "role": payload.get("role", ""),
                        "score": hit.get("score", 0),
                        "timestamp": payload.get("timestamp", ""),
                    })

                return results

        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []

    async def delete_dialog_memories(self, user_id: int, dialog_id: int) -> bool:
        """
        Delete all memories for a specific dialog.

        Args:
            user_id: Telegram user ID
            dialog_id: Dialog ID

        Returns:
            True if deleted successfully
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.qdrant_url}/collections/{self.collection}/points/delete",
                    json={
                        "filter": {
                            "must": [
                                {"key": "user_id", "match": {"value": user_id}},
                                {"key": "dialog_id", "match": {"value": dialog_id}},
                            ]
                        }
                    },
                    timeout=10.0,
                )

                return response.status_code in (200, 201)

        except Exception as e:
            logger.error(f"Error deleting memories: {e}")
            return False


# Global service instance
embedding_service = EmbeddingService()
