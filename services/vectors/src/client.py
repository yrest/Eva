"""Qdrant client wrapper."""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    SearchRequest,
)

from .config import settings


class VectorClient:
    """Wrapper for Qdrant client with convenience methods."""

    def __init__(self):
        """Initialize Qdrant client."""
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
            timeout=settings.qdrant_timeout
        )

    async def health_check(self) -> bool:
        """Check if Qdrant is available."""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def create_collection(
        self,
        name: str,
        vector_size: int,
        distance: str = None
    ) -> Dict[str, Any]:
        """
        Create a new collection.

        Args:
            name: Collection name
            vector_size: Dimension of vectors
            distance: Distance metric (Cosine, Euclid, Dot)

        Returns:
            Collection info
        """
        distance_metric = self._get_distance_metric(distance)

        self.client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance_metric
            )
        )

        return {
            "name": name,
            "vector_size": vector_size,
            "distance": distance or settings.default_distance
        }

    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        return self.client.delete_collection(collection_name=name)

    def collection_exists(self, name: str) -> bool:
        """Check if collection exists."""
        try:
            self.client.get_collection(collection_name=name)
            return True
        except Exception:
            return False

    def get_collection_info(self, name: str) -> Dict[str, Any]:
        """Get collection information."""
        info = self.client.get_collection(collection_name=name)
        return {
            "name": info.name,
            "status": info.status,
            "vector_size": info.config.params.vectors.size,
            "distance": str(info.config.params.vectors.distance),
            "points_count": info.points_count,
        }

    def list_collections(self) -> List[Dict[str, Any]]:
        """List all collections."""
        collections = self.client.get_collections().collections
        return [
            {
                "name": col.name,
            }
            for col in collections
        ]

    def upsert_vectors(
        self,
        collection: str,
        points: List[Dict[str, Any]]
    ) -> int:
        """
        Insert or update vectors.

        Args:
            collection: Collection name
            points: List of points with id, vector, and optional payload

        Returns:
            Number of points upserted
        """
        qdrant_points = [
            PointStruct(
                id=point["id"],
                vector=point["vector"],
                payload=point.get("payload", {})
            )
            for point in points
        ]

        self.client.upsert(
            collection_name=collection,
            points=qdrant_points
        )

        return len(qdrant_points)

    def search_vectors(
        self,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            collection: Collection name
            query_vector: Query vector
            limit: Maximum results
            score_threshold: Minimum similarity score
            filter_conditions: Optional metadata filters

        Returns:
            List of search results with id, score, and payload
        """
        # Build filter if provided
        query_filter = None
        if filter_conditions:
            query_filter = Filter(**filter_conditions)

        results = self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter
        )

        return [
            {
                "id": result.id,
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]

    def get_vector(self, collection: str, point_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific vector by ID."""
        result = self.client.retrieve(
            collection_name=collection,
            ids=[point_id]
        )

        if not result:
            return None

        point = result[0]
        return {
            "id": point.id,
            "vector": point.vector,
            "payload": point.payload
        }

    def delete_vectors(
        self,
        collection: str,
        point_ids: List[str] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Delete vectors by IDs or filter.

        Args:
            collection: Collection name
            point_ids: List of point IDs to delete
            filter_conditions: Filter conditions for deletion

        Returns:
            Success status
        """
        if point_ids:
            self.client.delete(
                collection_name=collection,
                points_selector=point_ids
            )
        elif filter_conditions:
            query_filter = Filter(**filter_conditions)
            self.client.delete(
                collection_name=collection,
                points_selector=query_filter
            )
        else:
            raise ValueError("Must provide either point_ids or filter_conditions")

        return True

    def _get_distance_metric(self, distance: Optional[str]) -> Distance:
        """Convert distance string to Qdrant Distance enum."""
        distance = distance or settings.default_distance

        if distance.lower() == "cosine":
            return Distance.COSINE
        elif distance.lower() == "euclid":
            return Distance.EUCLID
        elif distance.lower() == "dot":
            return Distance.DOT
        else:
            raise ValueError(f"Unknown distance metric: {distance}")


# Global client instance
vector_client = VectorClient()
