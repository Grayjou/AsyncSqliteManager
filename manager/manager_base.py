from __future__ import annotations
from aiosqlite import connect, Connection as AioConnection, Cursor as AioCursor
from contextlib import asynccontextmanager
import asyncio
import re
from .history import HistoryManager, default_history_format_function
from .dbpathdict import DbPathDict, PathConnection
from .types import QueryParams, QueryResult, HistoryItem
from .exceptions import ConnectionError

from ..execution_async import try_query
from ..execution_async.row_factory import type_converting_row_factory, custom_row_factory
from ..log import ExecutionLog
from typing import Optional, Callable, Any, Dict, Union, List, Literal, Tuple, Type
from logging import Logger, getLogger as logging_getLogger

from ..async_history_dump import AsyncHistoryDumpGenerator

# Regex for validating savepoint names to prevent SQL injection
_VALID_SAVEPOINT_NAME = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

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

    def get_connection(
        self,
        path_or_alias: str,
        mode: Literal["read", "write"] = "write"
    ) -> Optional[AioConnection]:
        """
        Get the connection associated with a given path or alias.
        
        Args:
            path_or_alias: The path or alias of the database.
            mode: "read" or "write", defaults to "write" for backwards compatibility.
            
        Returns:
            The connection for the specified mode, or None if not found.
        """
        return self.db_dict.get_connection(path_or_alias, mode)

    def get_path_connection(self, path_or_alias: str) -> Optional[PathConnection]:
        """
        Get the PathConnection object associated with a given path or alias.
        
        Args:
            path_or_alias: The path or alias of the database.
            
        Returns:
            The PathConnection object, or None if not found.
        """
        return self.db_dict.get_path_connection(path_or_alias)

    async def close(self, db_path: str) -> None:
        """Close a database connection (both read and write connections)."""
        if db_path in self.db_dict:
            pc = self.get_path_connection(db_path)
            if pc:
                # Close write connection
                if pc.write_conn:
                    await pc.write_conn.close()
                # Close read connection if it exists and is different from write
                if pc.read_conn and pc.read_conn is not pc.write_conn:
                    await pc.read_conn.close()
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

    def _should_commit(self, commit: bool, override_autocommit: bool = False, mode: Literal["read", "write"] = "write") -> bool:
        return (commit or (self.autocommit and not override_autocommit)) and mode == "write"

    def _call_logger(self, method: str, *args, **kwargs) -> None:
        if self.logger:
            f = getattr(self.logger, method, None)
            if callable(f):
                f(*args, **kwargs)

    async def _append_history(self, item: HistoryItem) -> None:
        await self._history_manager.append(item)

    async def flush_history_to_file(self) -> None:
        await self._history_manager.flush_to_file()

    async def connect(
        self,
        db_path: str,
        alias: Optional[str] = None,
        *,
        create_read_connection: bool = False,
        mode: Literal["read", "write"] = "write"
    ) -> AioConnection:
        """
        Connect to a SQLite database.
        
        Args:
            db_path: Path to the SQLite database file.
            alias: Optional alias for the database path.
            create_read_connection: If True, creates a separate read connection.
            mode: "read" or "write" - specifies which connection to return.
            
        Returns:
            The requested connection to the database.
            
        Note:
            All connections use a custom row_factory that automatically converts
            string representations of integers to int type. This is useful for
            working with IntEnum and similar types that require integer values.
        """
        if db_path in self.db_dict:
            pc = self.db_dict[db_path]
            # If read connection is requested but doesn't exist, create it
            if create_read_connection and pc.read_conn is None:
                try:
                    pc.read_conn = await connect(db_path)
                    pc.read_conn.row_factory = type_converting_row_factory
                except Exception as e:
                    raise ConnectionError(f"Failed to create read connection to {db_path}: {e}") from e
            
            if mode == "read":
                if pc.read_conn is None:
                    raise ConnectionError(f"No read connection available for {db_path}")
                return pc.read_conn
            return pc.write_conn
        
        try:
            write_conn = await connect(db_path)
            write_conn.row_factory = type_converting_row_factory
            
            read_conn = None
            if create_read_connection:
                read_conn = await connect(db_path)
                read_conn.row_factory = type_converting_row_factory
            
            pc = PathConnection(
                path=db_path,
                write_conn=write_conn,
                read_conn=read_conn,
                alias=alias
            )
            self._db_dict[db_path] = pc
            if mode == "read":
                if pc.read_conn is None:
                    raise ConnectionError(f"No read connection available for {db_path}")
                return pc.read_conn
            return write_conn
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
        override_omnilog: bool = False,
        mode : Literal["read", "write"] = "write",
        create_read_connection: bool = True,
        expected_types: Optional[Tuple[Optional[Type], ...]] = None,
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
            mode (Literal["read", "write"], optional): Connection mode to use. Defaults to "write".
                - "read": Use a read-only connection (if available). Best for SELECT queries
                  to improve concurrency. Falls back to write connection if no read connection exists.
                - "write": Use the write connection. Required for INSERT, UPDATE, DELETE, and DDL queries.
            create_read_connection (bool, optional): If True and mode="read", creates a separate 
                read connection if it doesn't exist. Defaults to True.
            expected_types (Optional[Tuple[Optional[Type], ...]], optional): A tuple of expected types 
                for type conversion. Can be shorter than the number of columns (remaining columns use 
                automatic conversion). Use None for a column to skip conversion for that column.
                If not provided, uses default automatic type conversion.

        Returns:
            Optional[List[Any]]: Query results, if any.
            
        Note:
            By default, query results use automatic type conversion - string representations of integers
            are automatically converted to int type. This is useful for working with IntEnum
            and other types that require integer values. You can customize this behavior using the
            expected_types parameter.
            
        Connection Mode Best Practices:
            - Use mode="read" for all SELECT queries to leverage read connection and improve
              concurrent read performance.
            - Use mode="write" (default) for INSERT, UPDATE, DELETE, CREATE, ALTER, DROP queries.
            - Read connections can execute simultaneously without blocking each other.
            - Write operations will block other operations on the same database.
            
        Performance Implications:
            - Read mode with separate read connection: Multiple simultaneous reads possible.
            - Write mode: Serialized access, one operation at a time per database.
            - Creating separate read connections adds overhead but improves concurrency.
            
        Examples:
            # Read-only query using read connection
            users = await manager.execute("mydb", "SELECT * FROM users", mode="read")
            
            # Write query using write connection (default)
            await manager.execute("mydb", "INSERT INTO users VALUES (?, ?)", 
                                params=(1, "Alice"), commit=True, mode="write")
            
            # Read query with explicit write connection
            count = await manager.execute("mydb", "SELECT COUNT(*) FROM users", mode="write")
            
            # Query with custom type conversion
            result = await manager.execute("mydb", "SELECT status, count, name, description",
                                         expected_types=(bool, int))
            # First column converted to bool, second to int, rest use default conversion
            
            # Query with selective type conversion
            result = await manager.execute("mydb", "SELECT id, name, count",
                                         expected_types=(None, None, int))
            # Skip first two columns, convert third to int
        """
        conn = await self.connect(db_path, mode=mode, create_read_connection=create_read_connection and mode=="read")
        params = params or ()
        
        # Note: We cannot change row_factory dynamically for cursors that have already
        # executed queries. Instead, we'll apply type conversion after fetching results.
        result = None
        
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
            # Create a new cursor with custom row_factory if needed
            if expected_types is not None:
                original_row_factory = conn.row_factory
                conn.row_factory = custom_row_factory(expected_types)
                try:
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
                finally:
                    conn.row_factory = original_row_factory
            else:
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
        
        # Apply type conversion post-fetch if needed and cursor was provided
        if expected_types is not None and cursor is not None and result is not None:
            factory = custom_row_factory(expected_types)
            # The factory function doesn't use the cursor parameter, but we pass None
            # for API consistency with the row_factory signature
            result = [factory(None, row) for row in result]

        # commit logic:

        if self._should_commit(commit, override_autocommit, mode=mode):

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
    @staticmethod
    def _validate_savepoint_name(name: str) -> None:
        """Validate savepoint name to prevent SQL injection.
        
        Args:
            name: The savepoint name to validate.
            
        Raises:
            ValueError: If the name contains invalid characters.
        """
        if not _VALID_SAVEPOINT_NAME.match(name):
            raise ValueError(
                "Invalid savepoint name. "
                "Must start with a letter or underscore and contain only alphanumeric characters and underscores."
            )

    async def savepoint(self, db_path: str, name: str) -> None:
        """Create a named savepoint.
        
        Args:
            db_path: Path or alias of the database.
            name: Name of the savepoint. Must be alphanumeric with underscores only.
            
        Raises:
            ValueError: If the savepoint name is invalid.
        """
        self._validate_savepoint_name(name)
        conn = self.get_connection(db_path)
        if conn is None:
            return
        await conn.execute(f"SAVEPOINT {name}")
        self._call_logger("info", f"SAVEPOINT {name} created in {db_path}")

    async def rollback_to(self, db_path: str, name: str) -> None:
        """Roll back to a savepoint.
        
        Args:
            db_path: Path or alias of the database.
            name: Name of the savepoint to roll back to.
            
        Raises:
            ValueError: If the savepoint name is invalid.
        """
        self._validate_savepoint_name(name)
        conn = self.get_connection(db_path)
        if conn is None:
            return
        await conn.execute(f"ROLLBACK TO {name}")
        self._call_logger("info", f"ROLLBACK TO SAVEPOINT {name} in {db_path}")

    async def release_savepoint(self, db_path: str, name: str) -> None:
        """Release a savepoint.
        
        Args:
            db_path: Path or alias of the database.
            name: Name of the savepoint to release.
            
        Raises:
            ValueError: If the savepoint name is invalid.
        """
        self._validate_savepoint_name(name)
        conn = self.get_connection(db_path)
        if conn is None:
            return
        await conn.execute(f"RELEASE SAVEPOINT {name}")
        self._call_logger("info", f"SAVEPOINT {name} released in {db_path}")
