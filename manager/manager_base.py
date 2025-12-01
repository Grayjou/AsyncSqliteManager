from __future__ import annotations
from aiosqlite import connect, Connection as AioConnection, Cursor as AioCursor
from contextlib import asynccontextmanager
import asyncio
from .history import HistoryManager, default_history_format_function
from .dbpathdict import DbPathDict
from .types import QueryParams, QueryResult, HistoryItem
from .exceptions import ConnectionError

from ..execution_async import try_query
from ..log import ExecutionLog
from typing import Optional, Callable, Any, Dict, Union, List
from logging import Logger, getLogger as logging_getLogger

from ..async_history_dump import AsyncHistoryDumpGenerator

class ManagerBase:

    def __init__(
        self,
        autocommit: bool = False,
        omni_log: bool = False,
        history_length: Optional[int] = 10,
        log_results: bool = True,
        logger: Optional[Logger] = None,
        history_dump_generator: Optional[AsyncHistoryDumpGenerator] = None,
        *,
        history_tolerance: Optional[int] = 5,
        history_format_function: Callable[[dict], Any] = default_history_format_function,
    ) -> None:

        self._db_dict: DbPathDict = DbPathDict()
        self.autocommit = autocommit
        self.omni_log = omni_log
        self.log_results = log_results
        self.logger = logger or logging_getLogger(__name__)

        # Initialize history manager
        self._history_manager = HistoryManager(
            history_length=history_length,
            history_tolerance=history_tolerance,
            history_dump_generator=history_dump_generator,
            history_format_function=history_format_function,
        )

        self._locks: dict[str, asyncio.Lock] = {}
    # Connection Management
    def _get_lock(self, db_path: str) -> asyncio.Lock:
        return self._locks.setdefault(db_path, asyncio.Lock())

    def get_connection(self, path_or_alias: str) -> Optional[AioConnection]:
        """Get the connection associated with a given path or alias."""
        return self.db_dict.get(path_or_alias)

    async def close(self, db_path: str) -> None:
        """Close a database connection."""
        if db_path in self.db_dict:
            conn = self.get_connection(db_path)
            await conn.close() #type: ignore
            self._db_dict.__delitem__(db_path)
            self._locks.pop(db_path, None)

    disconnect = close
    # Properties
    @property
    def db_dict(self) -> DbPathDict:
        return self._db_dict

    @property
    def databases(self) -> list[str]:
        return self.db_dict.paths

    @property
    def history_length(self) -> Optional[int]:
        return self._history_manager.history_length

    @history_length.setter
    def history_length(self, value: Optional[int]) -> None:
        self._history_manager.history_length = value

    @property
    def history_tolerance(self) -> Optional[int]:
        return self._history_manager.history_tolerance

    @history_tolerance.setter
    def history_tolerance(self, value: Optional[int]) -> None:
        self._history_manager.history_tolerance = value

    @property
    def history_dump_generator(self) -> Optional[AsyncHistoryDumpGenerator]:
        return self._history_manager.history_dump_generator

    @history_dump_generator.setter
    def history_dump_generator(self, value: Optional[AsyncHistoryDumpGenerator]) -> None:
        self._history_manager.history_dump_generator = value

    


    # Utility Methods
    def _should_log(self, log: bool, override_omnilog: bool = False) -> bool:
        return log or (self.omni_log and not override_omnilog)

    def _should_commit(self, commit: bool, override_autocommit: bool = False) -> bool:
        return commit or (self.autocommit and not override_autocommit)

    def _call_logger(self, method: str, *args, **kwargs) -> None:
        if self.logger:
            f = getattr(self.logger, method, None)
            if callable(f):
                f(*args, **kwargs)

    async def _append_history(self, item: HistoryItem) -> None:
        await self._history_manager.append(item)

    async def flush_history_to_file(self) -> None:
        await self._history_manager.flush_to_file()

    async def connect(self, db_path: str, alias = None) -> AioConnection:
        """Connect to a SQLite database."""
        if db_path in self.db_dict:
            return self.db_dict[db_path]
        
        try:
            conn = await connect(db_path)
            self._db_dict[db_path] = conn
            self._db_dict.setalias(db_path, alias)
            return conn
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {db_path}: {e}") from e

    async def execute(
        self,
        db_path: str,
        query: str,
        params: Optional[QueryParams] = None,
        return_type: str = "fetchall",
        *,
        cursor: Optional[AioCursor] = None,
        commit: bool = False,
        override_autocommit: bool = False,
        log: bool = False,
        override_omnilog: bool = False
    ) -> QueryResult:
        """
        Execute a SQL query on the specified database.

        Args:
            db_path (str): Path or alias of the target SQLite database.
            query (str): SQL query to execute.
            params (tuple or list of tuples, optional): Parameters to inject.
            return_type (str): Return strategy ('fetchall', 'fetchone', etc.).
            cursor (AioCursor, optional): Cursor to use for execution. If provided,
                this cursor is used instead of creating a new one. Useful for
                transactions that need to execute multiple queries with the same cursor.
            commit (bool): Whether to commit after execution.
            override_autocommit (bool): Force override of autocommit behavior.
            log (bool): Whether to log this query.
            override_omnilog (bool): Force override of omni_log behavior.

        Returns:
            Optional[List[Any]]: Query results, if any.
        """
        conn = await self.connect(db_path)
        params = params or ()

        if cursor is not None:
            # Use the provided cursor
            result = await try_query(
                cursor=cursor,
                query=query,
                commit=False,  # IMPORTANT: never auto-commit inside exec
                injection_values=params,
                return_type=return_type,
                log=log,
                raise_on_fail=True,
                notify_bulk=False,
                force_notify_bulk=False,
                convert_to_dollar=False,
            )
        else:
            # Create a new cursor
            async with conn.cursor() as new_cursor:
                result = await try_query(
                    cursor=new_cursor,
                    query=query,
                    commit=False,  # IMPORTANT: never auto-commit inside exec
                    injection_values=params,
                    return_type=return_type,
                    log=log,
                    raise_on_fail=True,
                    notify_bulk=False,
                    force_notify_bulk=False,
                    convert_to_dollar=False,
                )

        # commit logic:
        if self._should_commit(commit, override_autocommit):
            await conn.commit()
            await self._append_history(
                {
                    "path": db_path,
                    "query": "COMMIT",
                    "params": None,
                    "timestamp": None,
                    "result": None,
                }
            )

        # logging/history:
        if self._should_log(log, override_omnilog):
            self._call_logger("info", f"{query} | {params}")

        if self.log_results:
            await self._append_history(
                ExecutionLog(db_path, query, params, return_type, result).to_dict()
            )

        return result

   # Transaction Management
    async def commit(self, db_path: str, log: bool = False, override_omnilog: bool = False) -> None:
        """Commit the current transaction."""
        conn = self.get_connection(db_path)
        if conn is None:
            return
        await conn.commit()

        await self._append_history({
            "path": db_path,
            "query": "COMMIT",
            "params": None,
            "timestamp": None,
            "result": None,
        })

        if self._should_log(log, override_omnilog):
            self._call_logger("info", f"Commit on {db_path}")

    async def rollback(self, db_path: str, log: bool = False, override_omnilog: bool = False) -> None:
        """Rollback the current transaction."""

        conn = self.get_connection(db_path)
        if conn is None:
            return
        await conn.rollback()

        await self._append_history({
            "path": db_path,
            "query": "ROLLBACK",
            "params": None,
            "timestamp": None,
            "result": None,
        })

        if self._should_log(log, override_omnilog):
            self._call_logger("info", f"Rollback on {db_path}")

    # Savepoint Management
    async def savepoint(self, db_path: str, name: str) -> None:
        """Create a named savepoint."""
        conn = self.get_connection(db_path)
        if conn is None:
            return
        await conn.execute(f"SAVEPOINT {name}")
        self._call_logger("info", f"SAVEPOINT {name} created in {db_path}")

    async def rollback_to(self, db_path: str, name: str) -> None:
        """Roll back to a savepoint."""
        conn = self.get_connection(db_path)
        if conn is None:
            return
        await conn.execute(f"ROLLBACK TO {name}")
        self._call_logger("info", f"ROLLBACK TO SAVEPOINT {name} in {db_path}")

    async def release_savepoint(self, db_path: str, name: str) -> None:
        """Release a savepoint."""
        conn = self.get_connection(db_path)
        if conn is None:
            return
        await conn.execute(f"RELEASE SAVEPOINT {name}")
        self._call_logger("info", f"SAVEPOINT {name} released in {db_path}")