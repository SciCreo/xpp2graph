# Assistant Tooling

`src/assistant/toolkit.py` wires the graph queries and embeddings layer into a
single toolkit that future LLM agents can call.

Provided capabilities:

- `search_nodes` – semantic lookup using the vector store.
- `get_neighbors` – fetch neighboring nodes and relationship hop counts.
- `get_method_source` – return the stored method body for code-aware prompts.
- `explain_node` – combine node properties, semantic summary, and local graph
  context in a single payload.

Instantiate the toolkit with:

```python
from pathlib import Path
from src.assistant import AssistantToolkit
from src.embeddings.store import LocalVectorStore
from src.embeddings.client import HashEmbeddingClient
from src.config import load_settings

settings = load_settings()
store = LocalVectorStore(Path("data/embeddings.db"), dimension=384)
assistant = AssistantToolkit.from_defaults(
    store=store,
    embedding_client=HashEmbeddingClient(),
    settings=settings,
)
```

Remember to call `assistant.close()` when done to release the Neo4j driver and
vector store connections.


