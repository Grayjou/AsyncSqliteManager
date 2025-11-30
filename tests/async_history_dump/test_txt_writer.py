# tests/test_txt_writer.py
import pytest
from ...async_history_dump.writers import TXTWriter


@pytest.mark.asyncio
async def test_txt_overwrite(tmp_path):
    writer = TXTWriter()
    path = tmp_path / "file.txt"

    await writer.write_single(str(path), "hello", "overwrite", key=None)
    assert path.read_text().strip() == "hello"


@pytest.mark.asyncio
async def test_txt_append(tmp_path):
    writer = TXTWriter()
    path = tmp_path / "file.txt"

    await writer.write_single(str(path), "a", "overwrite", key=None)
    await writer.write_single(str(path), "b", "append", key=None)

    assert path.read_text().splitlines() == ["a", "b"]
