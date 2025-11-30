# tests/manager/test_types.py
import pytest
from ...manager.types import QueryParams, QueryResult, HistoryItem


def test_query_params_accepts_none():
    """Test that QueryParams type alias accepts None."""
    params: QueryParams = None
    assert params is None


def test_query_params_accepts_tuple():
    """Test that QueryParams type alias accepts tuple."""
    params: QueryParams = (1, 2, 3)
    assert params == (1, 2, 3)


def test_query_params_accepts_list_of_tuples():
    """Test that QueryParams type alias accepts list of tuples."""
    params: QueryParams = [(1,), (2,), (3,)]
    assert params == [(1,), (2,), (3,)]


def test_query_result_accepts_none():
    """Test that QueryResult type alias accepts None."""
    result: QueryResult = None
    assert result is None


def test_query_result_accepts_list():
    """Test that QueryResult type alias accepts list."""
    result: QueryResult = [1, 2, 3]
    assert result == [1, 2, 3]


def test_history_item_is_dict():
    """Test that HistoryItem is a dict type alias."""
    item: HistoryItem = {"query": "SELECT *", "path": "test.db"}
    assert isinstance(item, dict)
    assert item["query"] == "SELECT *"
    assert item["path"] == "test.db"
