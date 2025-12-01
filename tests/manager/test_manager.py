# tests/manager/test_manager.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from ...manager.manager import Manager
from ...manager.transaction import Transaction


class TestManager:
    """Tests for Manager class."""

    def test_init_default(self):
        """Test Manager initialization with defaults."""
        manager = Manager()
        assert manager.autocommit is False
        assert manager.omni_log is False
        assert manager.log_results is True
        assert manager.history_length == 10
        assert manager.history_tolerance == 5

    def test_init_with_custom_values(self):
        """Test Manager initialization with custom values."""
        manager = Manager(
            autocommit=True,
            omni_log=True,
            history_length=20,
            log_results=False,
            history_tolerance=10,
        )
        assert manager.autocommit is True
        assert manager.omni_log is True
        assert manager.log_results is False
        assert manager.history_length == 20
        assert manager.history_tolerance == 10

    @pytest.mark.asyncio
    async def test_queue_context_manager(self, tmp_path):
        """Test queue context manager serializes access."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        async with manager.queue(db_path):
            # Should acquire lock
            lock = manager._get_lock(db_path)
            assert lock.locked()
        
        # Lock should be released after context
        assert not lock.locked()

    @pytest.mark.asyncio
    async def test_safe_transaction(self, tmp_path):
        """Test safe_transaction context manager."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        async with manager.safe_transaction(db_path) as txn:
            assert isinstance(txn, Transaction)
            await txn.execute("CREATE TABLE test (id INTEGER)")
            await txn.execute("INSERT INTO test VALUES (1)")
        
        # Verify data was committed
        result = await manager.execute(db_path, "SELECT * FROM test")
        assert result == [(1,)]
        
        await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_disconnect_all(self, tmp_path):
        """Test disconnect_all closes all connections."""
        manager = Manager()
        db1 = str(tmp_path / "test1.db")
        db2 = str(tmp_path / "test2.db")
        
        await manager.connect(db1)
        await manager.connect(db2)
        
        assert len(manager.databases) == 2
        
        await manager.disconnect_all()
        
        assert len(manager.databases) == 0

    @pytest.mark.asyncio
    async def test_shutdown(self, tmp_path):
        """Test shutdown closes all connections and flushes history."""
        manager = Manager()
        db_path = str(tmp_path / "test.db")
        
        await manager.connect(db_path)
        
        with patch.object(manager, 'flush_history_to_file', new_callable=AsyncMock) as mock_flush:
            await manager.shutdown()
            mock_flush.assert_awaited_once()
        
        assert len(manager.databases) == 0

    def test_transaction_returns_transaction_instance(self):
        """Test Transaction method returns Transaction instance."""
        manager = Manager()
        txn = manager.Transaction("test.db")
        assert isinstance(txn, Transaction)
        assert txn.database_path == "test.db"
        assert txn.manager is manager

    def test_transaction_with_custom_params(self):
        """Test Transaction method with custom parameters."""
        mock_logger = MagicMock()
        manager = Manager()
        txn = manager.Transaction(
            "test.db",
            autocommit=False,
            log_all=True,
            logger=mock_logger,
        )
        assert txn.autocommit is False
        assert txn.logger is mock_logger

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self, tmp_path):
        """Test Transaction as context manager."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        async with manager.Transaction(db_path) as txn:
            await txn.execute("CREATE TABLE test (id INTEGER)")
            await txn.execute("INSERT INTO test VALUES (1)")
        
        # Verify data was committed
        result = await manager.execute(db_path, "SELECT * FROM test")
        assert result == [(1,)]
        
        await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_exception(self, tmp_path):
        """Test Transaction rolls back on exception."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        # Create table first
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        
        with pytest.raises(ValueError):
            async with manager.Transaction(db_path) as txn:
                await txn.execute("INSERT INTO test VALUES (1)")
                raise ValueError("Test error")
        
        # Verify data was rolled back
        result = await manager.execute(db_path, "SELECT * FROM test")
        assert result == []
        
        await manager.disconnect_all()

    def test_with_transaction_decorator(self):
        """Test with_transaction decorator creates decorated function."""
        @Manager.with_transaction("test.db")
        async def my_func(manager):
            pass
        
        assert callable(my_func)

    @pytest.mark.asyncio
    async def test_queue_prevents_concurrent_access(self, tmp_path):
        """Test queue prevents concurrent access to same database."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        order = []
        
        async def task1():
            async with manager.queue(db_path):
                order.append("task1_start")
                await asyncio.sleep(0.1)
                order.append("task1_end")
        
        async def task2():
            await asyncio.sleep(0.01)  # Small delay to ensure task1 starts first
            async with manager.queue(db_path):
                order.append("task2_start")
                order.append("task2_end")
        
        await asyncio.gather(task1(), task2())
        
        # task1 should complete before task2 starts
        assert order == ["task1_start", "task1_end", "task2_start", "task2_end"]

    @pytest.mark.asyncio
    async def test_manager_inherits_from_manager_base(self):
        """Test Manager inherits from ManagerBase."""
        from ...manager.manager_base import ManagerBase
        manager = Manager()
        assert isinstance(manager, ManagerBase)

    @pytest.mark.asyncio
    async def test_full_workflow(self, tmp_path):
        """Test full workflow with Manager."""
        db_path = str(tmp_path / "test.db")
        manager = Manager(autocommit=True)
        
        # Connect and create table
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE users (id INTEGER, name TEXT)")
        
        # Use transaction to insert data
        async with manager.Transaction(db_path) as txn:
            await txn.execute("INSERT INTO users VALUES (?, ?)", (1, "Alice"))
            await txn.execute("INSERT INTO users VALUES (?, ?)", (2, "Bob"))
        
        # Query data
        result = await manager.execute(db_path, "SELECT * FROM users ORDER BY id")
        assert result == [(1, "Alice"), (2, "Bob")]
        
        # Shutdown
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_safe_transaction_multiple_queries(self, tmp_path):
        """Test safe_transaction allows multiple queries without locking the database."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        async with manager.safe_transaction(db_path) as txn:
            # Create table and insert multiple rows in one transaction
            await txn.execute("CREATE TABLE test (id INTEGER, value TEXT)")
            await txn.execute("INSERT INTO test VALUES (?, ?)", (1, "first"))
            await txn.execute("INSERT INTO test VALUES (?, ?)", (2, "second"))
            await txn.execute("INSERT INTO test VALUES (?, ?)", (3, "third"))
            
            # Query within the same transaction
            result = await txn.execute("SELECT * FROM test ORDER BY id")
            assert result == [(1, "first"), (2, "second"), (3, "third")]
        
        # Verify data was committed
        result = await manager.execute(db_path, "SELECT COUNT(*) FROM test")
        assert result == [(3,)]
        
        await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_transaction_multiple_queries(self, tmp_path):
        """Test Transaction allows multiple queries without locking the database."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        async with manager.Transaction(db_path) as txn:
            await txn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
            await txn.execute("INSERT INTO items (name) VALUES (?)", ("item1",))
            await txn.execute("INSERT INTO items (name) VALUES (?)", ("item2",))
            await txn.execute("INSERT INTO items (name) VALUES (?)", ("item3",))
            
            # Query within the same transaction
            result = await txn.execute("SELECT name FROM items ORDER BY id")
            assert result == [("item1",), ("item2",), ("item3",)]
        
        # Verify data was committed
        result = await manager.execute(db_path, "SELECT COUNT(*) FROM items")
        assert result == [(3,)]
        
        await manager.disconnect_all()

    @pytest.mark.asyncio
    async def test_execute_with_cursor_parameter(self, tmp_path):
        """Test Manager.execute can accept a cursor parameter."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        conn = await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        
        # Get a cursor and use it for multiple queries
        cursor = await conn.cursor()
        try:
            await manager.execute(db_path, "INSERT INTO test VALUES (1)", cursor=cursor, commit=True)
            await manager.execute(db_path, "INSERT INTO test VALUES (2)", cursor=cursor, commit=True)
            result = await manager.execute(db_path, "SELECT * FROM test ORDER BY id", cursor=cursor)
            assert result == [(1,), (2,)]
        finally:
            await cursor.close()
        
        await manager.disconnect_all()
