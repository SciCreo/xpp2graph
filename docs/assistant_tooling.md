# Assistant Tooling

`src/assistant/toolkit.py` wires the graph queries and embeddings layer into a
single toolkit that future LLM agents can call.

Provided capabilities:

- `search_nodes` – semantic lookup via Neo4j vector + full-text indexes.
- `get_neighbors` – fetch neighboring nodes and relationship hop counts.
- `get_method_source` – return the stored method body for code-aware prompts.
- `explain_node` – combine node properties, semantic summary, and local graph
  context in a single payload.

Instantiate the toolkit with:

```python
from src.assistant import AssistantToolkit
from src.config import load_settings

settings = load_settings()
assistant = AssistantToolkit.from_defaults(
    settings=settings,
)
```

Remember to call `assistant.close()` when done to release the Neo4j driver.


