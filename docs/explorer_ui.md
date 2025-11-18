# Explorer UI

The minimal explorer UI is served from the API at `/explorer`. It provides three
graph queries in a single page:

- Method where-used lookup
- Field read/write analysis
- Class hierarchy traversal

Each form issues a `fetch` call against the REST endpoints implemented in
`src/api/server.py`. Results are rendered as formatted JSON for quick inspection.

Launch the API via:

```bash
uvicorn src.api.server:create_app --factory --reload
```

Then visit [http://localhost:8000/explorer](http://localhost:8000/explorer).


