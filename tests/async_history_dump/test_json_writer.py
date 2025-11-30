# tests/test_json_writer.py
import pytest
import json
from ...async_history_dump.writers import JSONWriter


@pytest.mark.asyncio
async def test_json_overwrite(tmp_path):
    writer = JSONWriter()
    path = tmp_path / "file.json"

    await writer.write_single(str(path), {"a": 1}, "overwrite", key=None)
    data = json.loads(path.read_text())
    assert data == {"a": 1}


@pytest.mark.asyncio
async def test_json_nested_append(tmp_path):
    writer = JSONWriter()
    path = tmp_path / "nested.json"

    await writer.write_single(str(path), {"x": 1}, "overwrite", key=("a",))
    await writer.write_single(str(path), {"y": 2}, "append", key=("a",))

    data = json.loads(path.read_text())

    # APPEND on dict should MERGE keys, not create list
    assert isinstance(data["a"], dict)
    assert data["a"] == {"x": 1, "y": 2}



@pytest.mark.asyncio
async def test_json_strict_keys(tmp_path):
    writer = JSONWriter()
    path = tmp_path / "strict.json"

    # Initialize the file
    await writer.write_single(str(path), {"b": 1}, "overwrite", key=("a",))

    # Writing strict to a missing key → KeyError
    with pytest.raises(KeyError):
        await writer.write_single(str(path), {"c": 2}, "append", key=("a", "missing"), strict_keys=True)
