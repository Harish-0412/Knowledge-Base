# LLM Infrastructure Guide

## Architecture

The LLM infrastructure layer provides a small, explicit boundary around three
external systems:

- **Ollama** hosts `llama3.1:8b` and exposes completion and chat APIs.
- **LlamaIndex** provides the application-facing LLM abstraction used by future
  RAG, root-cause analysis, recommendation, and conversational chains.
- **Qdrant** stores domain knowledge and compatibility-rule vectors.
- **Neo4j** stores inventory and graph relationships used for hybrid retrieval.

`services/llm_service.py` is the central generation interface. The connectors
perform connectivity and resource validation without embedding credentials in
source control. `validate_infrastructure.py` regenerates both health reports.

## Folder Structure

```text
ReasoningLayer/llm/
|-- configs/       JSON runtime defaults and resource names
|-- connectors/    Ollama, Qdrant, and Neo4j adapters
|-- services/      Central LlamaIndex LLM service
|-- prompts/       Future versioned prompt templates
|-- chains/        Future RAG and reasoning chains
|-- tests/         Live connectivity tests
|-- reports/       Generated dependency and health reports
`-- docs/          Operations documentation
```

## Configuration

The JSON files under `configs/` define non-secret defaults. Environment
variables override connection values. Keep credentials in the project-root
`.env` file and do not place resolved secrets in the JSON files or reports.

| Variable | Required | Default |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` |
| `OLLAMA_MODEL` | No | `llama3.1:8b` |
| `OLLAMA_TIMEOUT` | No | `120` |
| `QDRANT_URL` | Yes | none |
| `QDRANT_API_KEY` | Cloud clusters | none |
| `NEO4J_URI` | No | `bolt://localhost:7687` |
| `NEO4J_USERNAME` | No | `neo4j` |
| `NEO4J_PASSWORD` | Yes | none |
| `NEO4J_DATABASE` | No | `neo4j` |

Qdrant compliance requires collections named `domain_knowledge` and
`compatibility_rules`. Similar collection names are not automatically treated
as aliases because doing so could route retrieval to an incompatible schema.

## Ollama Setup

Install Ollama, pull the model, and confirm it is listed:

```powershell
ollama pull llama3.1:8b
ollama list
```

The connector calls `/api/tags`, `/api/generate`, and `/api/chat`. A successful
health check requires the server to respond and the exact configured model name
to appear in the model list.

## Qdrant Setup

Set `QDRANT_URL` and, for Qdrant Cloud, `QDRANT_API_KEY`. Provision both required
collections with the vector dimensions and distance metric used by the embedding
pipeline. This layer validates connectivity, names, and collection statistics;
it intentionally does not create, migrate, or delete collections.

## Neo4j Setup

Start Neo4j, set the four `NEO4J_*` variables, and ensure the configured user can
run read queries against the configured database. Health validation runs
`RETURN 1 AS result`. `get_database_stats()` performs a read-only node and
relationship count.

## Testing

Install dependencies and run the live test group from the repository root:

```powershell
python -m pip install llama-index llama-index-llms-ollama qdrant-client neo4j requests pytest
python -m pytest ReasoningLayer/llm/tests -v
python -m ReasoningLayer.llm.validate_infrastructure
```

The validator always writes:

- `reports/dependency_validation.json`
- `reports/infrastructure_health_report.json`

It exits with code `0` only when every dependency and external system passes.

## Troubleshooting

- **Ollama connection refused:** start the Ollama application or `ollama serve`,
  then retry `/api/tags` at the configured base URL.
- **Model missing:** run `ollama pull llama3.1:8b` or update `OLLAMA_MODEL` and
  `llm_config.json` together.
- **Qdrant authentication failure:** verify the URL, API key, cluster status, and
  outbound HTTPS access.
- **Qdrant collection failure:** provision the exact required names or update the
  infrastructure contract only after confirming schema compatibility.
- **Neo4j password not configured:** add `NEO4J_PASSWORD` to `.env`.
- **Neo4j connection refused:** confirm the Bolt port, URI scheme, database name,
  firewall rules, and user permissions.
- **LlamaIndex import error:** install both `llama-index` and
  `llama-index-llms-ollama` into the Python environment running the tests.

## Future Integration Points

Future RAG chains can combine Qdrant semantic results with Neo4j inventory paths,
then pass grounded context through `LLMService`. The same service boundary can be
used by the root-cause analyzer, recommendation engine, and conversational
assistant. Add prompt templates under `prompts/` and orchestration under
`chains/`; keep retrieval and model configuration outside chain code so models,
ranking, and stores can evolve independently.
