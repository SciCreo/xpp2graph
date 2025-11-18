# Embeddings Layer

Phase 2 adds semantic search on top of the AOT graph. The implementation lives
under `src/embeddings/` and now stores vector data directly in Neo4j so that the
graph remains the single source of truth.

Key components:

- `client.py` – embedding client abstractions, including the production
  `OpenAIEmbeddingClient` (targets `text-embedding-3-large` by default).
- `text.py` – `NodeTextBuilder` traverses Neo4j to produce searchable summaries
  and metadata for classes, methods, tables, and fields.
- `pipeline.py` – orchestrates text extraction, calls OpenAI for embeddings, and
  writes results back onto nodes (`summary`, `embedding`, `searchMetadata`,
  `searchLabel`, `searchUpdatedAt`, and the `:Searchable` label).
- `__main__.py` – CLI entry point for generating embeddings
  (`python -m src.embeddings --batch-size 64`).

During ingestion or refresh runs the pipeline:

1. Loads Neo4j connection details.
2. Creates OpenAI embeddings for each node description.
3. Updates the node in-place with the embedding vector and searchable summary.
4. Relies on Neo4j vector and full-text indexes (`codex_vector_index`,
   `codex_keyword_index`) for fast retrieval.

The assistant toolkit and API query these indexes via Cypher
(`CALL db.index.vector.queryNodes` and `CALL db.index.fulltext.queryNodes`),
removing the need for an external vector store.
