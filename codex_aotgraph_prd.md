# Codex AOTGraph – Product Requirements Document (PRD)

## 0. Summary

Codex AOTGraph is a developer assistant for Microsoft Dynamics 365 F&O (x++) teams, powered by a knowledge graph of the Application Object Tree (AOT).

Phase 1 builds an **x++ → AOT Graph ingestion pipeline** and a **Neo4j-backed knowledge graph** that represents classes, methods, tables, fields, and their relationships.

Phase 2 adds an **AI coding assistant** that uses this graph (plus embeddings) to:
- Answer code-navigation and impact-analysis questions
- Suggest examples and patterns following the existing codebase
- Speed up development and reduce regression risk

The first internal customer is Rod’s Dynamics team (ex‑Thinkmax), with the long‑term goal of becoming a specialized productivity tool for Dynamics partners and F&O dev shops.

---

## 1. Background & Context

- Dynamics 365 F&O uses x++ and the AOT (Application Object Tree) structure.
- The AOT is inherently graph-shaped (classes ⇄ tables ⇄ forms ⇄ menu items ⇄ services ⇄ events).
- Today, navigation is done through:
  - Visual Studio AOT browser
  - Built-in “where-used” features (limited)
  - Manual search/grep
- Teams repeatedly face:
  - Difficulty understanding impact: “If I change this field/method, what breaks?”
  - Fragmented knowledge about patterns and best practices
  - Onboarding time for new devs to understand local customizations

At the same time, AI code assistants (Copilot, ChatGPT, etc.) are powerful but **blind to the specific AOT graph and project‑specific patterns**. They hallucinate or suggest generic x++ that ignores local extensions and conventions.

Codex AOTGraph fills this gap by giving the codebase an explicit, queryable brain.

---

## 2. Problem Statement

Dynamics 365 F&O development teams lack a precise, navigable representation of their AOT that can be leveraged by both humans and AI.

This leads to:
- Slow impact analysis and refactoring
- Hard-to-answer questions like:
  - “Who writes to this field?”
  - “Where is this method called?”
  - “Which tables and forms are involved in this business process?”
- AI assistants that generate code without awareness of:
  - Existing patterns
  - Local extensions
  - Domain-specific constraints

We want to:
- Turn the AOT into a knowledge graph
- Make that graph queryable by humans (DevTools, UI) and AI (tooling/RAG)

---

## 3. Vision

> **Give every Dynamics F&O team a living map of their codebase that both humans and AI can navigate and extend.**

Longer term:
- Codex AOTGraph becomes the **foundation layer** for:
  - AI pair-programming for x++
  - Automated impact analysis and change‑risk scoring
  - Design documentation generated from the graph
  - Cross‑project pattern mining

---

## 4. Goals & Non‑Goals (Phase 1–2)

### 4.1 Goals (Phase 1 – Graph Foundation)

1. Ingest x++ AOT XML exports into a structured Intermediate Representation (IR).
2. Populate a Neo4j (or similar) graph with key entities and relationships:
   - Classes, methods, tables, fields
   - Class inheritance (`EXTENDS`)
   - Method declarations and basic call graph
   - Table/field ownership
3. Provide usable graph APIs & queries for:
   - “Where is this method used?”
   - “Which methods read/write this field?”
   - “What does this class extend/override?”
4. Deliver a minimal UI or CLI for interactive exploration and simple visualizations.

### 4.2 Goals (Phase 2 – AI Assistant)

5. Add semantic search over methods/classes using embeddings.
6. Provide an AI assistant that can:
   - Explain what a class/method/table does, based on graph + code
   - Suggest code changes or new methods reusing existing patterns
   - Guide developers through impact analysis (”what does this change touch?”)
7. Expose the assistant through:
   - Chat UI (web or VS Code/VS extension)
   - API surface for future integrations

### 4.3 Non‑Goals (for now)

- Full static analysis of x++ (dataflow, sophisticated type inference).
- Real-time syncing with live F&O environments.
- Automated code refactoring / code generation that directly commits changes.
- Support for non‑x++ languages.

---

## 5. Target Users & Personas

### 5.1 Primary Persona – Dynamics Senior Dev / Architect (Rod)

- Works daily in x++ and the AOT.
- Responsible for complex features, refactors, and debugging.
- Pain points:
  - Time-consuming impact analysis.
  - Difficulty explaining architecture to juniors.
  - Fear of regressions when touching central objects.
- Success looks like:
  - “I can see quickly who depends on this thing.”
  - “I can ask: what breaks if I change X?”

### 5.2 Secondary Persona – Intermediate / Junior x++ Dev

- Still learning the ERP and local customizations.
- Asks a lot of “Where is this used?” and “How do we usually do X here?”
- Success looks like:
  - Faster onboarding.
  - AI explanations grounded in the project’s own code.

### 5.3 Tertiary Persona – Dynamics Practice Lead / Manager

- Oversees a team of devs.
- Cares about delivery speed, quality, and maintainability.
- Success looks like:
  - Fewer regressions.
  - Easier onboarding.
  - Ability to reason about complexity hotspots.

