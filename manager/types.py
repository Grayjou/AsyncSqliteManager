from __future__ import annotations
from typing import Optional, Union, List, Any, Generator, Callable, Set, Type, TypeVar
from aiosqlite import Connection as AioConnection
from logging import Logger

# Type aliases
QueryParams = Optional[Union[tuple, List[tuple]]]
QueryResult = Optional[List[Any]]
HistoryItem = dict[str, Any]