# Retrieval Layer

This layer performs deterministic semantic retrieval against the Layer 1 and Layer 3 Qdrant collections. It does not call an LLM. Query embeddings use `BAAI/bge-base-en-v1.5`, and answers are assembled only from returned payload fields.

## Components

- `query_router.py` classifies queries as `DOMAIN`, `COMPATIBILITY`, or `HYBRID`.
- `retriever.py` creates query embeddings and searches a Qdrant collection.
- `search_service.py` exposes Layer 1, Layer 3, and combined search with configurable `top_k`.
- `answer_builder.py` creates grounded answers with sources and similarity-derived confidence.
- `run_retrieval_evaluation.py` runs the complete test suite and writes reports.

## Environment

The project-root `.env` must define `QDRANT_URL` and `QDRANT_API_KEY`. Credentials are never hardcoded or written to reports.

Expected collections:

- `kb_domain_layer`
- `kb_compatibility_layer`

Both collections must use 768-dimensional vectors produced by `BAAI/bge-base-en-v1.5`.

Search returns up to `top_k` grounded results. To avoid adding weak tail neighbors to an answer, results must score at least `0.50` and remain within `0.10` cosine similarity of the best result for that query.

## Run

```powershell
python retrieval/run_retrieval_evaluation.py
```

Generated reports are written to `retrieval/reports/`. The final status is `READY_FOR_LAYER_INTEGRATION` only when both collections exist, at least 90% of questions are answered with sources, no more than 10% are empty, no search failures occur, and average similarity is greater than 0.70.

## Ask Questions Interactively

Start the terminal console:

```powershell
python retrieval/ask.py
```

Enable extra grounding information inside the console:

```text
/verify on
```

Other commands are `/topk 5`, `/route auto`, `/route domain`, `/route compatibility`, `/route hybrid`, `/help`, and `/quit`.

Run and verify one question without entering interactive mode:

```powershell
python retrieval/ask.py --question "Which BIOS and firmware versions are incompatible?" --verify
```

Every response includes the selected route, Qdrant source IDs, collection names, cosine scores, summary, detailed source content, and similarity-derived confidence. This makes it possible to compare each answer directly with its retrieved evidence.

## Questions You Can Ask

Domain questions ask what a component is or what it does:

- What is BIOS?
- What is UEFI?
- What is TPM?
- What is Secure Boot?
- What does a graphics driver do?
- What is endpoint management?
- What is Windows 11?
- What is embedded controller firmware?

Compatibility questions ask about rules, versions, requirements, and conflicts:

- Which BIOS and firmware versions are incompatible?
- Which driver pack is required for Enterprise OS 2026.1?
- What minimum version is required for Security Agent 4.8.3?
- What update order must be followed for BIOS and firmware?
- Which Enterprise OS versions support Platform Driver Pack 12.5.0?
- What remediation is recommended for unsupported versions?
- Which rule describes support for SIEM connectors?
- What causes non-compliance?

Hybrid questions combine component knowledge with compatibility behavior:

- How does firmware impact compliance?
- How do drivers affect compatibility?
- How does BIOS affect firmware compatibility?
- How does an operating system version influence driver compatibility?
- What dependencies between BIOS and firmware must be checked?
- How does an endpoint management agent affect security agent compatibility?

The complete 50-question validation set is available in `retrieval/tests/retrieval_questions.json`.
