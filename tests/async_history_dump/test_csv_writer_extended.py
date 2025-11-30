import pytest
import csv
from ...async_history_dump.writers import CSVWriter


@pytest.mark.asyncio
async def test_csv_overwrite_multi_column_order(tmp_path):
    writer = CSVWriter()
    path = tmp_path / "multi.csv"

    await writer.write_single(str(path), [{"a": 1, "b": 2, "c": 3}], "overwrite", None)
    rows = list(csv.reader(path.read_text().splitlines()))

    assert rows[0] == ["a", "b", "c"]
    assert rows[1] == ["1", "2", "3"]


@pytest.mark.asyncio
async def test_csv_append_preserves_header_and_data(tmp_path):
    writer = CSVWriter()
    path = tmp_path / "append.csv"

    await writer.write_single(str(path), [{"x": 1}], "overwrite", None)
    await writer.write_single(str(path), [{"x": 2}], "append", None)

    rows = list(csv.reader(path.read_text().splitlines()))
    assert rows == [["x"], ["1"], ["2"]]


@pytest.mark.asyncio
async def test_csv_append_mixed_list_to_dict(tmp_path):
    writer = CSVWriter()
    path = tmp_path / "mixed1.csv"

    # Start with dict (header 'x') then append list row ['3']
    await writer.write_single(str(path), [{"x": 1}, {"x": 2}], "overwrite", None)
    await writer.write_single(str(path), [["3"]], "append", None)

    rows = list(csv.reader(path.read_text().splitlines()))
    assert rows == [["x"], ["1"], ["2"], ["3"]]


@pytest.mark.asyncio
async def test_csv_append_mixed_dict_to_list(tmp_path):
    writer = CSVWriter()
    path = tmp_path / "mixed2.csv"

    # Start with list-only single column then append dict with same logical header
    await writer.write_single(str(path), [["1"], ["2"]], "overwrite", None)
    await writer.write_single(str(path), [{"col": "3"}], "append", None)

    # Expect header reconstructed as 'col' with existing values under it
    rows = list(csv.reader(path.read_text().splitlines()))
    assert rows[0] == ["col"]
    assert rows[1:] == [["1"], ["2"], ["3"]]


@pytest.mark.asyncio
async def test_csv_overwrite_then_append_new_header_keys_order(tmp_path):
    writer = CSVWriter()
    path = tmp_path / "newkeys.csv"

    await writer.write_single(str(path), [{"a": 1, "b": 2}], "overwrite", None)
    await writer.write_single(str(path), [{"b": 3, "c": 4}], "append", None)

    rows = list(csv.reader(path.read_text().splitlines()))
    # Header order should follow first appearance across rows: a, b, c
    assert rows[0] == ["a", "b", "c"]
    assert rows[1] == ["1", "2", ""]
    assert rows[2] == ["", "3", "4"]


@pytest.mark.asyncio
async def test_csv_pure_list_rows_no_header(tmp_path):
    writer = CSVWriter()
    path = tmp_path / "purelist.csv"

    await writer.write_single(str(path), [["a", "b"], ["1", "2"]], "overwrite", None)
    rows = list(csv.reader(path.read_text().splitlines()))

    # No header detection because we didn't create alphabetic-only header via dict writer
    assert rows == [["a", "b"], ["1", "2"]]
