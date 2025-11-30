"""
High-level async SQLite manager.

Public API:

    from your_package import Manager

    manager = Manager(autocommit=False, omni_log=True)

    await manager.connect("example.db")
    rows = await manager.execute("example.db", "SELECT 1")

    async with manager.Transaction("example.db") as txn:
        await txn.execute("INSERT INTO test (value) VALUES (?)", (42,))

The lower-level pieces (ManagerBase, HistoryManager, DbPathDict, etc.)
are also exported for advanced/custom integrations, but the recommended
entry point is `Manager`.
"""

from .manager import Manager            # High-level manager facade
from .manager_base import ManagerBase    # Core implementation

from .transaction import Transaction     # Transaction context manager

from .history import (
    HistoryManager,
    default_history_format_function,
)

from .dbpathdict import (
    PathConnection,
    DbPathDict,
)

from .exceptions import (
    AsyncSQLiteError,
    ConnectionError,
    TransactionError,
    HistoryError,
)

from .types import (
    QueryParams,
    QueryResult,
    HistoryItem,
)
AsyncSQLiteManager = Manager

__all__ = [
    # Main entry points
    "Manager",
    "Transaction",

    # Advanced / extension points
    "ManagerBase",
    "HistoryManager",
    "default_history_format_function",
    "PathConnection",
    "DbPathDict",

    # Exceptions
    "AsyncSQLiteError",
    "ConnectionError",
    "TransactionError",
    "HistoryError",

    # Typing helpers
    "QueryParams",
    "QueryResult",
    "HistoryItem",
]
