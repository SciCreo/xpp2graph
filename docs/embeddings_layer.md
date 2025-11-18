# Embeddings Layer

Phase 2 adds semantic search on top of the AOT graph. The implementation lives
under `src/embeddings/` and consists of:

- `client.py` – interfaces for embedding providers (`HashEmbeddingClient` is a
  deterministic placeholder; swap in OpenAI/Azure later).
- `text.py` – `NodeTextBuilder` extracts descriptive text for classes, methods,
  tables, and fields by traversing Neo4j.
- `store.py` – lightweight SQLite-backed vector store with cosine similarity.
- `pipeline.py` – orchestration that generates embeddings, writes them to the
  store, and supports similarity search.
- `__main__.py` – CLI entry point for generating embeddings or running ad-hoc
  searches (`python -m src.embeddings --store data/embeddings.db`).

The pipeline defaults to the hash-based embedding client so it can run without
external services. Replace it with a real provider by implementing
`EmbeddingClient` and passing it to `EmbeddingPipeline.default(..)`.


