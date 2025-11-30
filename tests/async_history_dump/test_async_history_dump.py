# tests/test_async_history_dump.py
import pytest
import json
from ...async_history_dump import AsyncHistoryDump


@pytest.mark.asyncio
async def test_single_write_json(tmp_path):
    path = tmp_path / "test.json"

    d = AsyncHistoryDump(
        path=str(path),
        filetype="json",
        mode="overwrite",
        data={"a": 1},
    )

    await d.write()

    assert json.loads(path.read_text()) == {"a": 1}


@pytest.mark.asyncio
async def test_write_many_grouping(tmp_path):
    p = tmp_path / "g.json"

    d1 = AsyncHistoryDump(str(p), filetype="json", mode="append", data={"x": 1})
    d2 = AsyncHistoryDump(str(p), filetype="json", mode="append", data={"y": 2})

    await AsyncHistoryDump.write_many([d1, d2])

    out = json.loads(p.read_text())
    assert isinstance(out, list)
    assert out == [{"x": 1}, {"y": 2}]
