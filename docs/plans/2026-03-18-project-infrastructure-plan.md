# Project Infrastructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Dependabot, CI workflow (lint + integration tests), and testcontainers-based test infrastructure.

**Architecture:** Dependabot watches pip and GitHub Actions dependencies. CI runs two parallel jobs: fast Ruff lint and integration tests using testcontainers to spin up ArcadeDB 26.3.1. Tests are refactored from requiring a pre-running instance to self-contained container lifecycle.

**Tech Stack:** GitHub Actions, Dependabot, testcontainers-python, Ruff, pytest, Docker

---

### Task 1: Add dev dependencies to pyproject.toml

**Files:**
- Modify: `pyproject.toml:39-43`

**Step 1: Update dev dependencies**

Replace the existing `[tool.hatch.envs.default] dependencies` block with:

```toml
[tool.hatch.envs.default]
dependencies = [
    "pytest",
    "pytest-cov",
    "testcontainers>=4.9.1",
    "docker>=7.1.0",
    "ruff",
]
```

Also add an `[project.optional-dependencies]` section after `[project.urls]` for pip-based installs (used by CI):

```toml
[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    "testcontainers>=4.9.1",
    "docker>=7.1.0",
    "ruff",
]
```

**Step 2: Verify pyproject.toml is valid**

Run: `python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))"`
Expected: No output (success)

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build: add testcontainers, docker, and ruff to dev dependencies"
```

---

### Task 2: Create Dependabot configuration

**Files:**
- Create: `.github/dependabot.yml`

**Step 1: Create the file**

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

**Step 2: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))" 2>/dev/null || python -c "print('yaml module not available, skipping validation')"`

**Step 3: Commit**

```bash
git add .github/dependabot.yml
git commit -m "ci: add Dependabot configuration for pip and GitHub Actions"
```

---

### Task 3: Create CI workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Step 1: Create the workflow file**

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install ruff
      - run: ruff check .
      - run: ruff format --check .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -e ".[dev]"
      - run: pytest tests/ --cov=haystack_integrations --cov-report=term-missing -v
```

**Step 2: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" 2>/dev/null || python -c "print('yaml module not available, skipping validation')"`

**Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add CI workflow with lint and test jobs"
```

---

### Task 4: Add testcontainers fixture to conftest.py

**Files:**
- Create: `tests/conftest.py`

**Step 1: Create the shared fixture**

This fixture starts ArcadeDB once per test session, waits for readiness, and provides the base URL to all tests.

```python
# SPDX-FileCopyrightText: 2026-present ArcadeData Ltd <info@arcadedb.com>
# SPDX-License-Identifier: Apache-2.0

import time

import pytest
import requests
from testcontainers.core.container import DockerContainer

ARCADEDB_IMAGE = "arcadedata/arcadedb:26.3.1"


def _wait_for_ready(container, timeout=60):
    """Wait for ArcadeDB HTTP API to become ready."""
    host = container.get_container_host_ip()
    port = container.get_exposed_port(2480)
    url = f"http://{host}:{port}/api/v1/ready"

    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=2)
            if resp.status_code == 204:
                return
        except (requests.ConnectionError, requests.Timeout):
            pass
        time.sleep(1)
    raise TimeoutError(f"ArcadeDB not ready at {url} after {timeout}s")


@pytest.fixture(scope="session")
def arcadedb_url():
    """Start an ArcadeDB container and yield its HTTP base URL."""
    container = (
        DockerContainer(ARCADEDB_IMAGE)
        .with_exposed_ports(2480)
        .with_env(
            "JAVA_OPTS",
            "-Darcadedb.server.rootPassword=arcadedb",
        )
    )
    container.start()
    _wait_for_ready(container)

    host = container.get_container_host_ip()
    port = container.get_exposed_port(2480)
    yield f"http://{host}:{port}"

    container.stop()
```

**Step 2: Verify the file is syntactically valid**

Run: `python -c "import ast; ast.parse(open('tests/conftest.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add testcontainers fixture for ArcadeDB"
```

---

### Task 5: Refactor test_document_store.py to use testcontainers

**Files:**
- Modify: `tests/test_document_store.py`

**Step 1: Rewrite the test file**

Key changes:
- Remove `import os` and `import unittest`
- Add `import pytest`
- Replace `_store()` helper to accept `arcadedb_url` fixture instead of env var
- Convert from `unittest.TestCase` class to plain pytest functions
- Each test receives `arcadedb_url` fixture and creates a fresh store with `recreate_type=True`

Replace the entire file with:

```python
# SPDX-FileCopyrightText: 2026-present ArcadeData Ltd <info@arcadedb.com>
# SPDX-License-Identifier: Apache-2.0