---

## 6. Use Cases & User Stories

### 6.1 Graph-only (Phase 1)

1. **Where-used for methods**  
   *As a senior dev, I want to see all methods that call a given method, so I can assess the impact of changing it.*

2. **Field read/write analysis**  
   *As a dev, I want to see all methods that read or write a given table field, so I can understand business logic and side effects.*

3. **Class inheritance navigation**  
   *As a dev, I want to see the inheritance chain for a class and which methods are overridden, so I can reason about behavior.*

4. **Hotspot identification (graph queries)**  
   *As an architect, I want to query the graph to find highly connected nodes (e.g., methods called by many others) to identify risky areas.*

### 6.2 AI‑assisted (Phase 2)

5. **Explain this class/method**  
   *As a dev, I want an AI explanation of what this class or method does, referencing related nodes and code, so I can learn it faster.*

6. **Suggest implementation pattern**  
   *As a dev, I want the AI to show me existing examples of similar patterns (e.g., validation, posting, data updates) so I can follow established practices.*

7. **AI-guided impact analysis**  
   *As a dev, I want to ask the AI: “What is the impact of changing `CustTable.CreditMax` logic?” and get a structured list of affected methods, forms, and processes.*

8. **Onboarding assistant**  
   *As a new hire, I want to ask high-level questions (”How is customer invoicing implemented?”) and get a guided tour of the relevant AOT graph.*

---

## 7. Scope & Phasing

### 7.1 Phase 1 – AOT Graph Foundation (MVP)

**Deliverables**

1. **AOT XML Parser & IR**
   - Input: AOT exports (XML) from Dynamics F&O.
   - Output: Intermediate structures, e.g.:
     - `ClassIR { name, path, model, layer, methods[] }`
     - `MethodIR { name, modifiers, bodyText, aotPath }`
     - `TableIR { name, fields[] }`
     - `FieldIR { name, type, extendedDataType }`

2. **Graph Model (Neo4j)**
   - Node labels:
     - `:Class`, `:Method`, `:Table`, `:Field`, `:Model`, `:Package`.
   - Relationships:
     - `(:Class)-[:EXTENDS]->(:Class)`
     - `(:Class)-[:DECLARES_METHOD]->(:Method)`
     - `(:Table)-[:HAS_FIELD]->(:Field)`
     - `(:Method)-[:CALLS]->(:Method)` (basic call extraction)
     - `(:Method)-[:READS_FIELD]->(:Field)`
     - `(:Method)-[:WRITES_FIELD]->(:Field)`

3. **Ingestion Pipeline**
   - CLI or service that:
     - Accepts one or more AOT XML files.
     - Parses them into IR.
     - Upserts nodes and relationships into the graph.
   - Idempotent & repeatable (safe to re-run on updated exports).

4. **Core Queries & Dev UX**
   - Cypher query library and/or REST/GraphQL API to support:
     - `whereUsedMethod(methodName)`
     - `whoWritesField(tableName, fieldName)`
     - `whoReadsField(tableName, fieldName)`
     - `getClassHierarchy(className)`
   - Minimal UI (web or CLI) to:
     - Search for a class/method/table.
     - Visualize local neighborhood of a node.

### 7.2 Phase 2 – AI Layer & Assistant

**Deliverables**

1. **Text & Embeddings Layer**
   - Generate text descriptions for nodes:
     - Signature
     - Short summary (heuristic: comments + first lines)
     - Snippets of method bodies
   - Index in a vector store (e.g., Qdrant/PGVector) for semantic search.

2. **AI Tools / Functions**
   - `search_nodes(query)` – semantic search over nodes.
   - `get_neighbors(nodeId, depth)` – fetch graph neighborhood.
   - `get_method_source(nodeId)` – original x++ snippet.

3. **Assistant Behaviors**
   - Explain node (class/method/table/field).
   - Guided impact analysis for a change.
   - Suggest example implementations based on similar nodes.

4. **Client Integration**
   - Web chat UI (Codex UI) with:
     - Code-aware rendering (monospace snippets, syntax highlighting).
     - Links back into the graph explorer.
   - Optional: VS Code / Visual Studio integration (future sub-phase).

---

## 8. Data Model (Initial)

### 8.1 Node Types

- `:Class`
  - `name`
  - `aotPath`
  - `model`
  - `package`
  - `layer`

- `:Method`
  - `name`
  - `isStatic`
  - `access` (public/protected/private)
  - `aotPath`
  - `lineCount`
  - `cyclomaticComplexity` (optional later)

- `:Table`
  - `name`
  - `aotPath`
  - `model`

- `:Field`
  - `name`
  - `extendedDataType`
  - `type`

- `:Model` / `:Package`
  - `name`

### 8.2 Relationship Types

