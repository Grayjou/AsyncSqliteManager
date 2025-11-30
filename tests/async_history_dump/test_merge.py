# tests/test_merge.py
import pytest
from ...async_history_dump.merge import (
    force_list,
    merge_flat,
    resolve_nested,
    apply_mode_json,
    apply_nested_json,
)


def test_force_list_basic():
    assert force_list("a") == ["a"]
    assert force_list(1) == [1]
    assert force_list(["x"]) == ["x"]
    assert force_list(None) == []
    assert force_list(("a", "b")) == ["a", "b"]


def test_merge_flat_modes():
    assert merge_flat([], ["a"], "overwrite") == ["a"]
    assert merge_flat(["x"], ["a"], "append") == ["x", "a"]
    assert merge_flat(["x"], ["a"], "extend") == ["x", "a"]

    with pytest.raises(ValueError):
        merge_flat([], [], "invalid")


def test_resolve_nested_create():
    obj = {}
    c, last = resolve_nested(obj, ("a", "b"), create=True)
    assert last == "b"
    assert "a" in obj and isinstance(obj["a"], dict)


def test_resolve_nested_strict_error():
    obj = {}
    with pytest.raises(KeyError):
        resolve_nested(obj, ("x", "y"), create=False)


def test_apply_mode_json_list_append():
    out = apply_mode_json([], "x", "append")
    assert out == ["x"]


def test_apply_nested_json_list_extend():
    obj = {"a": {"b": [1]}}
    apply_nested_json(obj["a"], "b", [2, 3], "extend")
    assert obj["a"]["b"] == [1, 2, 3]
