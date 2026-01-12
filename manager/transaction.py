from __future__ import annotations
from typing import Optional, Type, Literal, Tuple
from logging import Logger, getLogger as logging_getLogger
from .types import QueryParams, QueryResult
from .exceptions import TransactionError
from aiosqlite import Connection as AioConnection, Cursor as AioCursor
from .manager_base import ManagerBase

class Transaction:
    """
    A context manager for handling SQLite transactions.
    """
    
    def __init__(
        self,
        database_path: str,
        autocommit: bool = True,
        log_all: bool = False,
        manager: Optional[ManagerBase] = None,
        logger: Optional[Logger] = None
    ):
        self.database_path = database_path
        self.autocommit = autocommit
        if manager is None:
            raise TransactionError("Transaction requires an existing ManagerBase instance.")
        self.manager = manager
        self.logger = logger or logging_getLogger(__name__)
        self._connection: Optional[AioConnection] = None
        self._cursor: Optional[AioCursor] = None
        self._succeeded: Optional[bool] = None  # Track transaction outcome

    async def __aenter__(self) -> Transaction:
        """Enter the transaction context."""
        self._connection = await self.manager.connect(self.database_path)
        if self._connection is None:
            raise TransactionError(f"Failed to connect to database: {self.database_path}")
        
        # Create a cursor for the transaction to reuse across multiple queries
        self._cursor = await self._connection.cursor()
        
        try:
            await self._cursor.execute("BEGIN")
            self.logger.info(f"BEGIN transaction on database: {self.database_path}")
        except Exception as e:
            # Close cursor on failure
            if self._cursor:
                await self._cursor.close()
                self._cursor = None
            self.logger.error(f"Failed to BEGIN transaction: {e}")
            raise TransactionError(f"Failed to begin transaction: {e}") from e
            
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], 
                       exc_val: Optional[BaseException], exc_tb) -> None:
        """Exit the transaction context."""
        if not self._connection:
            self.logger.warning(f"No connection to close for database: {self.database_path}")
            return
            
        try:
            if exc_type is not None:
                await self._connection.rollback()
                self.logger.error(f"ROLLBACK transaction on database: {self.database_path}")
                self._succeeded = False
            elif self.autocommit:
                await self.manager.commit(self.database_path)
                self.logger.info(f"COMMIT transaction on database: {self.database_path}")
                self._succeeded = True
            else:
                await self._connection.rollback()
                self.logger.info(f"ROLLBACK transaction on database: {self.database_path}")
                self._succeeded = False
        except Exception as e:
            self.logger.error(f"Failed to commit/rollback transaction: {e}")
            self._succeeded = False
            raise
        finally:
            # Close the cursor when exiting the transaction
            if self._cursor:
                await self._cursor.close()
                self._cursor = None

    async def execute(
        self,
        query: str,
        params: QueryParams = None,
        return_type: str = "fetchall",
        commit: bool = False,
        override_autocommit: bool = False,
        log: bool = False,
        override_omnilog: bool = False,
        mode : Literal["read", "write"] = "write",
        expected_types: Optional[Tuple[Optional[Type], ...]] = None,
    ) -> QueryResult:
        return await self.manager.execute(
            db_path=self.database_path,
            query=query,
            params=params,
            return_type=return_type,
            cursor=self._cursor,
            commit=commit,
            override_autocommit=override_autocommit,
            log=log,
            override_omnilog=override_omnilog,
            mode=mode,
            expected_types=expected_types,
        )

    async def commit(self, log: bool = False, override_omnilog: bool = False) -> None:
        """Commit the current transaction."""
        await self.manager.commit(self.database_path, log=log, override_omnilog=override_omnilog)

    async def rollback(self, log: bool = False, override_omnilog: bool = False) -> None:
        """Rollback the current transaction."""
        await self.manager.rollback(self.database_path, log=log, override_omnilog=override_omnilog)

    async def savepoint(self, name: str) -> None:
        """Create a named savepoint."""
        await self.manager.savepoint(self.database_path, name)

    async def rollback_to(self, name: str) -> None:
        """Roll back to a savepoint."""
        await self.manager.rollback_to(self.database_path, name)

    async def release_savepoint(self, name: str) -> None:
        """Release a savepoint."""
        await self.manager.release_savepoint(self.database_path, name)
    
    @property
    def succeeded(self) -> Optional[bool]:
        """
        Check if the transaction succeeded (committed).
        
        Returns:
            True if transaction was committed, False if rolled back, None if still in progress.
            
        Note:
            This property is accessible after the transaction context exits.
        """
        return self._succeeded
    
    @property
    def failed(self) -> Optional[bool]:
        """
        Check if the transaction failed (rolled back).
        
        Returns:
            True if transaction was rolled back, False if committed, None if still in progress.
            
        Note:
            This property is accessible after the transaction context exits.
        """
        if self._succeeded is None:
            return None
        return not self._succeeded
