# async_history_dump/writers.py
from __future__ import annotations

import os
import json
import csv
import io
import aiofiles
from typing import Any, List, Tuple, Protocol, Union

from .merge import (
    merge_flat,
    resolve_nested,
    apply_mode_json,
    apply_nested_json,
)


def _is_header(row: List[str]) -> bool:
    """
    Detect if row is a CSV header.

    Rule:
    - If ANY cell contains ANY alphabetic character → treat row as header.
    - Purely numeric, empty, or symbol-only rows are NOT headers.
    """
    for cell in row:
        if any(char.isalpha() for char in cell):
            return True
    return False



# =============================================================================
# Writer Protocol (Interface)
# =============================================================================

class BaseWriter(Protocol):
    async def write_single(
        self,
        path: str,
        data: Any,
        mode: str,
        key: Tuple[str, ...] | None,
        strict_keys: bool = False,
    ) -> None:
        ...

    async def write_batch(
        self,
        path: str,
        data_list: List[Any],
        mode: str,
        key: Tuple[str, ...] | None,
        strict_keys: bool = False,
    ) -> None:
        ...


# =============================================================================
# JSON WRITER
# =============================================================================

class JSONWriter:
    """Handles JSON file reading, merging, and writing."""

    async def _read_json(self, path: str, key: Tuple[str, ...] | None):
        if not os.path.exists(path):
            return {} if key else []
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            txt = await f.read()
        if not txt.strip():
            return {} if key else []
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            return {} if key else []

    def _validate_strict_key(self, existing: Any, key: Tuple[str, ...]):
        """Ensure all segments of nested key path exist AND are dicts."""
        current = existing
        for segment in key:
            if not isinstance(current, dict):
                raise TypeError(
                    f"Strict key violation: segment '{segment}' expected dict, got {type(current).__name__}"
                )
            if segment not in current:
                raise KeyError(
                    f"Strict key violation: key path '{'.'.join(key)}' does not exist in JSON file"
                )
            current = current[segment]

    async def write_single(
        self,
        path: str,
        data: Any,
        mode: str,
        key: Tuple[str, ...] | None,
        strict_keys: bool = False,
    ) -> None:

        existing = await self._read_json(path, key)

        if strict_keys and key:
            self._validate_strict_key(existing, key)

        if key is None:
            existing = apply_mode_json(existing, data, mode)
        else:
            container, last_key = resolve_nested(
                existing, key, create=not strict_keys # type: ignore
            )
            apply_nested_json(container, last_key, data, mode)

        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(existing, indent=2))

    async def write_batch(
        self,
        path: str,
        data_list: List[Any],
        mode: str,
        key: Tuple[str, ...] | None,
        strict_keys: bool = False,
    ) -> None:

        for item in data_list:
            await self.write_single(
                path=path,
                data=item,
                mode=mode,
                key=key,
                strict_keys=strict_keys,
            )
# =============================================================================
# TXT WRITER
# =============================================================================

class TXTWriter:
    async def _read_txt(self, path: str) -> List[str]:
        if not os.path.exists(path):
            return []
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            return [line.rstrip("\n") async for line in f]

    async def write_single(
        self,
        path: str,
        data: Any,
        mode: str,
        key: Tuple[str, ...] | None = None,
        strict_keys: bool = False, #For protocol compatibility 
    ) -> None:

        existing = []
        if os.path.exists(path) and mode != "overwrite":
            existing = await self._read_txt(path)

        merged = merge_flat(existing, data, mode)

        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            for line in merged:
                await f.write(f"{line}\n")

    async def write_batch(
        self,
        path: str,
        data_list: List[Any],
        mode: str,
        key: Tuple[str, ...] | None,
        strict_keys: bool = False, #For protocol compatibility 
    ) -> None:
        existing = []
        if os.path.exists(path) and mode != "overwrite":
            existing = await self._read_txt(path)

        combined = []
        for item in data_list:
            if isinstance(item, list):
                combined.extend(item)
            else:
                combined.append(item)

        merged = merge_flat(existing, combined, mode)

        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            for line in merged:
                await f.write(f"{line}\n")


# =============================================================================
# CSV WRITER
# =============================================================================


