from __future__ import annotations
from datetime import datetime
from typing import Optional, Callable, Union, Iterable
from .async_history_dump import AsyncHistoryDump, OutputData


def default_time_format_function(time_data: datetime) -> str:
    return time_data.strftime("%Y-%m-%d %H:%M:%S")


class AsyncHistoryDumpGenerator:
    """
    Factory for creating AsyncHistoryDump instances with consistent settings.

    Now fully aligned with the refactored AsyncHistoryDump API.
    """
    __slots__ = (
        "base_path",
        "filetype",
        "mode",
        "key",
        "log_time",
        "log_as",
        "time_format_function",
        "timestamp_key",
        "strict_keys",
    )

    def __init__(
        self,
        base_path: str,
        *,
        filetype: str = "__autodetect__",
        mode: str = "append",
        key: Optional[tuple[str, ...]] = None,
        log_time: bool = False,
        log_as: str = "key",
        time_format_function: Callable = default_time_format_function,
        timestamp_key: str = "timestamp",
        strict_keys: bool = False,
    ) -> None:

        self.base_path = base_path
        self.filetype = filetype
        self.mode = mode
        self.key = key
        self.log_time = log_time
        self.log_as = log_as
        self.time_format_function = time_format_function
        self.timestamp_key = timestamp_key
        self.strict_keys = strict_keys

    # --------------------------------------------------------------

    def _custom_or_default_time_format_function(self) -> str:
        return "Default" if self.time_format_function is default_time_format_function else "Custom"

    def __repr__(self) -> str:
        return (
            f"AsyncHistoryDumpGenerator(base_path={self.base_path}, "
            f"mode={self.mode}, filetype={self.filetype}, key={self.key}, "
            f"log_as={self.log_as}, strict_keys={self.strict_keys}, "
            f"time_format_function={self._custom_or_default_time_format_function()})"
        )

    # --------------------------------------------------------------

    def _add_timestamp(self, data: Optional[OutputData] = None) -> OutputData:
        """
        Add a timestamp to data using configured time_format_function.
        """
        if self.time_format_function is None:
            raise AttributeError("time_format_function is not set.")

        time_value = self.time_format_function(datetime.now())

        if data is None:
            data = {}

        if isinstance(data, dict):
            data[self.timestamp_key] = time_value

        elif isinstance(data, (list, tuple)):
            is_tuple = isinstance(data, tuple)
            data = list(data)
            if self.log_as == "append":
                data.append(time_value)
            else:
                data.append({self.timestamp_key: time_value})
            if is_tuple:
                data = tuple(data)

        else:
            if self.log_as == "append":
                data = (data, time_value)
            else:
                data = {"data": data, self.timestamp_key: time_value}

        return data

    # --------------------------------------------------------------

    def create(self, data: Optional[OutputData] = None) -> AsyncHistoryDump:
        """
        Produce a configured AsyncHistoryDump instance.
        """
        if self.log_time:
            data = self._add_timestamp(data)

        return AsyncHistoryDump(
            path=self.base_path,
            mode=self.mode,
            filetype=self.filetype,
            key=self.key,
            data=data,
            strict_keys=self.strict_keys,
        )

    # --------------------------------------------------------------

    def __call__(self, *args) -> AsyncHistoryDump | tuple[AsyncHistoryDump, ...]:
        """
        gen(x) -> one dump
        gen(x, y, z) -> tuple of dumps
        """
        if not args:
            raise ValueError("No data provided to AsyncHistoryDumpGenerator.")

        if len(args) == 1:
            return self.create(args[0])

        return tuple(self.create(d) for d in args)

    # --------------------------------------------------------------

    def create_many(self, *args) -> list[AsyncHistoryDump]:
        """
        gen.create_many(x, y, z) -> list of dumps
        """
        if len(args) == 1:
            return [self.create(args[0])]

        return [self.create(d) for d in args]
