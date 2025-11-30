from __future__ import annotations
from contextlib import asynccontextmanager
from .transaction import Transaction
from .history import default_history_format_function
from typing import Optional, Callable, Any
from logging import Logger
from .manager_base import ManagerBase
from ..async_history_dump import AsyncHistoryDumpGenerator

class Manager(ManagerBase):
    """
    A database connection and query manager for SQLite databases.
    """

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

        super().__init__(
            autocommit=autocommit,
            omni_log=omni_log,
            history_length=history_length,
            log_results=log_results,
            logger=logger,
            history_dump_generator=history_dump_generator,
            history_tolerance=history_tolerance,
            history_format_function=history_format_function,
        )


    @asynccontextmanager
    async def queue(self, db_path: str):
        """Serialize all queries and transactions for this database path."""
        lock = self._get_lock(db_path)
        async with lock:
            yield

    @asynccontextmanager
    async def safe_transaction(self, db_path: str, **kw):
        """Transaction that automatically acquires the per-DB lock."""
        async with self.queue(db_path):
            async with self.Transaction(db_path, **kw) as txn:
                yield txn

    # Lifecycle Management
    async def disconnect_all(self) -> None:
        for db_path in self.databases:
            await self.close(db_path)

    async def shutdown(self) -> None:
        await self.disconnect_all()
        await self.flush_history_to_file()
        if self.logger:
            self.logger.info("Manager instance shut down.")

    # Decorator for transactions
    @staticmethod
    def with_transaction(db_path: str, *, autocommit=True, log_all=False):
        def decorator(func):
            async def wrapper(self: Manager, *args, **kwargs):
                self_or_manager = args[0]
                manager = self_or_manager if isinstance(self_or_manager, Manager) else self

                async with manager.Transaction(db_path, autocommit, log_all):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator

    def Transaction(self, database_path: str, autocommit: bool = True,
                    log_all: bool = False, manager: Optional[Manager] = None,
                    logger: Optional[Logger] = None) -> Transaction:
        return Transaction(database_path, autocommit, log_all, manager or self, logger or self.logger)