- `(:Class)-[:EXTENDS]->(:Class)`
- `(:Class)-[:DECLARES_METHOD]->(:Method)`
- `(:Table)-[:HAS_FIELD]->(:Field)`
- `(:Method)-[:CALLS]->(:Method)`
- `(:Method)-[:READS_FIELD]->(:Field)`
- `(:Method)-[:WRITES_FIELD]->(:Field)`
- `(:Class)-[:BELONGS_TO_MODEL]->(:Model)`
- `(:Table)-[:BELONGS_TO_MODEL]->(:Model)`

### 8.3 Identification Strategy

- Use stable AOT paths and names to derive unique keys.
- Example synthetic IDs:
  - `class:ModelName/ClassName`
  - `method:ModelName/ClassName/methodName`
  - `table:ModelName/TableName`
  - `field:ModelName/TableName/FieldName`

---

## 9. System Architecture (High-Level)

### 9.1 Components

1. **AOT Importer (CLI/Service)**
   - Handles reading AOT XML.
   - Produces IR objects.

2. **Graph Loader**
   - Converts IR to Neo4j operations.
   - Upserts nodes and relationships.

3. **Graph API**
   - REST/GraphQL endpoints in front of Neo4j.
   - Provides typed queries for front-end and assistant.

4. **Vector Search Service** (Phase 2)
   - Uses embeddings to index node text.
   - Provides semantic search API.

5. **Assistant Service** (Phase 2)
   - LLM + tools:
     - Graph queries
     - Vector search
     - Code retrieval

6. **Client(s)**
   - Web UI for graph exploration.
   - Chat UI for Codex assistant.

### 9.2 Tech Assumptions

- Graph DB: Neo4j (Aura or self-hosted).
- Backend: .NET / Node.js / Python (TBD; align with team skills).
- LLM: OpenAI / Anthropic model, abstracted behind an internal client.

---

## 10. UX Overview

### 10.1 Graph Explorer (MVP UI)

Key screens:
- **Search** box: search for class/method/table by name.
- **Node detail pane**:
  - Basic metadata
  - Inbound/outbound relationships
  - For methods: list of calls & callers, fields read/written.
- **Mini-graph visualization**: local neighborhood (1–2 hops).


### 10.2 Codex Assistant (Phase 2)

Key flows:

1. **Ask about a node**
   - User selects a method in the UI and clicks “Ask Codex”.
   - Context: node details + neighborhood + code snippet.
   - User asks: “Explain what this method does and where it’s used.”

2. **Free-form question**
   - User types: “Where is customer credit limit enforced?”
   - Assistant:
     - Uses semantic search to find relevant nodes.
     - Traverses graph around them.
     - Returns explanation + list of key methods/tables/forms.

3. **Impact analysis**
   - User types: “What is the impact of changing CustTable.CreditMax?”
   - Assistant:
     - Resolves `CustTable.CreditMax` node.
     - Traverses `READS_FIELD`/`WRITES_FIELD` edges.
     - Ranks affected methods/forms.
     - Presents a structured answer.

---

## 11. Success Metrics

### 11.1 Phase 1

- Time to answer “where is this method used?” reduced by X% (self-reported).
- At least N weekly active devs using the graph explorer.
- Positive qualitative feedback from Rod’s team:
  - “I trust the where-used results.”
  - “I can see relationships that were opaque before.”

### 11.2 Phase 2

- Percentage of dev questions answered satisfactorily by Codex (thumbs up / down in UI).
- Reduction in onboarding time for a new dev to deliver first feature.
- Number of sessions where Codex is used in a dev workflow.

---

## 12. Constraints & Risks

- **AOT Export Availability**: Need reliable access to AOT XML exports from customer environments.
- **x++ Parsing Complexity**: Method bodies may be non-trivial to analyze; MVP will rely on heuristics/regex-based extraction for calls and field accesses.
- **Data Volume & Performance**: Large Dynamics projects → large graphs; must benchmark Neo4j performance.
- **Security & IP**: Customer codebases are proprietary; deployment likely needs to be:
  - On-prem or within customer’s cloud subscription.
  - AI calls scoped and compliant with data policies.

---

## 13. Rollout Plan

1. **Internal MVP (Rod’s Team)**
   - Ingest a real AOT export.
   - Validate schema and queries.
   - Iterate quickly based on feedback.

2. **Private Alpha with 1–2 More Partners**
   - Validate on different codebases.
   - Capture varying patterns and sizes.

3. **Codex Assistant Beta**
   - Turn on AI layer for select teams.
   - Gather usage analytics and refine prompts/tools.

4. **Public Launch (Later)**
   - Packaging + deployment models (SaaS vs. self-hosted).
   - Pricing for Dynamics partners.

---

## 14. Open Questions

1. Which subset of AOT node types should be in v1 beyond Classes/Tables/Fields/Methods? Forms? Menu items? Queries?
2. How deep should we go in parsing method bodies in v1 (simple regex vs. proper x++ parser)?
3. Hosting model for first customers (Rod’s team likely fine with a simple VM + Neo4j + service).
4. Minimum UI stack for MVP (simple React app vs. CLI + Neo4j Bloom).
5. How much of this should be branded as standalone “Codex AOTGraph” vs. potentially integrated as a mesh inside ScientiaMesh later?

