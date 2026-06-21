import json
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient


ROOT = Path(__file__).resolve().parents[3]
QDRANT_DIR = Path(__file__).resolve().parent
REPORTS_DIR = QDRANT_DIR / "reports"
TESTS_DIR = QDRANT_DIR / "tests"
COLLECTION_NAME = "kb_compatibility_layer"
VECTOR_SIZE = 768
MODEL_NAME = "BAAI/bge-base-en-v1.5"
POINT_NAMESPACE = uuid.UUID("a576124a-4135-4f65-a7d6-e08ca001c49b")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def read_json(path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def get_client():
    load_dotenv(ROOT / ".env")
    url = os.getenv("QDRANT_URL", "").strip()
    api_key = os.getenv("QDRANT_API_KEY", "").strip()
    if not url or not api_key:
        raise RuntimeError("QDRANT_URL and QDRANT_API_KEY must be set in the root .env file")
    return QDRANTClientFactory.create(url, api_key)


class QDRANTClientFactory:
    @staticmethod
    def create(url, api_key):
        return QdrantClient(url=url, api_key=api_key, timeout=60)


def point_id(document_id):
    return str(uuid.uuid5(POINT_NAMESPACE, document_id))


def distance_name(distance):
    return str(getattr(distance, "value", distance)).lower()


def vector_config(collection_info):
    vectors = collection_info.config.params.vectors
    if isinstance(vectors, dict):
        raise RuntimeError("Named vectors are not supported by this Layer 3 pipeline")
    return int(vectors.size), distance_name(vectors.distance)


def validate_embeddings(records):
    failures = []
    ids = [record.get("document_id") for record in records]
    duplicates = len(ids) - len(set(ids))
    required_metadata = {
        "rule_id",
        "rule_type",
        "subject",
        "predicate",
        "object",
        "status",
        "confidence",
        "source",
    }
    for record in records:
        document_id = record.get("document_id")
        vector = record.get("embedding")
        metadata = record.get("metadata")
        if not document_id:
            failures.append({"document_id": document_id, "reason": "Missing document_id"})
        if not isinstance(vector, list) or len(vector) != VECTOR_SIZE:
            length = len(vector) if isinstance(vector, list) else None
            failures.append({"document_id": document_id, "reason": f"Invalid vector dimension: {length}"})
        elif not all(isinstance(value, (int, float)) and math.isfinite(value) for value in vector):
            failures.append({"document_id": document_id, "reason": "Vector contains null or non-finite values"})
        if not isinstance(metadata, dict):
            failures.append({"document_id": document_id, "reason": "Metadata is missing"})
        else:
            missing = sorted(required_metadata - set(metadata))
            if missing:
                failures.append({"document_id": document_id, "reason": f"Missing metadata fields: {missing}"})
    if duplicates:
        failures.append({"document_id": None, "reason": f"Found {duplicates} duplicate document IDs"})
    return failures, duplicates


def payload_for(record):
    metadata = record["metadata"]
    return {
        "document_id": record["document_id"],
        "rule_id": metadata["rule_id"],
        "rule_type": metadata["rule_type"],
        "subject": metadata["subject"],
        "predicate": metadata["predicate"],
        "object": metadata["object"],
        "status": metadata["status"],
        "confidence": float(metadata["confidence"]),
        "source": "CompatibilityLayer",
        "layer": "Layer3",
    }


def report_is_ready(filename, ready_status):
    path = REPORTS_DIR / filename
    return path.exists() and read_json(path).get("status") == ready_status


def write_readiness_report():
    connection_ready = report_is_ready("qdrant_connection_report.json", "CONNECTED")
    collection_ready = report_is_ready("collection_creation_report.json", "READY")
    upload_ready = report_is_ready("upload_report.json", "READY")
    integrity_ready = report_is_ready("collection_integrity_report.json", "READY")
    retrieval_ready = report_is_ready("retrieval_quality_report.json", "READY")
    all_ready = all((connection_ready, collection_ready, upload_ready, integrity_ready, retrieval_ready))

    vector_count = 0
    integrity_path = REPORTS_DIR / "collection_integrity_report.json"
    if integrity_path.exists():
        vector_count = int(read_json(integrity_path).get("vector_count", 0))

    report = {
        "connection_status": "PASS" if connection_ready else "FAIL",
        "collection_status": "PASS" if collection_ready else "FAIL",
        "upload_status": "PASS" if upload_ready else "FAIL",
        "integrity_status": "PASS" if integrity_ready else "FAIL",
        "retrieval_status": "PASS" if retrieval_ready else "FAIL",
        "vector_count": vector_count,
        "embedding_dimension": VECTOR_SIZE,
        "collection_name": COLLECTION_NAME,
        "status": "READY_FOR_PHASE_5" if all_ready else "VALIDATION_FAILED",
        "generated_at": utc_now(),
    }
    write_json(REPORTS_DIR / "layer3_qdrant_readiness.json", report)
    return report
