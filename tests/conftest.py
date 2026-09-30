"""测试共享 Fixtures。"""

import os
import pytest
from fastapi.testclient import TestClient

from server.core.config import app_config
from server.db.session import init_db
from server.main import app

app_config.api_key = "onetts-test-key"


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _setup_test_env():
    import asyncio
    asyncio.run(init_db())
    yield
