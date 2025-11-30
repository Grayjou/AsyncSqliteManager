class AsyncSQLiteError(Exception):
    """Base exception for async SQLite manager."""
    pass

class ConnectionError(AsyncSQLiteError):
    """Raised when connection operations fail."""
    pass

class TransactionError(AsyncSQLiteError):
    """Raised when transaction operations fail."""
    pass

class HistoryError(AsyncSQLiteError):
    """Raised when history operations fail."""
    pass