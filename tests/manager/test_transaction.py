# tests/manager/test_transaction.py
import pytest
from unittest.mock import MagicMock, AsyncMock
from ...manager.transaction import Transaction
from ...manager.exceptions import TransactionError


class TestTransaction:
    """Tests for Transaction class."""

    def test_init_without_manager_raises(self):
        """Test Transaction raises TransactionError when manager is None."""
        with pytest.raises(TransactionError) as exc_info:
            Transaction("test.db", manager=None)
        assert "requires an existing ManagerBase instance" in str(exc_info.value)

    def test_init_with_manager(self):
        """Test Transaction initialization with manager."""
        mock_manager = MagicMock()
        txn = Transaction("test.db", manager=mock_manager)
        assert txn.database_path == "test.db"
        assert txn.autocommit is True
        assert txn.manager is mock_manager

    def test_init_with_custom_options(self):
        """Test Transaction initialization with custom options."""
        mock_manager = MagicMock()
        mock_logger = MagicMock()
        txn = Transaction(
            "test.db",
            autocommit=False,
            log_all=True,
            manager=mock_manager,
            logger=mock_logger,
        )
        assert txn.database_path == "test.db"
        assert txn.autocommit is False
        assert txn.logger is mock_logger

    @pytest.mark.asyncio
    async def test_aenter_connects_and_begins(self):
        """Test __aenter__ connects to database and begins transaction."""
        mock_manager = MagicMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor = AsyncMock(return_value=mock_cursor)
        mock_manager.connect = AsyncMock(return_value=mock_conn)

        txn = Transaction("test.db", manager=mock_manager)
        result = await txn.__aenter__()

        mock_manager.connect.assert_awaited_once_with("test.db")
        mock_conn.cursor.assert_awaited_once()
        mock_cursor.execute.assert_awaited_once_with("BEGIN")
        assert result is txn
        assert txn._cursor is mock_cursor

    @pytest.mark.asyncio
    async def test_aenter_raises_if_connection_fails(self):
        """Test __aenter__ raises TransactionError if connection returns None."""
        mock_manager = MagicMock()
        mock_manager.connect = AsyncMock(return_value=None)

        txn = Transaction("test.db", manager=mock_manager)
        with pytest.raises(TransactionError) as exc_info:
            await txn.__aenter__()
        assert "Failed to connect to database" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_aenter_raises_if_begin_fails(self):
        """Test __aenter__ raises TransactionError if BEGIN fails."""
        mock_manager = MagicMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_cursor.execute.side_effect = Exception("BEGIN failed")
        mock_conn.cursor = AsyncMock(return_value=mock_cursor)
        mock_manager.connect = AsyncMock(return_value=mock_conn)

        txn = Transaction("test.db", manager=mock_manager)
        with pytest.raises(TransactionError) as exc_info:
            await txn.__aenter__()
        assert "Failed to begin transaction" in str(exc_info.value)
        # Cursor should be closed on failure
        mock_cursor.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_commits_on_success_with_autocommit(self):
        """Test __aexit__ commits when no exception and autocommit=True."""
        mock_manager = MagicMock()
        mock_manager.commit = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor = AsyncMock(return_value=mock_cursor)
        mock_manager.connect = AsyncMock(return_value=mock_conn)

        txn = Transaction("test.db", autocommit=True, manager=mock_manager)
        await txn.__aenter__()
        await txn.__aexit__(None, None, None)

        mock_manager.commit.assert_awaited_once_with("test.db")
        mock_cursor.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_rollback_on_exception(self):
        """Test __aexit__ rolls back when exception occurred."""
        mock_manager = MagicMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor = AsyncMock(return_value=mock_cursor)
        mock_manager.connect = AsyncMock(return_value=mock_conn)

        txn = Transaction("test.db", manager=mock_manager)
        await txn.__aenter__()
        await txn.__aexit__(ValueError, ValueError("test"), None)

        mock_conn.rollback.assert_awaited_once()
        mock_cursor.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_rollback_without_autocommit(self):
        """Test __aexit__ rolls back when autocommit=False and no exception."""
        mock_manager = MagicMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor = AsyncMock(return_value=mock_cursor)
        mock_manager.connect = AsyncMock(return_value=mock_conn)

        txn = Transaction("test.db", autocommit=False, manager=mock_manager)
        await txn.__aenter__()
        await txn.__aexit__(None, None, None)

        mock_conn.rollback.assert_awaited_once()
        mock_cursor.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_logs_warning_if_no_connection(self):
        """Test __aexit__ logs warning if no connection exists."""
        mock_manager = MagicMock()
        mock_logger = MagicMock()
        txn = Transaction("test.db", manager=mock_manager, logger=mock_logger)
        txn._connection = None

        await txn.__aexit__(None, None, None)
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_delegates_to_manager(self):
        """Test execute delegates to manager.execute."""
        mock_manager = MagicMock()
        mock_manager.execute = AsyncMock(return_value=[(1,)])
        mock_cursor = AsyncMock()

        txn = Transaction("test.db", manager=mock_manager)
        txn._cursor = mock_cursor
        result = await txn.execute("SELECT 1", params=(1,), return_type="fetchone")

        mock_manager.execute.assert_awaited_once_with(
            db_path="test.db",
            query="SELECT 1",
            params=(1,),
            return_type="fetchone",
            cursor=mock_cursor,
            commit=False,
            override_autocommit=False,
            log=False,
            override_omnilog=False,
        )
        assert result == [(1,)]

    @pytest.mark.asyncio
    async def test_commit_delegates_to_manager(self):
        """Test commit delegates to manager.commit."""
        mock_manager = MagicMock()
        mock_manager.commit = AsyncMock()

        txn = Transaction("test.db", manager=mock_manager)
        await txn.commit(log=True)

        mock_manager.commit.assert_awaited_once_with(
            "test.db", log=True, override_omnilog=False
        )

    @pytest.mark.asyncio
    async def test_rollback_delegates_to_manager(self):
        """Test rollback delegates to manager.rollback."""
        mock_manager = MagicMock()
        mock_manager.rollback = AsyncMock()

        txn = Transaction("test.db", manager=mock_manager)
        await txn.rollback()

        mock_manager.rollback.assert_awaited_once_with(
            "test.db", log=False, override_omnilog=False
        )

    @pytest.mark.asyncio
    async def test_savepoint_delegates_to_manager(self):
        """Test savepoint delegates to manager.savepoint."""
        mock_manager = MagicMock()
        mock_manager.savepoint = AsyncMock()

        txn = Transaction("test.db", manager=mock_manager)
        await txn.savepoint("sp1")

        mock_manager.savepoint.assert_awaited_once_with("test.db", "sp1")

    @pytest.mark.asyncio
    async def test_rollback_to_delegates_to_manager(self):
        """Test rollback_to delegates to manager.rollback_to."""
        mock_manager = MagicMock()
        mock_manager.rollback_to = AsyncMock()

        txn = Transaction("test.db", manager=mock_manager)
        await txn.rollback_to("sp1")

        mock_manager.rollback_to.assert_awaited_once_with("test.db", "sp1")

    @pytest.mark.asyncio
    async def test_release_savepoint_delegates_to_manager(self):
        """Test release_savepoint delegates to manager.release_savepoint."""
        mock_manager = MagicMock()
        mock_manager.release_savepoint = AsyncMock()

        txn = Transaction("test.db", manager=mock_manager)
        await txn.release_savepoint("sp1")

        mock_manager.release_savepoint.assert_awaited_once_with("test.db", "sp1")

    @pytest.mark.asyncio
    async def test_transaction_reuses_cursor_for_multiple_queries(self):
        """Test that Transaction reuses the same cursor for multiple execute calls."""
        mock_manager = MagicMock()
        mock_manager.execute = AsyncMock(return_value=[])
        mock_manager.commit = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor = AsyncMock(return_value=mock_cursor)
        mock_manager.connect = AsyncMock(return_value=mock_conn)

        txn = Transaction("test.db", manager=mock_manager)
        await txn.__aenter__()

        # Execute multiple queries
        await txn.execute("CREATE TABLE test (id INTEGER)")
        await txn.execute("INSERT INTO test VALUES (1)")
        await txn.execute("SELECT * FROM test")

        # All execute calls should use the same cursor
        assert mock_manager.execute.await_count == 3
        for call in mock_manager.execute.await_args_list:
            assert call.kwargs['cursor'] is mock_cursor

        await txn.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_cursor_is_closed_on_aexit(self):
        """Test that cursor is properly closed when exiting transaction."""
        mock_manager = MagicMock()
        mock_manager.commit = AsyncMock()
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor = AsyncMock(return_value=mock_cursor)
        mock_manager.connect = AsyncMock(return_value=mock_conn)

        txn = Transaction("test.db", manager=mock_manager)
        await txn.__aenter__()

        # Verify cursor is stored
        assert txn._cursor is mock_cursor

        await txn.__aexit__(None, None, None)

        # Verify cursor is closed
        mock_cursor.close.assert_awaited_once()
        assert txn._cursor is None

    @pytest.mark.asyncio
    async def test_cursor_is_closed_on_exception_during_aexit(self):
        """Test that cursor is closed even when commit/rollback raises."""
        mock_manager = MagicMock()
        mock_manager.commit = AsyncMock(side_effect=Exception("Commit failed"))
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()
        mock_conn.cursor = AsyncMock(return_value=mock_cursor)
        mock_manager.connect = AsyncMock(return_value=mock_conn)

        txn = Transaction("test.db", manager=mock_manager)
        await txn.__aenter__()

        with pytest.raises(Exception) as exc_info:
            await txn.__aexit__(None, None, None)

        assert "Commit failed" in str(exc_info.value)
        # Cursor should still be closed
        mock_cursor.close.assert_awaited_once()
        assert txn._cursor is None
