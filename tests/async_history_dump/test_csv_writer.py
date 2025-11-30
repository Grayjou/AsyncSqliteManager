# tests/test_csv_writer.py
import pytest
import csv
from ...async_history_dump.writers import CSVWriter


@pytest.mark.asyncio
async def test_csv_overwrite(tmp_path):
    writer = CSVWriter()
    path = tmp_path / "file.csv"

    await writer.write_single(str(path), [{"a": 1, "b": 2}], "overwrite", key=None)
    rows = list(csv.reader(path.read_text().splitlines()))

    assert rows[0] == ["a", "b"]
    assert rows[1] == ["1", "2"]


@pytest.mark.asyncio
async def test_csv_append(tmp_path):
    writer = CSVWriter()
    path = tmp_path / "data.csv"

    await writer.write_single(str(path), [{"x": 1}], "overwrite", None)
    await writer.write_single(str(path), [{"x": 2}], "append", None)

    rows = list(csv.reader(path.read_text().splitlines()))
    assert rows == [["x"], ["1"], ["2"]]
