# Codex AOTGraph

Give your Microsoft Dynamics 365 F&O codebase a living, queryable brain powered by a Neo4j knowledge graph, semantic embeddings, and an AI-ready toolchain.

Codex AOTGraph ingests AOT XML exports, turns them into a richly linked graph, exposes a developer-friendly API and explorer, and layers on embeddings plus assistant tooling for semantic navigation and impact analysis.

---

## Highlights

- **Graph-native AOT model** – Classes, tables, fields, and methods become first-class nodes with dependency edges (`CALLS`, `READS_FIELD`, `WRITES_FIELD`, `EXTENDS`, …).
- **Repeatable ingestion pipeline** – Parse XML exports (or zip archives) into an intermediate representation and sync them into Neo4j with idempotent upserts.
- **Developer APIs & UI** – FastAPI service exposing where-used, field access, class hierarchy queries, and minimal web explorers at `/explorer` and `/assistant`.
- **Embeddings & semantic search** – Hash-based embeddings out of the box (swap in a managed provider later) with a SQLite-backed vector store for RAG-style workflows.
- **Assistant toolkit** – Orchestrates graph traversal, semantic retrieval, and source fetches to ground LLM agents in real project knowledge.

---

## Repository Layout

| Path | Purpose |
| --- | --- |
| `src/ir/` | Intermediate Representation dataclasses (classes, methods, tables, fields) |
| `src/pipeline/` | XML parser and ingestion pipeline that loads Neo4j |
| `src/graph/` | Schema metadata and Neo4j loader helpers |
| `src/api/` | FastAPI app, query service, and Pydantic models |
| `src/ui/templates/` | Minimal HTML explorers for graph queries and assistant workflows |
| `src/embeddings/` | Embedding client, vector store, text extraction, and CLI |
| `src/assistant/` | Toolkit combining graph and embeddings for AI agents |
| `docs/` | Supplemental documentation for each layer |

Key documentation:

- `docs/ir_schema_overview.md`
- `docs/ingestion_pipeline.md`
- `docs/api_overview.md`
- `docs/explorer_ui.md`
- `docs/embeddings_layer.md`
- `docs/assistant_tooling.md`
- `docs/chat_ui.md`

---

## Quick Start

### 1. Clone & prerequisites

- Python 3.11+
- Docker & Docker Compose v2 (optional but recommended)
- Access to Dynamics 365 F&O AOT XML exports

### 2. Environment variables

The application reads the following variables (set them locally or via Docker Compose):

| Variable | Description | Default |
| --- | --- | --- |
| `CODXA_NEO4J_URI` | Bolt connection string | `bolt://localhost:7687` |
| `CODXA_NEO4J_USER` | Neo4j username | – |
| `CODXA_NEO4J_PASSWORD` | Neo4j password | – |
| `CODXA_NEO4J_DATABASE` | Target database | `neo4j` |
| `OPENAI_API_KEY` | Required for embeddings & assistant search | – |
| `OPENAI_EMBED_MODEL` | OpenAI embedding model | `text-embedding-3-large` |
| `OPENAI_API_BASE` | Optional custom OpenAI base URL | – |
| `CODXA_KEYWORD_INDEX_NAME` | Neo4j fulltext index name | `codex_keyword_index` |
| `CODXA_VECTOR_INDEX_NAME` | Neo4j vector index name | `codex_vector_index` |
| `CODXA_VECTOR_DIMENSIONS` | Embedding vector dimensions | `2048` |

---

## Running with Docker Compose

The repository ships with a ready-to-use Dockerfile and `docker-compose.yml` that launch:

- `neo4j` – Neo4j 5 community edition (with APOC)
- `api` – Codex AOTGraph FastAPI service served by Uvicorn

```bash
# Prepare local bind mounts for data persistence
mkdir -p neo4j/data neo4j/logs neo4j/plugins

# Build images and start services
docker compose up --build
```

Services:

- API: http://localhost:8000 (health at `/health`, graph explorer at `/explorer`, assistant UI at `/assistant`)
- Neo4j Browser: http://localhost:7474 (credentials `neo4j/devpassword` by default)

Stop everything with `docker compose down`. To nuke volumes, add `--volumes`.

---

## Manual Development Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Export required environment variables.
   ```powershell
   # PowerShell helper to load values from .env into the current session
   ./scripts/export-env.ps1
   # or specify a custom path
   ./scripts/export-env.ps1 -EnvPath .env.sample
   ```
4. Run the FastAPI server:
   ```bash
   uvicorn src.api.server:create_app --factory --reload
   ```
5. Ingest AOT XML exports or zip archives (repeat as needed):
   ```bash
   python -m src.pipeline path/to/export1.xml path/to/dir/of/xmls
   python -m src.pipeline path/to/AOTExport.zip
   # Optional flags
   python -m src.pipeline --staging-dir ./tmp --keep-extracted samples/MessageProcessor.zip
   ```
6. Generate embeddings (optional but recommended for semantic search / assistant):
   ```bash
   python -m src.embeddings --batch-size 64
   ```
   (requires `OPENAI_API_KEY`)

---

## Features in Depth

### Ingestion Pipeline

- Parses AOT XML into structured dataclasses.
- Computes method call graphs and field read/write relationships.
- Upserts nodes and edges into Neo4j with unique constraints and indexes.
- CLI entry point: `python -m src.pipeline` (accepts files, directories, or zip archives).

More: `docs/ingestion_pipeline.md`

### Graph API & Explorer

- REST endpoints for where-used, field-access, and class hierarchy queries.
- HTML explorer (`/explorer`) for quick, code-free graph inspection.

More: `docs/api_overview.md`, `docs/explorer_ui.md`

### Embeddings & Assistant

- `python -m src.embeddings` builds semantic vectors for methods, classes, tables, and fields.
- `src/assistant.toolkit.AssistantToolkit` combines graph traversal with embeddings for agent workflows.
- `/assistant` UI exposes semantic search, explain node, and method source retrieval.

More: `docs/embeddings_layer.md`, `docs/assistant_tooling.md`, `docs/chat_ui.md`

---

## Development Notes

- Targeted at Neo4j 5.x community edition; adjust connection settings if you run Enterprise or Aura.
- Default embeddings use a deterministic hash-based client—swap in OpenAI/Azure by implementing `EmbeddingClient`.
- Keep AOT exports under version control only if sanitized; otherwise mount them in at runtime.
- The repo is ASCII-first; avoid introducing non-ASCII characters unless they already exist in source assets.

---

## Roadmap Ideas

- Real embedding providers & managed vector stores.
- VS Code / Visual Studio extensions powered by the assistant toolkit.
- Advanced static analysis for more precise call graphs.
- ScientiaMesh integration as a dedicated “code mesh.”

---

## License

Choose and document a license before public release. (The repository currently has no explicit license.)

---

## Contributing

Issues and pull requests are welcome! Please open an issue describing the improvement or bugfix you have in mind. For major changes, discuss via an issue first to align on direction.


