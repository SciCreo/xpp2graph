# Chat UI & Assistant Endpoints

Codex AOTGraph now exposes AI-facing tooling through new REST endpoints and a
simple chat interface.

## Endpoints

- `POST /assistant/search` – semantic retrieval over the embeddings store.
- `POST /assistant/explain` – combine node properties, summary text, and
  immediate neighbors.
- `POST /assistant/method-source` – fetch stored method body/source metadata.

These routes rely on `AssistantToolkit` (`src/assistant/toolkit.py`), which
wraps Neo4j vector/full-text queries plus an OpenAI embedding client for reuse
by future LLM agents.

## UI

Visit `/assistant` to access a lightweight chat-style dashboard that calls the
endpoints above. It supports:

- Free-form semantic search with optional label filtering.
- Node explanation by ID.
- Retrieval of x++ method source snippets for grounding LLM responses.

Ensure the following environment variables are available to the API container:

- `OPENAI_API_KEY`
- `OPENAI_EMBED_MODEL` (defaults to `text-embedding-3-large`)
- `CODXA_VECTOR_INDEX_NAME` and `CODXA_KEYWORD_INDEX_NAME` (must match the names
  created during ingestion)
