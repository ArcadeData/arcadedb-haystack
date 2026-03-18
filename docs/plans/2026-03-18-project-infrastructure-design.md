# Project Infrastructure Design

## Overview

Set up CI, Dependabot, and foundational project infrastructure for the `arcadedb-haystack` project hosted on GitHub under the `ArcadeData` org.

## Dependabot

**File:** `.github/dependabot.yml`

Two ecosystems, both on a weekly schedule targeting `main`:

- **pip** — monitors `pyproject.toml` for dependency updates
- **github-actions** — monitors workflow action versions (e.g., `actions/checkout`, `actions/setup-python`)

No auto-merge, no grouping, no reviewers. The ArcadeDB Docker image version is updated manually (not tracked by Dependabot).

## CI Workflow

**File:** `.github/workflows/ci.yml`

**Triggers:** pull request to main, push to main, `workflow_dispatch`

### Job 1: `lint`

- Runs on `ubuntu-latest`, Python 3.13
- Installs Ruff
- Runs `ruff check .` and `ruff format --check .`

### Job 2: `test`

- Runs on `ubuntu-latest`, Python 3.13
- Installs project with dev dependencies (`pip install -e .` + dev deps)
- Tests use `testcontainers` to spin up `arcadedata/arcadedb:26.3.1` with a readiness check on the HTTP API (`/api/v1/ready` on port 2480)
- Runs `pytest tests/` with coverage
- Docker is pre-installed on GitHub Actions runners

## File Changes

### New files

| File | Purpose |
|------|---------|
| `.github/dependabot.yml` | Dependabot configuration |
| `.github/workflows/ci.yml` | CI workflow with lint + test jobs |

### Modified files

| File | Change |
|------|--------|
| `pyproject.toml` | Add `testcontainers`, `docker`, and `ruff` to dev dependencies |
| `tests/test_document_store.py` | Refactor to use a `testcontainers` fixture (module-scoped) instead of requiring a pre-running ArcadeDB instance |

### Unchanged files

| File | Reason |
|------|--------|
| `tests/test_filters.py` | Pure unit tests, no ArcadeDB dependency |

## Testcontainers Fixture Pattern

Following the pattern from `e2e-python/tests/test_arcadedb.py`:

```python
from testcontainers.core.container import DockerContainer

ARCADEDB_IMAGE = "arcadedata/arcadedb:26.3.1"

arcadedb = (
    DockerContainer(ARCADEDB_IMAGE)
    .with_exposed_ports(2480)
    .with_env("JAVA_OPTS", "-Darcadedb.server.rootPassword=arcadedb")
)

@pytest.fixture(scope="module", autouse=True)
def arcadedb_container():
    arcadedb.start()
    wait_for_http_endpoint(arcadedb, "/api/v1/ready", 2480, 204, timeout=30)
    yield arcadedb
    arcadedb.stop()
```

The `_store()` helper will resolve the URL from the container's mapped host/port.

## Out of Scope

- Release/publish workflow to PyPI (manual for now)
- Python version matrix (3.13 only)
- Docker image version tracking via Dependabot (manual updates)
