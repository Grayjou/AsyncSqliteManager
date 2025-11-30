# async_history_dump/async_history_dump.py
from __future__ import annotations

import os
import asyncio
from typing import Iterable, Optional, Tuple, Dict
from collections import defaultdict
from .writers import JSONWriter, TXTWriter, CSVWriter, WriterType
from .types import OutputData 


class AsyncHistoryDump:
    """
    Public facade for writing JSON, CSV, or TXT asynchronously.
    """

    filetypes = {"json", "csv", "txt"}
    modes = {"overwrite", "append", "update", "extend"}

    _writers: Dict[str, WriterType] = {
        "json": JSONWriter(),
        "txt": TXTWriter(),
        "csv": CSVWriter(),
    }

    def __init__(
        self,
        path: str,
        *,
        mode: str = "overwrite",
        filetype: str = "__autodetect__",
        key: Optional[Tuple[str, ...]] = None,
        data: Optional[OutputData] = None,
        strict_keys: bool = False,
    ) -> None:
        self.path = self._normalize_path(path)
        self.mode = self._validate_mode(mode)
        self.filetype = self._resolve_filetype(filetype)
        self.key = tuple(key) if key else None
        self.data = data
        self.strict_keys = strict_keys
    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_path(path: str) -> str:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        return os.path.abspath(path)

    @staticmethod
    def _validate_mode(mode: str) -> str:
        if mode not in AsyncHistoryDump.modes:
            raise ValueError(f"Invalid mode: {mode}")
        return mode

    def _resolve_filetype(self, filetype: str) -> str:
        if filetype != "__autodetect__":
            if filetype not in self.filetypes:
                raise ValueError(f"Invalid filetype: {filetype}")
            return filetype

        if self.path.endswith(".json"):
            return "json"
        if self.path.endswith(".csv"):
            return "csv"
        if self.path.endswith(".txt"):
            return "txt"

        raise ValueError("Cannot autodetect filetype from path.")

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def write(self) -> None:
        if self.data is None:
            raise ValueError("No data to write")

        writer = self._writers[self.filetype]

        # Just call write_single() cleanly
        await writer.write_single(
            path=self.path,
            data=self.data,
            mode=self.mode,
            key=self.key,
            strict_keys = self.strict_keys
        )

    # -------------------------------------------------------------------------

    @classmethod
    async def write_many(cls, dumps: Iterable["AsyncHistoryDump"]) -> None:
        groups = defaultdict(list)

        # Group dumps by file (path, type, key)
        for d in dumps:
            if not isinstance(d, cls):
                raise TypeError(f"Expected AsyncHistoryDump, got {type(d).__name__}")
            groups[(d.path, d.filetype, tuple(d.key) if d.key else None)].append(d)

        tasks = []

        # Process each group with the appropriate writer
        for (path, filetype, key), batch in groups.items():
            writer = cls._writers[filetype]

            mode = batch[0].mode
            data_list = [d.data for d in batch]

            tasks.append(
                writer.write_batch(
                    path=path,
                    data_list=data_list,
                    mode=mode,
                    key=key,
                    strict_keys=batch[0].strict_keys
                )
            )

        await asyncio.gather(*tasks)
