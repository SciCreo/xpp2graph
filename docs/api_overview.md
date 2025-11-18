# API Overview

Codex AOTGraph exposes a FastAPI service that surfaces key developer queries
over the Neo4j knowledge graph.

## Endpoints

- `GET /health` – simple uptime probe.
- `GET /where-used/method` – callers of a method.
  - Query params: `className`, `methodName`, optional `model`.
- `GET /field-access` – methods reading and writing a field.
  - Query params: `tableName`, `fieldName`, optional `model`.
- `GET /class-hierarchy` – inheritance chain for a class.
  - Query params: `className`, optional `model`.

## Running the API

Set the same Neo4j environment variables used by the ingestion pipeline. Then:

```bash
uvicorn src.api.server:create_app --factory --reload
```

The server lazily loads Neo4j credentials from environment variables and
instantiates the `GraphQueryService` for each request.


