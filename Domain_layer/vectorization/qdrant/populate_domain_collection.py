import json
import math
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams


ROOT = Path(__file__).resolve().parents[3]
VECTOR_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = Path(__file__).resolve().parent / "reports"
EMBEDDINGS_PATH = VECTOR_ROOT / "embeddings" / "domain_embeddings.json"
COLLECTION_NAME = "kb_domain_layer"
VECTOR_SIZE = 768
POINT_NAMESPACE = uuid.UUID("9c8e4c39-038c-4bf7-8e16-89db93ff2541")
BATCH_SIZE = 100


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def status_value(value):
    return str(getattr(value, "value", value)).lower()


def main():
    load_dotenv(ROOT / ".env")
    url = os.getenv("QDRANT_URL", "").strip()
    api_key = os.getenv("QDRANT_API_KEY", "").strip()
    if not url or not api_key:
        raise RuntimeError("QDRANT_URL and QDRANT_API_KEY are required in the root .env")
    client = QdrantClient(url=url, api_key=api_key, timeout=60)
    client.get_collections()

    with EMBEDDINGS_PATH.open("r", encoding="utf-8-sig") as handle:
        records = json.load(handle)
    identifiers = [record["document_id"] for record in records]
    failures = []
    duplicates = len(identifiers) - len(set(identifiers))
    for record in records:
        vector = record.get("embedding")
        if not isinstance(vector, list) or len(vector) != VECTOR_SIZE:
            failures.append({"document_id": record.get("document_id"), "reason": "Invalid vector dimension"})
        elif not all(isinstance(value, (int, float)) and math.isfinite(value) for value in vector):
            failures.append({"document_id": record.get("document_id"), "reason": "Null or non-finite vector value"})
        if not record.get("metadata") or not record.get("text"):
            failures.append({"document_id": record.get("document_id"), "reason": "Missing metadata or semantic text"})
    if duplicates:
        failures.append({"document_id": None, "reason": f"Found {duplicates} duplicate document IDs"})
    write_json(
        REPORTS_DIR / "embedding_validation_report.json",
        {
            "documents_processed": len(records),
            "embedding_dimension": VECTOR_SIZE,
            "duplicates": duplicates,
            "failures": failures,
            "status": "READY" if not failures else "VALIDATION_FAILED",
        },
    )
    if failures:
        raise RuntimeError("Domain embedding validation failed")

    created = False
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        created = True
    info = client.get_collection(COLLECTION_NAME)
    vectors = info.config.params.vectors
    actual_size = getattr(vectors, "size", None)
    actual_distance = status_value(getattr(vectors, "distance", None))
    if actual_size != VECTOR_SIZE or actual_distance != "cosine":
        raise RuntimeError("Existing kb_domain_layer vector configuration is incompatible")

    indexes = {
        "document_id": PayloadSchemaType.KEYWORD,
        "entity_id": PayloadSchemaType.KEYWORD,
        "name": PayloadSchemaType.KEYWORD,
        "type": PayloadSchemaType.KEYWORD,
        "subtype": PayloadSchemaType.KEYWORD,
        "knowledge_category": PayloadSchemaType.KEYWORD,
        "source": PayloadSchemaType.KEYWORD,
        "layer": PayloadSchemaType.KEYWORD,
    }
    for field_name, field_schema in indexes.items():
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field_name,
            field_schema=field_schema,
            wait=True,
        )
    write_json(
        REPORTS_DIR / "collection_creation_report.json",
        {
            "collection_name": COLLECTION_NAME,
            "created": created,
            "existing_collection_preserved": not created,
            "vector_size": actual_size,
            "distance": actual_distance,
            "payload_indexed_fields": sorted(indexes),
            "status": "READY",
        },
    )

    points = []
    for record in records:
        metadata = record["metadata"]
        payload = {
            "document_id": record["document_id"],
            "entity_id": metadata["entity_id"],
            "name": metadata["name"],
            "type": metadata["type"],
            "subtype": metadata["subtype"],
            "knowledge_category": metadata["knowledge_category"],
            "domain_layer": metadata["domain_layer"],
            "compatibility_relevance": metadata["compatibility_relevance"],
            "validation_priority": metadata["validation_priority"],
            "source_file": metadata["source_file"],
            "source": "DomainLayer",
            "layer": "Layer1",
            "text": record["text"],
        }
        points.append(
            PointStruct(
                id=str(uuid.uuid5(POINT_NAMESPACE, record["document_id"])),
                vector=record["embedding"],
                payload=payload,
            )
        )

    started = time.perf_counter()
    uploaded = 0
    upload_failures = []
    for offset in range(0, len(points), BATCH_SIZE):
        batch = points[offset : offset + BATCH_SIZE]
        try:
            client.upsert(COLLECTION_NAME, points=batch, wait=True)
            uploaded += len(batch)
        except Exception as exc:
            upload_failures.append(str(exc))
    upload_time = round(time.perf_counter() - started, 3)
    write_json(
        REPORTS_DIR / "upload_report.json",
        {
            "vectors_uploaded": uploaded,
            "documents_expected": len(records),
            "failures": upload_failures,
            "duplicates": duplicates,
            "batch_size": BATCH_SIZE,
            "upload_time_seconds": upload_time,
            "status": "READY" if uploaded == len(records) and not upload_failures else "UPLOAD_FAILED",
        },
    )
    if upload_failures:
        raise RuntimeError("Domain vector upload failed")

    count = client.count(COLLECTION_NAME, exact=True).count
    sample, _ = client.scroll(COLLECTION_NAME, limit=1, with_payload=True, with_vectors=False)
    payload_complete = bool(sample and sample[0].payload.get("text") and sample[0].payload.get("entity_id"))
    ready = count == len(records) and payload_complete
    write_json(
        REPORTS_DIR / "collection_integrity_report.json",
        {
            "collection_name": COLLECTION_NAME,
            "expected_vector_count": len(records),
            "vector_count": count,
            "embedding_dimension": actual_size,
            "distance": actual_distance,
            "payload_text_present": payload_complete,
            "failed_vectors": len(upload_failures),
            "status": "READY_FOR_RETRIEVAL" if ready else "INTEGRITY_FAILED",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    if not ready:
        raise RuntimeError("Domain collection integrity validation failed")
    print(f"Populated {COLLECTION_NAME} with {count} vectors in {upload_time} seconds")


if __name__ == "__main__":
    main()
