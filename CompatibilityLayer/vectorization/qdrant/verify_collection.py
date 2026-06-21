from qdrant_client.models import Filter, FieldCondition, MatchValue

from qdrant_common import (
    COLLECTION_NAME,
    REPORTS_DIR,
    VECTOR_SIZE,
    get_client,
    read_json,
    utc_now,
    vector_config,
    write_json,
    write_readiness_report,
)


def main():
    client = get_client()
    exists = client.collection_exists(COLLECTION_NAME)
    expected = read_json(REPORTS_DIR / "upload_report.json").get("vectors_uploaded", 0)
    actual = 0
    payload_count = 0
    actual_size = None
    actual_distance = None
    if exists:
        info = client.get_collection(COLLECTION_NAME)
        actual_size, actual_distance = vector_config(info)
        actual = client.count(collection_name=COLLECTION_NAME, exact=True).count
        payload_count = client.count(
            collection_name=COLLECTION_NAME,
            count_filter=Filter(
                must=[FieldCondition(key="layer", match=MatchValue(value="Layer3"))]
            ),
            exact=True,
        ).count

    upload_report = read_json(REPORTS_DIR / "upload_report.json")
    no_failed_vectors = not upload_report.get("failures")
    ready = all(
        (
            exists,
            actual_size == VECTOR_SIZE,
            actual_distance == "cosine",
            actual == expected,
            payload_count == actual,
            no_failed_vectors,
        )
    )
    report = {
        "collection_exists": exists,
        "collection_name": COLLECTION_NAME,
        "vector_count": actual,
        "expected_vector_count": expected,
        "payload_point_count": payload_count,
        "payload_exists_for_all_points": payload_count == actual and actual > 0,
        "embedding_dimension": actual_size,
        "distance": actual_distance,
        "failed_vectors": len(upload_report.get("failures", [])),
        "status": "READY" if ready else "INTEGRITY_FAILED",
        "checked_at": utc_now(),
    }
    write_json(REPORTS_DIR / "collection_integrity_report.json", report)
    write_readiness_report()
    if not ready:
        raise RuntimeError("Collection integrity validation failed")
    print(f"Verified {actual} collection points and payloads")


if __name__ == "__main__":
    main()
