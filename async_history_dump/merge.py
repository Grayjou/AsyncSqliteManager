# async_history_dump/merge.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple


# =============================================================================
# FLAT MERGE (TXT / CSV)
# =============================================================================

def force_list(obj: Any) -> List[Any]:
    """Normalize any value into a list suitable for flat outputs (txt/csv)."""
    if obj is None:
        return []
    if isinstance(obj, list):
        return obj
    if isinstance(obj, (tuple, set)):
        return list(obj)
    if isinstance(obj, str):
        return [obj]
    return [obj]


def merge_flat(existing, new, mode: str):
    """Flat merge for TXT/CSV; dict rows are allowed."""
    existing_list = force_list(existing)
    new_list = force_list(new)

    if mode == "overwrite":
        return new_list

    if mode in {"append", "extend", "update"}:
        return existing_list + new_list

    raise ValueError(f"Unsupported mode '{mode}' for flat output.")


# =============================================================================
# JSON MERGE
# =============================================================================

def resolve_nested(obj: Dict, key: Tuple[str, ...], create: bool) -> Tuple[Dict, str]:
    """Return (container, last_key). Creates intermediate dicts if needed."""
    current = obj
    for k in key[:-1]:
        if k not in current or not isinstance(current[k], dict):
            if not create:
                raise KeyError(f"Key path {key} does not exist in JSON.")
            current[k] = {}
        current = current[k]
    return current, key[-1]


def apply_mode_json(existing: Any, data: Any, mode: str) -> Any:
    """Merge logic for root-level JSON writes."""
    if mode == "overwrite":
        return data

    if mode == "append":
        if isinstance(existing, list):
            existing.append(data)
        elif isinstance(existing, dict) and isinstance(data, dict):
            existing.update(data)  # restore expected behavior
        elif isinstance(existing, set) and isinstance(data, set):
            existing.update(data)
        else:
            # fallback: wrap into list
            return [existing, data]
        return existing

    if mode in {"extend", "update"}:
        if isinstance(existing, list):
            if not isinstance(data, list):
                raise ValueError("Cannot extend list with non-list.")
            existing.extend(data)
        elif isinstance(existing, dict) and isinstance(data, dict):
            existing.update(data)
        elif isinstance(existing, set) and isinstance(data, set):
            existing.update(data)
        else:
            raise ValueError("Update/extend not supported for type.")
        return existing

    raise ValueError(f"Unsupported JSON mode {mode}")


def apply_nested_json(container: Dict, last_key: str, data: Any, mode: str):
    """Merge logic for nested JSON keys."""
    target = container.get(last_key)

    if mode == "overwrite":
        container[last_key] = data
        return

    if mode == "append":
        if target is None:
            container[last_key] = [data]
        elif isinstance(target, list):
            target.append(data)
        elif isinstance(target, dict) and isinstance(data, dict):
            target.update(data)
        else:
            container[last_key] = [target, data]
        return

    if mode in {"extend", "update"}:
        if target is None:
            container[last_key] = data
        elif isinstance(target, list) and isinstance(data, list):
            target.extend(data)
        elif isinstance(target, dict) and isinstance(data, dict):
            target.update(data)
        elif isinstance(target, set) and isinstance(data, set):
            target.update(data)
        else:
            raise ValueError(f"Update/extend not supported for nested type at {last_key}")
        return

    raise ValueError(f"Unsupported nested mode {mode}")