class CSVWriter:
    async def _read_csv(self, path: str) -> Tuple[List[str] | None, List[List[str]]]:
        if not os.path.exists(path):
            return None, []

        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()

        reader = csv.reader(content.splitlines())
        rows = list(reader)

        if not rows:
            return None, []

        # Detect header
        if _is_header(rows[0]):
            return rows[0], rows[1:]

        return None, rows

    async def _write_csv(self, path: str, rows: List[Any], existing_header: List[str] | None = None) -> None:
        buffer = io.StringIO()

        if not rows:
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                return

        # Decide mode: if any dict is present, write as dict CSV with header.
        any_dict = any(isinstance(r, dict) for r in rows)

        if any_dict:
            # Collect headers by first appearance across dict rows
            # Start headers from existing header if available, then append new keys
            headers: List[str] = list(existing_header) if existing_header else []
            for r in rows:
                if isinstance(r, dict):
                    for k in r.keys():
                        if k not in headers:
                            headers.append(k)

            # Normalize rows: convert list rows to dicts using headers when possible
            norm_rows: List[dict] = []
            for r in rows:
                if isinstance(r, dict):
                    norm_rows.append(r)
                elif isinstance(r, list):
                    if len(headers) == 1:
                        # Single-column CSV: map the sole value
                        norm_rows.append({headers[0]: r[0] if r else ""})
                    else:
                        # Attempt positional mapping; pad/truncate to headers length
                        mapped = {h: (r[i] if i < len(r) else "") for i, h in enumerate(headers)}
                        norm_rows.append(mapped)
                else:
                    # Fallback: stringify as single column if one header, else put in first
                    if len(headers) == 1:
                        norm_rows.append({headers[0]: str(r)})
                    else:
                        mapped = {h: "" for h in headers}
                        mapped[headers[0]] = str(r)
                        norm_rows.append(mapped)

            writer = csv.DictWriter(buffer, fieldnames=headers)
            writer.writeheader()
            for row in norm_rows:
                writer.writerow({key: row.get(key, "") for key in headers})
        else:
            # Pure list rows: if we have an existing header, write as single/multi-column headered CSV
            if existing_header:
                headers = list(existing_header)
                writer = csv.DictWriter(buffer, fieldnames=headers)
                writer.writeheader()
                for r in rows:
                    if isinstance(r, list):
                        if len(headers) == 1:
                            writer.writerow({headers[0]: r[0] if r else ""})
                        else:
                            mapped = {h: (r[i] if i < len(r) else "") for i, h in enumerate(headers)}
                            writer.writerow(mapped)
                    else:
                        if len(headers) == 1:
                            writer.writerow({headers[0]: str(r)})
                        else:
                            mapped = {h: "" for h in headers}
                            mapped[headers[0]] = str(r)
                            writer.writerow(mapped)
            else:
                writer = csv.writer(buffer)
                writer.writerows(rows)

        async with aiofiles.open(path, "w", encoding="utf-8", newline="") as f:
            await f.write(buffer.getvalue())

    async def write_single(
        self,
        path: str,
        data: Any,
        mode: str,
        key: Tuple[str, ...] | None,
        strict_keys: bool = False,
    ) -> None:

        if not isinstance(data, list):
            data = [data]

        existing_header: List[str] | None = None
        existing: List[List[str]] = []
        if os.path.exists(path) and mode != "overwrite":
            existing_header, existing = await self._read_csv(path)

        merged = merge_flat(existing, data, mode)

        await self._write_csv(path, merged, existing_header)

    async def write_batch(
        self,
        path: str,
        data_list: List[Any],
        mode: str,
        key: Tuple[str, ...] | None,
        strict_keys: bool = False,
    ) -> None:

        existing_header: List[str] | None = None
        existing: List[List[str]] = []
        if os.path.exists(path) and mode != "overwrite":
            existing_header, existing = await self._read_csv(path)

        combined = []
        for item in data_list:
            combined.extend(item if isinstance(item, list) else [item])

        merged = merge_flat(existing, combined, mode)

        await self._write_csv(path, merged, existing_header)

WriterType = Union[JSONWriter, TXTWriter, CSVWriter]