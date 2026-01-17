"""
Qdrant vector database client for long-term memory
"""
import os
from typing import Optional, List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
import openai


# Collection name for user memories
COLLECTION_NAME = "user_memories"

# Vector dimensions for OpenAI embeddings (text-embedding-3-small)
VECTOR_SIZE = 1536


class QdrantMemoryClient:
    """Qdrant client for storing and retrieving long-term memories"""

    def __init__(self):
        self.client: Optional[QdrantClient] = None
        self.qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self._openai_client: Optional[openai.OpenAI] = None

    def connect(self):
        """Connect to Qdrant"""
        if not self.client:
            self.client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port,
                timeout=10
            )
            self._ensure_collection()

        if not self._openai_client and self.openai_api_key:
            self._openai_client = openai.OpenAI(api_key=self.openai_api_key)

    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]

        if COLLECTION_NAME not in collection_names:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )
            # Create index for user_id for fast filtering
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name="user_id",
                field_schema=models.PayloadSchemaType.INTEGER
            )

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for text using OpenAI"""
        if not self._openai_client:
            raise ValueError("OpenAI client not initialized. Set OPENAI_API_KEY.")

        response = self._openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    def store_memory(
        self,
        user_id: int,
        content: str,
        message_id: Optional[int] = None,
        dialog_id: Optional[int] = None,
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a memory in Qdrant

        Args:
            user_id: User ID
            content: Text content to store
            message_id: Optional message ID from PostgreSQL
            dialog_id: Optional dialog ID
            role: Message role (user/assistant)
            metadata: Additional metadata

        Returns:
            Point ID
        """
        if not self.client:
            self.connect()

        # Get embedding
        embedding = self.get_embedding(content)

        # Generate unique point ID
        import uuid
        point_id = str(uuid.uuid4())

        # Prepare payload
        payload = {
            "user_id": user_id,
            "content": content,
            "role": role,
            "message_id": message_id,
            "dialog_id": dialog_id,
            **(metadata or {})
        }

        # Store in Qdrant
        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            ]
        )

        return point_id

    def search_memories(
        self,
        user_id: int,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant memories

        Args:
            user_id: User ID to filter by
            query: Search query text
            limit: Maximum results to return
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of memory dicts with content and score
        """
        if not self.client:
            self.connect()

        # Get query embedding
        query_embedding = self.get_embedding(query)

        # Search with user filter
        results = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            ),
            limit=limit,
            score_threshold=score_threshold
        )

        # Format results
        memories = []
        for result in results:
            memories.append({
                "id": result.id,
                "content": result.payload.get("content", ""),
                "role": result.payload.get("role", "user"),
                "score": result.score,
                "message_id": result.payload.get("message_id"),
                "dialog_id": result.payload.get("dialog_id")
            })

        return memories

    def delete_user_memories(self, user_id: int) -> int:
        """
        Delete all memories for a user

        Args:
            user_id: User ID

        Returns:
            Number of deleted points
        """
        if not self.client:
            self.connect()

        # Count before deletion
        count_before = self.client.count(
            collection_name=COLLECTION_NAME,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            )
        ).count

        # Delete by filter
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="user_id",
                            match=MatchValue(value=user_id)
                        )
                    ]
                )
            )
        )

        return count_before

    def get_user_memory_count(self, user_id: int) -> int:
        """Get count of memories for a user"""
        if not self.client:
            self.connect()

        result = self.client.count(
            collection_name=COLLECTION_NAME,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            )
        )
        return result.count

    def health_check(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            if not self.client:
                self.connect()
            self.client.get_collections()
            return True
        except Exception:
            return False


# Global client instance
qdrant_client = QdrantMemoryClient()
