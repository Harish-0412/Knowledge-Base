from qdrant_client.models import Distance, PayloadSchemaType, VectorParams

from qdrant_common import (
    COLLECTION_NAME,
    REPORTS_DIR,
    VECTOR_SIZE,
    distance_name,
    get_client,
    utc_now,
    vector_config,
    write_json,
)


def main():
    connection_report = {
        "collection_endpoint_reachable": False,
        "authentication_succeeded": False,
        "api_key_valid": False,
        "status": "FAILED",
        "checked_at": utc_now(),
    }
    try:
        client = get_client()
        client.get_collections()
        connection_report.update(
            {
                "collection_endpoint_reachable": True,
                "authentication_succeeded": True,
                "api_key_valid": True,
                "status": "CONNECTED",
            }
        )
    except Exception as exc:
        connection_report["error"] = str(exc)
        write_json(REPORTS_DIR / "qdrant_connection_report.json", connection_report)
        raise
    write_json(REPORTS_DIR / "qdrant_connection_report.json", connection_report)

    created = False
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        created = True

    info = client.get_collection(COLLECTION_NAME)
    actual_size, actual_distance = vector_config(info)
    configuration_valid = actual_size == VECTOR_SIZE and actual_distance == "cosine"
    index_definitions = {
        "document_id": PayloadSchemaType.KEYWORD,
        "rule_id": PayloadSchemaType.KEYWORD,
        "rule_type": PayloadSchemaType.KEYWORD,
        "subject": PayloadSchemaType.KEYWORD,
        "predicate": PayloadSchemaType.KEYWORD,
        "object": PayloadSchemaType.KEYWORD,
        "status": PayloadSchemaType.KEYWORD,
        "confidence": PayloadSchemaType.FLOAT,
        "source": PayloadSchemaType.KEYWORD,
        "layer": PayloadSchemaType.KEYWORD,
    }
    if configuration_valid:
        for field_name, field_schema in index_definitions.items():
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field_name,
                field_schema=field_schema,
                wait=True,
            )

    refreshed = client.get_collection(COLLECTION_NAME)
    indexed_fields = sorted(refreshed.payload_schema.keys())
    expected_fields = sorted(index_definitions.keys())
    payload_schema_valid = all(field in indexed_fields for field in expected_fields)
    ready = configuration_valid and payload_schema_valid
    report = {
        "collection_name": COLLECTION_NAME,
        "created": created,
        "existing_collection_preserved": not created,
        "expected_vector_size": VECTOR_SIZE,
        "actual_vector_size": actual_size,
        "expected_distance": "Cosine",
        "actual_distance": actual_distance,
        "payload_enabled": True,
        "payload_indexed_fields": indexed_fields,
        "configuration_valid": configuration_valid,
        "payload_schema_valid": payload_schema_valid,
        "status": "READY" if ready else "CONFIGURATION_MISMATCH",
        "checked_at": utc_now(),
    }
    write_json(REPORTS_DIR / "collection_creation_report.json", report)
    if not ready:
        raise RuntimeError("Existing collection configuration or payload schema does not match requirements")
    print(f"Collection {COLLECTION_NAME}: {'created' if created else 'verified'}")


if __name__ == "__main__":
    main()