"""Integration tests for ArcadeDBDocumentStore (using testcontainers)."""

import pytest
from haystack import Document
from haystack.document_stores.errors import DuplicateDocumentError
from haystack.document_stores.types import DuplicatePolicy

from haystack_integrations.document_stores.arcadedb import ArcadeDBDocumentStore


def _store(arcadedb_url, **kwargs):
    return ArcadeDBDocumentStore(
        url=arcadedb_url,
        database="haystack_test",
        username=kwargs.pop("username", None)
        or ArcadeDBDocumentStore.__init__.__kwdefaults__["username"],
        password=kwargs.pop("password", None)
        or ArcadeDBDocumentStore.__init__.__kwdefaults__["password"],
        recreate_type=True,
        **kwargs,
    )


def _sample_docs(n=3, dim=4):
    return [
        Document(
            content=f"Document number {i}",
            embedding=[float(i)] * dim,
            meta={"category": "test", "priority": i},
        )
        for i in range(n)
    ]


# ---- count ----


def test_count_empty(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    assert store.count_documents() == 0


def test_count_after_write(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(5)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)
    assert store.count_documents() == 5


# ---- write ----


def test_write_and_read(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(2)
    written = store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)
    assert written == 2

    all_docs = store.filter_documents()
    assert len(all_docs) == 2


def test_write_overwrite(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(1)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    docs[0].content = "Updated content"
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    all_docs = store.filter_documents()
    assert len(all_docs) == 1
    assert all_docs[0].content == "Updated content"


def test_write_skip(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(1)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    written = store.write_documents(docs, policy=DuplicatePolicy.SKIP)
    assert written == 0
    assert store.count_documents() == 1


def test_write_duplicate_raises(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(1)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    with pytest.raises(DuplicateDocumentError):
        store.write_documents(docs, policy=DuplicatePolicy.NONE)


# ---- delete ----


def test_delete(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(3)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    store.delete_documents([docs[0].id, docs[1].id])
    assert store.count_documents() == 1


# ---- filter ----


def test_filter_equality(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(3)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    result = store.filter_documents(
        filters={"field": "meta.category", "operator": "==", "value": "test"}
    )
    assert len(result) == 3


def test_filter_comparison(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(5)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    result = store.filter_documents(
        filters={"field": "meta.priority", "operator": ">", "value": 2}
    )
    assert len(result) == 2


def test_filter_and(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(5)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    result = store.filter_documents(
        filters={
            "operator": "AND",
            "conditions": [
                {"field": "meta.category", "operator": "==", "value": "test"},
                {"field": "meta.priority", "operator": ">=", "value": 3},
            ],
        }
    )
    assert len(result) == 2


# ---- embedding retrieval ----


def test_embedding_retrieval(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    docs = _sample_docs(5, dim=4)
    store.write_documents(docs, policy=DuplicatePolicy.OVERWRITE)

    results = store._embedding_retrieval(
        query_embedding=[4.0, 4.0, 4.0, 4.0], top_k=3
    )
    assert len(results) <= 3
    assert results[0].score is not None


# ---- serialization ----


def test_to_dict_from_dict(arcadedb_url):
    store = _store(arcadedb_url, embedding_dimension=4)
    data = store.to_dict()
    restored = ArcadeDBDocumentStore.from_dict(data)
    assert restored._database == store._database
    assert restored._embedding_dimension == store._embedding_dimension
```

**Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('tests/test_document_store.py').read()); print('OK')"`
Expected: `OK`

**Step 3: Run the unit tests (filters) to confirm no breakage**

Run: `pytest tests/test_filters.py -v`
Expected: All tests pass

**Step 4: Commit**

```bash
git add tests/test_document_store.py
git commit -m "test: refactor integration tests to use testcontainers fixture"
```

---

### Task 6: Run full test suite locally (if Docker available)

**Step 1: Run all tests**

Run: `pytest tests/ -v --tb=short`
Expected: All tests pass (filter unit tests + document store integration tests)

**Step 2: Run linting**

Run: `ruff check . && ruff format --check .`
Expected: No errors

**Step 3: Fix any lint issues if found**

Run: `ruff format .` (if formatting issues) then re-run checks.

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "style: fix lint issues"
```
