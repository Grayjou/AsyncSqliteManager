from __future__ import annotations
from typing import Optional, Callable, Any
from .types import HistoryItem
from ..cloggable_list import CloggableList
from ..async_history_dump import AsyncHistoryDump, AsyncHistoryDumpGenerator
import asyncio

def default_history_format_function(history: HistoryItem) -> str:
    """
    Default function to format history entries for dumping.
    """
    query, path = history["query"], history["path"]
    if query == "COMMIT":
        return f"[{history['timestamp']}]({path}) : COMMIT\n"

    params, results = history["params"], history["result"]
    timestamp = history.get("timestamp", "no timestamp")
    return (
        f"[{timestamp}]({path})\n"
        f"{query}\n"
        f"Input: {params}\n"
        f"Output: {results}\n"
    )

class HistoryManager:
    """
    Manages query execution history and dumping.
    """
    
    def __init__(
        self,
        history_length: Optional[int] = 10,
        history_tolerance: Optional[int] = 5,
        history_dump_generator: Optional[AsyncHistoryDumpGenerator] = None,
        history_format_function: Callable[[HistoryItem], Any] = default_history_format_function,
    ) -> None:
        
        self.history_format_function = history_format_function
        self.history_dump_generator = history_dump_generator
        
        # Initialize history
        history_length = self._validate_none_or_non_neg_int(history_length)
        history_tolerance = self._validate_none_or_non_neg_int(history_tolerance)

        if history_length is None:
            self._history = None
        else:
            self._history = CloggableList(
                max_length=history_length, tolerance=history_tolerance
            )

        self._history_length = history_length
        self._history_tolerance = history_tolerance
        self._history_lock = asyncio.Lock()

    @staticmethod
    def _validate_none_or_non_neg_int(value: Optional[int]) -> Optional[int]:
        """Validate non-negative integer or None."""
        if value is not None and (not isinstance(value, int) or value < 0):
            raise ValueError("Value must be a non-negative integer or None")
        return value

    async def append(self, item: HistoryItem) -> None:
        """Append an item to history."""
        if not self.history or not self.history_dump_generator:
            return

        async with self._history_lock:
            dump = self.history_dump_generator.create(item)
            if isinstance(dump.data, dict):
                dump.data = self.history_format_function(dump.data)

            full = self.history.append(dump)
            if full:
                await self.flush_to_file()

    async def flush_to_file(self) -> None:
        """Flush history to file."""
        if self.history is None:
            return
        dumps = self.history.flush()
        await AsyncHistoryDump.write_many(dumps)

    # Property accessors
    @property
    def history(self) -> Optional[CloggableList]:
        return self._history

    @history.setter
    def history(self, value: Optional[CloggableList]) -> None:
        if value is not None and not isinstance(value, CloggableList):
            raise ValueError("history must be a CloggableList or None")
        self._history = value
        self._history_length = value.max_length if value is not None else None

    @property
    def history_length(self) -> Optional[int]:
        return self._history_length

    @history_length.setter
    def history_length(self, value: Optional[int]) -> None:
        value = self._validate_none_or_non_neg_int(value)
        if value is None:
            self._history_length = None
            self.history = None
        else:
            self._history_length = value
            if self.history is None:
                self.history = CloggableList(value, tolerance=self.history_tolerance)
            else:
                self.history.max_length = value

    @property
    def history_tolerance(self) -> Optional[int]:
        return self._history_tolerance

    @history_tolerance.setter
    def history_tolerance(self, value: Optional[int]) -> None:
        value = self._validate_none_or_non_neg_int(value)
        self._history_tolerance = value
        if self.history is not None:
            self.history.tolerance = value

    @property
    def history_dump_generator(self) -> Optional[AsyncHistoryDumpGenerator]:
        return self._history_dump_generator

    @history_dump_generator.setter
    def history_dump_generator(self, value: Optional[AsyncHistoryDumpGenerator]) -> None:
        if value is not None and not isinstance(value, AsyncHistoryDumpGenerator):
            raise ValueError("history_dump must be a AsyncHistoryDumpGenerator instance or None")
        self._history_dump_generator = value