# Ingestion Pipeline Overview

Codex AOTGraph ships with a repeatable pipeline for converting Dynamics 365 F&O
AOT XML exports into the Neo4j knowledge graph.

## Components

- `src/pipeline/parser.py` – resilient XML parser that maps classes, methods,
  tables, and fields into the IR dataclasses (`src/ir/models.py`).
- `src/graph/loader.py` – Neo4j loader that creates nodes, maintains indexes and
  constraints, and establishes edges (`EXTENDS`, `DECLARES_METHOD`, etc.).
- `src/pipeline/ingest.py` – orchestration layer that wires the parser and the
  loader together and returns ingestion statistics.
- `src/pipeline/__main__.py` – CLI entry point; run with `python -m src.pipeline`.

## Running the Pipeline

1. Set the required Neo4j environment variables:
   - `CODXA_NEO4J_URI`
   - `CODXA_NEO4J_USER`
   - `CODXA_NEO4J_PASSWORD`
   - Optional: `CODXA_NEO4J_DATABASE`
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Ingest one or more XML exports:
   ```bash
   python -m src.pipeline path/to/AxClass.xml path/to/AxTable.xml
   ```

The pipeline automatically discovers XML files inside directories, enforces
required Neo4j constraints, and reports the number of classes, methods, tables,
and fields processed.


