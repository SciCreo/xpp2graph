# Codex AOTGraph IR & Graph Schema

This document summarizes the intermediate representation (IR) structures and the
Neo4j schema that underpin the Codex AOTGraph ingestion pipeline.

## Intermediate Representation

The IR bridges AOT XML exports and the graph database. Core definitions live in
`src/ir/models.py` and consist of typed dataclasses with deterministic element
IDs derived from AOT paths and model names.

- `ClassIR` – Represents a class node with metadata, inheritance chain, and a
  dictionary of `MethodIR` instances.
- `MethodIR` – Captures method signature details, access levels, static flag,
  source body, inferred line counts, and references to called methods and field
  accesses.
- `TableIR` – Represents a table with owned `FieldIR` instances and model
  packaging metadata.
- `FieldIR` – Encodes individual table fields, including EDT and primitive type.
- `FieldAccessIR` – Lightweight record of reads/writes that drive
  `[:READS_FIELD]` and `[:WRITES_FIELD]` relationships during graph load.

Helper utilities ensure consistent synthetic IDs (e.g.
`Model/Class/MethodName`) so that repeated imports remain idempotent.

## Graph Schema

Graph metadata is defined in `src/graph/schema.py`, centralizing node labels,
relationship names, and index/constraint expectations.

- Node labels: `Class`, `Method`, `Table`, `Field`, `Model`, `Package`.
- Relationships: `EXTENDS`, `DECLARES_METHOD`, `HAS_FIELD`, `CALLS`,
  `READS_FIELD`, `WRITES_FIELD`, `BELONGS_TO_MODEL`.
- `SchemaMetadata` enumerates unique keys and secondary indexes per label to
  guide constraint creation inside Neo4j.

The loader layer will rely on `format_node_properties` to normalize property
payloads prior to upsert, ensuring that null values are omitted and casing is
consistent.

Together, the IR and schema definitions provide the contractual boundary for
subsequent phases: the ingestion pipeline, API surfaces, and the AI assistant.


