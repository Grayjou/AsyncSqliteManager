# tests/manager/test_exceptions.py
import pytest
from ...manager.exceptions import (
    AsyncSQLiteError,
    ConnectionError,
    TransactionError,
    HistoryError,
)


def test_async_sqlite_error_is_base_exception():
    """Test that AsyncSQLiteError is an Exception subclass."""
    error = AsyncSQLiteError("test error")
    assert isinstance(error, Exception)


def test_connection_error_inherits_from_base():
    """Test that ConnectionError inherits from AsyncSQLiteError."""
    error = ConnectionError("connection failed")
    assert isinstance(error, AsyncSQLiteError)
    assert isinstance(error, Exception)


def test_transaction_error_inherits_from_base():
    """Test that TransactionError inherits from AsyncSQLiteError."""
    error = TransactionError("transaction failed")
    assert isinstance(error, AsyncSQLiteError)
    assert isinstance(error, Exception)


def test_history_error_inherits_from_base():
    """Test that HistoryError inherits from AsyncSQLiteError."""
    error = HistoryError("history failed")
    assert isinstance(error, AsyncSQLiteError)
    assert isinstance(error, Exception)


def test_exception_message():
    """Test that exception messages are properly stored."""
    msg = "test message"
    error = AsyncSQLiteError(msg)
    assert str(error) == msg


def test_connection_error_can_be_raised_and_caught():
    """Test that ConnectionError can be raised and caught as AsyncSQLiteError."""
    with pytest.raises(AsyncSQLiteError):
        raise ConnectionError("test")


def test_transaction_error_can_be_raised_and_caught():
    """Test that TransactionError can be raised and caught as AsyncSQLiteError."""
    with pytest.raises(AsyncSQLiteError):
        raise TransactionError("test")


def test_history_error_can_be_raised_and_caught():
    """Test that HistoryError can be raised and caught as AsyncSQLiteError."""
    with pytest.raises(AsyncSQLiteError):
        raise HistoryError("test")
