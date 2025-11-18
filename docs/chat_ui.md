# Chat UI & Assistant Endpoints

Codex AOTGraph now exposes AI-facing tooling through new REST endpoints and a
simple chat interface.

## Endpoints

- `POST /assistant/search` – semantic retrieval over the embeddings store.
- `POST /assistant/explain` – combine node properties, summary text, and
  immediate neighbors.
- `POST /assistant/method-source` – fetch stored method body/source metadata.

These routes rely on `AssistantToolkit` (`src/assistant/toolkit.py`), which
wraps `GraphQueryService` and the vector store for reuse by future LLM agents.

## UI

Visit `/assistant` to access a lightweight chat-style dashboard that calls the
endpoints above. It supports:

- Free-form semantic search with optional label filtering.
- Node explanation by ID.
- Retrieval of x++ method source snippets for grounding LLM responses.

Set `CODXA_EMBEDDINGS_DB` and `CODXA_EMBEDDINGS_DIM` environment variables to
point the API at the generated embeddings database (defaults to
`data/embeddings.db` and dimension `384`).


