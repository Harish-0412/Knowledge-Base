import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from sentence_transformers import SentenceTransformer


DOMAIN_ROOT = Path(__file__).resolve().parent.parent
NORMALIZED_DIR = DOMAIN_ROOT / "normalized"
OUTPUT_ROOT = Path(__file__).resolve().parent
DOCUMENTS_DIR = OUTPUT_ROOT / "generated_documents"
EMBEDDINGS_DIR = OUTPUT_ROOT / "embeddings"
MODEL_NAME = "BAAI/bge-base-en-v1.5"
VECTOR_SIZE = 768


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=True, indent=2)
        handle.write("\n")


def sentence_list(values):
    return ", ".join(str(value) for value in values) if values else "None documented"


def semantic_text(entity):
    return "\n\n".join(
        (
            "Domain Knowledge Entity",
            f"Name:\n{entity['name']}",
            f"Entity Type:\n{entity['type']}",
            f"Subtype:\n{entity['subtype']}",
            f"Knowledge Category:\n{entity['knowledge_category']}",
            f"Description:\n{entity['description']}",
            f"Purpose:\n{entity['purpose']}",
            f"Aliases:\n{sentence_list(entity['aliases'])}",
            f"Keywords:\n{sentence_list(entity['keywords'])}",
            f"Related Entities:\n{sentence_list(entity['related_entities'])}",
            f"Compatibility Relevance:\n{entity['compatibility_relevance']}",
            f"Validation Priority:\n{entity['validation_priority']}",
        )
    )


def main():
    entities = []
    for path in sorted(NORMALIZED_DIR.glob("*.json")):
        with path.open("r", encoding="utf-8-sig") as handle:
            records = json.load(handle)
        for record in records:
            record["source_file"] = path.name
            entities.append(record)

    entity_ids = [entity["entity_id"] for entity in entities]
    duplicate_ids = len(entity_ids) - len(set(entity_ids))
    documents = []
    for entity in entities:
        documents.append(
            {
                "document_id": f"DOMAIN-DOC-{entity['entity_id']}",
                "document_type": "domain_entity",
                "text": semantic_text(entity),
                "metadata": {
                    "entity_id": entity["entity_id"],
                    "name": entity["name"],
                    "type": entity["type"],
                    "subtype": entity["subtype"],
                    "knowledge_category": entity["knowledge_category"],
                    "domain_layer": entity["layer"],
                    "compatibility_relevance": entity["compatibility_relevance"],
                    "validation_priority": entity["validation_priority"],
                    "source_file": entity["source_file"],
                    "source": "DomainLayer",
                },
            }
        )

    document_failures = []
    if duplicate_ids:
        document_failures.append(f"Found {duplicate_ids} duplicate entity IDs")
    if any(not document["text"].strip() for document in documents):
        document_failures.append("One or more semantic documents are empty")
    write_json(DOCUMENTS_DIR / "domain_documents.json", documents)
    write_json(
        DOCUMENTS_DIR / "document_generation_report.json",
        {
            "entities_found": len(entities),
            "documents_generated": len(documents),
            "duplicates": duplicate_ids,
            "empty_documents": sum(not document["text"].strip() for document in documents),
            "failures": document_failures,
            "status": "READY_FOR_EMBEDDING" if not document_failures else "VALIDATION_FAILED",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    if document_failures:
        raise RuntimeError("Domain document generation validation failed")

    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode(
        [document["text"] for document in documents],
        batch_size=8,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    embeddings = []
    embedding_failures = []
    for document, vector in zip(documents, vectors):
        values = vector.astype(float).tolist()
        if len(values) != VECTOR_SIZE or not all(math.isfinite(value) for value in values):
            embedding_failures.append(document["document_id"])
        embeddings.append(
            {
                "document_id": document["document_id"],
                "embedding": values,
                "dimension": len(values),
                "text": document["text"],
                "metadata": document["metadata"],
            }
        )
    write_json(EMBEDDINGS_DIR / "domain_embeddings.json", embeddings)
    write_json(
        EMBEDDINGS_DIR / "embedding_generation_report.json",
        {
            "documents_processed": len(documents),
            "embeddings_generated": len(embeddings),
            "embedding_dimension": VECTOR_SIZE,
            "model_used": MODEL_NAME,
            "failures": embedding_failures,
            "status": "READY_FOR_QDRANT_UPLOAD" if not embedding_failures else "VALIDATION_FAILED",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    if embedding_failures:
        raise RuntimeError("Domain embedding validation failed")
    print(f"Generated {len(documents)} domain documents and {len(embeddings)} embeddings")


if __name__ == "__main__":
    main()
