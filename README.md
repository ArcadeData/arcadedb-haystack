# arcadedb-haystack

[![PyPI](https://img.shields.io/pypi/v/arcadedb-haystack)](https://pypi.org/project/arcadedb-haystack/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

**ArcadeDB integration for [Haystack](https://haystack.deepset.ai/) 2.x** — one database for document storage, HNSW vector search, and SQL metadata filtering.

## Why ArcadeDB?

Most RAG setups need separate backends for documents, vectors, and full-text search. ArcadeDB replaces all three:

- **Document storage** — vertex-based records with flexible MAP metadata
- **HNSW vector search** — native approximate nearest neighbor index (cosine, euclidean, dot product)
- **SQL filtering** — full SQL WHERE clauses on metadata fields
- **No special drivers** — pure HTTP/JSON API via `requests`

## Installation

```bash
pip install arcadedb-haystack
```

## Quick Start

```bash
# Start ArcadeDB
docker run -d -p 2480:2480 \
    -e JAVA_OPTS="-Darcadedb.server.rootPassword=arcadedb" \
    arcadedata/arcadedb:latest

export ARCADEDB_USERNAME=root
export ARCADEDB_PASSWORD=arcadedb
```

```python
from haystack import Document
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.document_stores.arcadedb import ArcadeDBDocumentStore

store = ArcadeDBDocumentStore(
    database="myproject",
    embedding_dimension=768,
)

# Write documents
docs = [
    Document(
        content="ArcadeDB supports graphs, documents, and vectors.",
        embedding=[0.1] * 768,
        meta={"source": "docs", "category": "database"},
    )
]
store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

# Filter by metadata
results = store.filter_documents(
    filters={"field": "meta.category", "operator": "==", "value": "database"}
)

# Vector similarity search
similar = store._embedding_retrieval(
    query_embedding=[0.1] * 768,
    top_k=5,
)
```

## Using in a Pipeline

```python
from haystack import Pipeline
from haystack_integrations.components.retrievers.arcadedb import ArcadeDBEmbeddingRetriever
from haystack_integrations.document_stores.arcadedb import ArcadeDBDocumentStore

store = ArcadeDBDocumentStore(database="myproject", embedding_dimension=768)

pipeline = Pipeline()
pipeline.add_component("retriever", ArcadeDBEmbeddingRetriever(document_store=store, top_k=10))

result = pipeline.run({"retriever": {"query_embedding": [0.1] * 768}})
documents = result["retriever"]["documents"]
```

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `url` | `http://localhost:2480` | ArcadeDB HTTP endpoint |
| `database` | `haystack` | Database name |
| `username` | env `ARCADEDB_USERNAME` | HTTP Basic Auth username |
| `password` | env `ARCADEDB_PASSWORD` | HTTP Basic Auth password |
| `type_name` | `Document` | Vertex type name |
| `embedding_dimension` | `768` | Vector dimension for HNSW index |
| `similarity_function` | `cosine` | `cosine`, `euclidean`, or `dot` |
| `recreate_type` | `False` | Drop and recreate type on init |
| `create_database` | `True` | Create database if it doesn't exist |

## Components

### `ArcadeDBDocumentStore`

Implements the Haystack `DocumentStore` protocol:

- `count_documents()` — count stored documents
- `filter_documents(filters)` — retrieve documents matching metadata filters
- `write_documents(documents, policy)` — write/upsert/skip documents
- `delete_documents(document_ids)` — delete by ID

### `ArcadeDBEmbeddingRetriever`

Pipeline component for vector similarity retrieval:

- Uses ArcadeDB's native HNSW index via `vectorNeighbors()`
- Supports runtime filter override and merge via `FilterPolicy`
- Serializable for pipeline export/import

## Development

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run tests (requires running ArcadeDB)
pytest tests/
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
