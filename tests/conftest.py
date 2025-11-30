# tests/conftest.py
import pytest
import asyncio
pytest_plugins = ("pytest_asyncio",)

@pytest.fixture
def event_loop():
    """Create an isolated event loop for asyncio tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()