import os
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent.parent
MODEL_NAME = "BAAI/bge-base-en-v1.5"
VECTOR_SIZE = 768
DOMAIN_COLLECTION = "kb_domain_layer"
COMPATIBILITY_COLLECTION = "kb_compatibility_layer"


class Retriever:
    def __init__(self):
        load_dotenv(ROOT / ".env")
        url = os.getenv("QDRANT_URL", "").strip()
        api_key = os.getenv("QDRANT_API_KEY", "").strip()
        if not url or not api_key:
            raise RuntimeError("QDRANT_URL and QDRANT_API_KEY must be configured in the root .env")
        self.client = QdrantClient(url=url, api_key=api_key, timeout=60)
        self._model = None
        self._collections = None

    @property
    def model(self):
        if self._model is None:
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    def refresh_collections(self):
        self._collections = {item.name for item in self.client.get_collections().collections}
        return self._collections

    def collection_exists(self, collection_name):
        if self._collections is None:
            self.refresh_collections()
        return collection_name in self._collections

    def verify_collections(self):
        names = self.refresh_collections()
        status = {}
        for collection_name in (DOMAIN_COLLECTION, COMPATIBILITY_COLLECTION):
            entry = {"exists": collection_name in names}
            if entry["exists"]:
                info = self.client.get_collection(collection_name)
                vectors = info.config.params.vectors
                entry.update(
                    {
                        "vector_count": self.client.count(collection_name, exact=True).count,
                        "vector_size": getattr(vectors, "size", None),
                        "distance": str(getattr(getattr(vectors, "distance", None), "value", getattr(vectors, "distance", None))),
                    }
                )
            status[collection_name] = entry
        return status

    def embed_query(self, query):
        return self.model.encode(
            query,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).tolist()

    def search(self, collection_name, query, top_k=5, query_vector=None):
        if not self.collection_exists(collection_name):
            raise RuntimeError(f"Collection unavailable: {collection_name}")
        vector = query_vector if query_vector is not None else self.embed_query(query)
        response = self.client.query_points(
            collection_name=collection_name,
            query=vector,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        return [
            {
                "collection": collection_name,
                "point_id": str(point.id),
                "score": float(point.score),
                "payload": point.payload or {},
            }
            for point in response.points
        ]
