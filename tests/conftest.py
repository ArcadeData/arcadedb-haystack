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
