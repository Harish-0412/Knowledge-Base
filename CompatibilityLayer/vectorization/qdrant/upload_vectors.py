import time

from qdrant_client.models import PointStruct

from qdrant_common import (
    COLLECTION_NAME,
    REPORTS_DIR,
    VECTOR_SIZE,
    get_client,
    payload_for,
    point_id,
    read_json,
    utc_now,
    validate_embeddings,
    write_json,
)


EMBEDDINGS_PATH = (
    REPORTS_DIR.parent.parent / "embeddings" / "compatibility_embeddings.json"
)
BATCH_SIZE = 100


def main():
    records = read_json(EMBEDDINGS_PATH)
    failures, duplicates = validate_embeddings(records)
    validation_report = {
        "documents_processed": len(records),
        "valid_embeddings": len(records) - len({failure.get("document_id") for failure in failures if failure.get("document_id")}),
        "embedding_dimension": VECTOR_SIZE,
        "duplicates": duplicates,
        "null_vectors": sum("null" in failure["reason"].lower() for failure in failures),
        "metadata_present": not any("metadata" in failure["reason"].lower() for failure in failures),
        "failures": failures,
        "status": "READY" if not failures else "VALIDATION_FAILED",
        "checked_at": utc_now(),
    }
    write_json(REPORTS_DIR / "embedding_validation_report.json", validation_report)
    if failures:
        raise RuntimeError("Embedding validation failed; upload was not attempted")

    client = get_client()
    if not client.collection_exists(COLLECTION_NAME):
        raise RuntimeError(f"Collection {COLLECTION_NAME} does not exist")

    upload_failures = []
    uploaded = 0
    started = time.perf_counter()
    for offset in range(0, len(records), BATCH_SIZE):
        batch = records[offset : offset + BATCH_SIZE]
        points = [
            PointStruct(
                id=point_id(record["document_id"]),
                vector=record["embedding"],
                payload=payload_for(record),
            )
            for record in batch
        ]
        try:
            client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
            uploaded += len(points)
        except Exception as exc:
            upload_failures.extend(
                {"document_id": record["document_id"], "reason": str(exc)} for record in batch
            )

    elapsed = round(time.perf_counter() - started, 3)
    ready = uploaded == len(records) and not upload_failures
    report = {
        "vectors_uploaded": uploaded,
        "documents_expected": len(records),
        "failures": upload_failures,
        "duplicates": duplicates,
        "batch_size": BATCH_SIZE,
        "point_id_strategy": "deterministic_uuid5_from_document_id",
        "upload_time": elapsed,
        "upload_time_unit": "seconds",
        "status": "READY" if ready else "UPLOAD_FAILED",
        "completed_at": utc_now(),
    }
    write_json(REPORTS_DIR / "upload_report.json", report)
    if not ready:
        raise RuntimeError("One or more vector batches failed to upload")
    print(f"Uploaded {uploaded} vectors in {elapsed} seconds")


if __name__ == "__main__":
    main()
