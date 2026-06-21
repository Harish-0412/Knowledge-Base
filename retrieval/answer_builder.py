def _first(payload, keys):
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _content(result):
    payload = result["payload"]
    direct = _first(payload, ("text", "content", "description", "definition", "summary"))
    if direct:
        return direct
    subject = payload.get("subject")
    predicate = payload.get("predicate")
    object_value = payload.get("object")
    if subject and predicate and object_value:
        sentence = f"{subject} {predicate} {object_value}."
        status = payload.get("status")
        if status:
            sentence += f" Status: {status}."
        return sentence
    name = payload.get("name") or payload.get("entity_name")
    purpose = payload.get("purpose")
    if name and purpose:
        return f"{name}: {purpose}"
    return None


def _source(result):
    payload = result["payload"]
    identifier = (
        payload.get("document_id")
        or payload.get("entity_id")
        or payload.get("rule_id")
        or result["point_id"]
    )
    return {
        "collection": result["collection"],
        "source_id": identifier,
        "source": payload.get("source") or payload.get("layer") or result["collection"],
        "score": round(result["score"], 6),
    }


class AnswerBuilder:
    def build(self, question, search_response):
        grounded = [(result, _content(result)) for result in search_response["results"]]
        grounded = [(result, content) for result, content in grounded if content]
        sources = [_source(result) for result, _ in grounded]
        details = [content for _, content in grounded]
        scores = [result["score"] for result, _ in grounded]
        average_score = sum(scores) / len(scores) if scores else 0.0
        level = "HIGH" if average_score >= 0.75 else "MEDIUM" if average_score >= 0.60 else "LOW"
        return {
            "question": question,
            "route": search_response["route"],
            "retrieved_sources": sources,
            "summary": details[0] if details else "",
            "detailed_explanation": details,
            "confidence": {
                "level": level if details else "NONE",
                "score": round(average_score, 6),
                "method": "mean cosine similarity of grounded retrieved sources",
            },
            "answered": bool(details and sources),
            "grounded_only": True,
            "errors": search_response.get("errors", []),
        }
