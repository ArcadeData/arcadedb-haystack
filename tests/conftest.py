# SPDX-FileCopyrightText: 2026-present ArcadeData Ltd <info@arcadedb.com>
# SPDX-License-Identifier: Apache-2.0

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import HttpWaitStrategy

ARCADEDB_IMAGE = "arcadedata/arcadedb:26.3.1"


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
        .waiting_for(
            HttpWaitStrategy(2480, "/api/v1/ready")
            .for_status_code(204)
            .with_startup_timeout(60)
        )
    )
    container.start()

    host = container.get_container_host_ip()
    port = container.get_exposed_port(2480)
    yield f"http://{host}:{port}"

    container.stop()
