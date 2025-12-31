# tests/manager/test_manager_base.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from ...manager.manager_base import ManagerBase
from ...manager.exceptions import ConnectionError
from ...manager.dbpathdict import DbPathDict


class TestManagerBase:
    """Tests for ManagerBase class."""

    def test_init_default(self):
        """Test ManagerBase initialization with defaults."""
        manager = ManagerBase()
        assert manager.autocommit is False
        assert manager.omni_log is False
        assert manager.log_results is True
        assert isinstance(manager.db_dict, DbPathDict)
        assert manager.history_length == 10
        assert manager.history_tolerance == 5

    def test_init_with_custom_values(self):
        """Test ManagerBase initialization with custom values."""
        manager = ManagerBase(
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

    def test_get_lock_creates_new_lock(self):
        """Test _get_lock creates new lock for new path."""
        manager = ManagerBase()
        lock1 = manager._get_lock("test1.db")
        lock2 = manager._get_lock("test2.db")
        assert isinstance(lock1, asyncio.Lock)
        assert isinstance(lock2, asyncio.Lock)
        assert lock1 is not lock2

    def test_get_lock_returns_same_lock(self):
        """Test _get_lock returns same lock for same path."""
        manager = ManagerBase()
        lock1 = manager._get_lock("test.db")
        lock2 = manager._get_lock("test.db")
        assert lock1 is lock2

    def test_get_connection_returns_none_for_nonexistent(self):
        """Test get_connection returns None for nonexistent path."""
        manager = ManagerBase()
        assert manager.get_connection("nonexistent.db") is None

    def test_databases_property(self):
        """Test databases property returns list of paths."""
        manager = ManagerBase()
        assert manager.databases == []

    def test_history_length_property(self):
        """Test history_length property getter and setter."""
        manager = ManagerBase(history_length=10)
        assert manager.history_length == 10
        manager.history_length = 20
        assert manager.history_length == 20

    def test_history_tolerance_property(self):
        """Test history_tolerance property getter and setter."""
        manager = ManagerBase(history_tolerance=5)
        assert manager.history_tolerance == 5
        manager.history_tolerance = 10
        assert manager.history_tolerance == 10

    def test_should_log_true_when_log_param_true(self):
        """Test _should_log returns True when log param is True."""
        manager = ManagerBase(omni_log=False)
        assert manager._should_log(True) is True

    def test_should_log_true_when_omni_log_enabled(self):
        """Test _should_log returns True when omni_log is enabled."""
        manager = ManagerBase(omni_log=True)
        assert manager._should_log(False) is True

    def test_should_log_false_when_override_omnilog(self):
        """Test _should_log returns False when override_omnilog is True."""
        manager = ManagerBase(omni_log=True)
        assert manager._should_log(False, override_omnilog=True) is False

    def test_should_commit_true_when_commit_param_true(self):
        """Test _should_commit returns True when commit param is True."""
        manager = ManagerBase(autocommit=False)
        assert manager._should_commit(True) is True

    def test_should_commit_true_when_autocommit_enabled(self):
        """Test _should_commit returns True when autocommit is enabled."""
        manager = ManagerBase(autocommit=True)
        assert manager._should_commit(False) is True

    def test_should_commit_false_when_override_autocommit(self):
        """Test _should_commit returns False when override_autocommit is True."""
        manager = ManagerBase(autocommit=True)
        assert manager._should_commit(False, override_autocommit=True) is False

    def test_call_logger_calls_method(self):
        """Test _call_logger calls the correct logger method."""
        mock_logger = MagicMock()
        manager = ManagerBase(logger=mock_logger)
        manager._call_logger("info", "test message")
        mock_logger.info.assert_called_once_with("test message")

    def test_call_logger_handles_missing_method(self):
        """Test _call_logger handles non-existent method gracefully."""
        mock_logger = MagicMock(spec=[])
        manager = ManagerBase(logger=mock_logger)
        manager._call_logger("nonexistent", "test")  # Should not raise

    @pytest.mark.asyncio
    async def test_connect_creates_new_connection(self, tmp_path):
        """Test connect creates new connection."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        conn = await manager.connect(db_path)
        assert conn is not None
        assert db_path in manager.db_dict
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_connect_returns_existing_connection(self, tmp_path):
        """Test connect returns existing connection for same path."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        conn1 = await manager.connect(db_path)
        conn2 = await manager.connect(db_path)
        assert conn1 is conn2
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_connect_with_alias(self, tmp_path):
        """Test connect with alias."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        conn = await manager.connect(db_path, alias="mydb")
        pc = manager.db_dict["mydb"]
        assert pc.write_conn is conn
        assert manager.get_connection("mydb") is conn
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_connect_raises_connection_error_on_failure(self):
        """Test connect raises ConnectionError on failure."""
        manager = ManagerBase()
        
        with pytest.raises(ConnectionError):
            await manager.connect("/nonexistent/path/test.db")

    @pytest.mark.asyncio
    async def test_close_removes_connection(self, tmp_path):
        """Test close removes connection."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        assert db_path in manager.db_dict
        
        await manager.close(db_path)
        assert db_path not in manager.db_dict

    @pytest.mark.asyncio
    async def test_disconnect_alias(self, tmp_path):
        """Test disconnect is alias for close."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        await manager.disconnect(db_path)
        assert db_path not in manager.db_dict

    @pytest.mark.asyncio
    async def test_close_removes_lock(self, tmp_path):
        """Test close removes the lock for the path."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        manager._get_lock(db_path)  # Ensure lock exists
        
        await manager.close(db_path)
        assert db_path not in manager._locks

    @pytest.mark.asyncio
    async def test_execute_query(self, tmp_path):
        """Test execute runs query and returns results."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        result = await manager.execute(db_path, "SELECT 1")
        assert result == [(1,)]
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_execute_with_params(self, tmp_path):
        """Test execute with query parameters."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER, name TEXT)")
        await manager.execute(
            db_path, 
            "INSERT INTO test VALUES (?, ?)", 
            params=(1, "Alice"),
            commit=True
        )
        result = await manager.execute(db_path, "SELECT * FROM test")
        assert result == [(1, "Alice")]
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_execute_with_commit(self, tmp_path):
        """Test execute with commit=True commits changes."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)")
        await manager.execute(
            db_path, 
            "INSERT INTO test VALUES (1)",
            commit=True
        )
        
        # Reconnect and verify data persisted
        await manager.close(db_path)
        await manager.connect(db_path)
        result = await manager.execute(db_path, "SELECT * FROM test")
        assert result == [(1,)]
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_commit(self, tmp_path):
        """Test commit method."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)")
        await manager.execute(db_path, "INSERT INTO test VALUES (1)")
        await manager.commit(db_path)
        
        # Reconnect and verify data persisted
        await manager.close(db_path)
        await manager.connect(db_path)
        result = await manager.execute(db_path, "SELECT * FROM test")
        assert result == [(1,)]
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_commit_returns_early_if_no_connection(self):
        """Test commit returns early if no connection exists."""
        manager = ManagerBase()
        await manager.commit("nonexistent.db")  # Should not raise

    @pytest.mark.asyncio
    async def test_rollback(self, tmp_path):
        """Test rollback method."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES (1)")
        await manager.rollback(db_path)
        
        result = await manager.execute(db_path, "SELECT * FROM test")
        assert result == []
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_rollback_returns_early_if_no_connection(self):
        """Test rollback returns early if no connection exists."""
        manager = ManagerBase()
        await manager.rollback("nonexistent.db")  # Should not raise

    @pytest.mark.asyncio
    async def test_savepoint(self, tmp_path):
        """Test savepoint creation."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        await manager.savepoint(db_path, "sp1")
        await manager.execute(db_path, "INSERT INTO test VALUES (1)")
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_savepoint_returns_early_if_no_connection(self):
        """Test savepoint returns early if no connection exists."""
        manager = ManagerBase()
        await manager.savepoint("nonexistent.db", "sp1")  # Should not raise

    @pytest.mark.asyncio
    async def test_rollback_to(self, tmp_path):
        """Test rollback_to savepoint."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        await manager.savepoint(db_path, "sp1")
        await manager.execute(db_path, "INSERT INTO test VALUES (1)")
        await manager.rollback_to(db_path, "sp1")
        
        result = await manager.execute(db_path, "SELECT * FROM test")
        assert result == []
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_rollback_to_returns_early_if_no_connection(self):
        """Test rollback_to returns early if no connection exists."""
        manager = ManagerBase()
        await manager.rollback_to("nonexistent.db", "sp1")  # Should not raise

    @pytest.mark.asyncio
    async def test_release_savepoint(self, tmp_path):
        """Test release_savepoint."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (id INTEGER)", commit=True)
        await manager.savepoint(db_path, "sp1")
        await manager.release_savepoint(db_path, "sp1")
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_release_savepoint_returns_early_if_no_connection(self):
        """Test release_savepoint returns early if no connection exists."""
        manager = ManagerBase()
        await manager.release_savepoint("nonexistent.db", "sp1")  # Should not raise

    @pytest.mark.asyncio
    async def test_flush_history_to_file(self):
        """Test flush_history_to_file delegates to history manager."""
        manager = ManagerBase()
        with patch.object(manager._history_manager, 'flush_to_file', new_callable=AsyncMock) as mock_flush:
            await manager.flush_history_to_file()
            mock_flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_with_read_connection(self, tmp_path):
        """Test connect with create_read_connection=True creates separate read connection."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        write_conn = await manager.connect(db_path, create_read_connection=True)
        pc = manager.get_path_connection(db_path)
        
        assert pc is not None
        assert pc.write_conn is write_conn
        assert pc.read_conn is not None
        assert pc.read_conn is not pc.write_conn
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_get_connection_with_mode(self, tmp_path):
        """Test get_connection with mode parameter."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        write_conn = await manager.connect(db_path, create_read_connection=True)
        
        # Test write mode
        assert manager.get_connection(db_path, mode="write") is write_conn
        
        # Test read mode - should return read connection
        read_conn = manager.get_connection(db_path, mode="read")
        assert read_conn is not None
        assert read_conn is not write_conn
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_get_connection_read_fallback_to_write(self, tmp_path):
        """Test get_connection read mode falls back to write when no read connection."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        # Connect without read connection
        write_conn = await manager.connect(db_path, create_read_connection=False)
        
        # Read mode should fall back to write connection
        read_conn = manager.get_connection(db_path, mode="read")
        assert read_conn is write_conn
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_get_connection_default_mode_is_write(self, tmp_path):
        """Test get_connection defaults to write mode."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        write_conn = await manager.connect(db_path, create_read_connection=True)
        
        # Default mode should be write
        default_conn = manager.get_connection(db_path)
        assert default_conn is write_conn
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_get_path_connection(self, tmp_path):
        """Test get_path_connection returns PathConnection object."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path, alias="mydb")
        
        # Access via path
        pc_by_path = manager.get_path_connection(db_path)
        assert pc_by_path is not None
        assert pc_by_path.path == db_path
        
        # Access via alias
        pc_by_alias = manager.get_path_connection("mydb")
        assert pc_by_alias is pc_by_path
        
        # Non-existent returns None
        assert manager.get_path_connection("nonexistent.db") is None
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_close_closes_both_connections(self, tmp_path):
        """Test close closes both read and write connections."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path, create_read_connection=True)
        pc = manager.get_path_connection(db_path)
        
        write_conn = pc.write_conn
        read_conn = pc.read_conn
        
        await manager.close(db_path)
        
        # Both connections should be closed
        assert db_path not in manager.db_dict

    @pytest.mark.asyncio
    async def test_connect_creates_read_connection_on_existing(self, tmp_path):
        """Test connect creates read connection for existing connection when requested."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        # First connect without read connection
        await manager.connect(db_path, create_read_connection=False)
        pc = manager.get_path_connection(db_path)
        assert pc.read_conn is None
        
        # Second connect with read connection should create it
        await manager.connect(db_path, create_read_connection=True)
        pc = manager.get_path_connection(db_path)
        assert pc.read_conn is not None
        assert pc.read_conn is not pc.write_conn
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_write_conn_isnot_read_conn(self, tmp_path):
        """Test that write and read connections are different objects."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path, create_read_connection=True)
        pc = manager.get_path_connection(db_path)
        
        assert pc.write_conn is not pc.read_conn
        
        await manager.close(db_path)

    def test_validate_savepoint_name_valid(self):
        """Test _validate_savepoint_name accepts valid names."""
        manager = ManagerBase()
        # These should not raise
        manager._validate_savepoint_name("sp1")
        manager._validate_savepoint_name("my_savepoint")
        manager._validate_savepoint_name("SavePoint123")
        manager._validate_savepoint_name("_private")
        manager._validate_savepoint_name("a")

    def test_validate_savepoint_name_invalid_raises(self):
        """Test _validate_savepoint_name raises for invalid names."""
        manager = ManagerBase()
        
        invalid_names = [
            "1starts_with_number",
            "has spaces",
            "has-dashes",
            "has.dots",
            "DROP TABLE; --",
            "",
            "has'quote",
            "has\"doublequote",
            "has;semicolon",
        ]
        
        for name in invalid_names:
            with pytest.raises(ValueError, match="Invalid savepoint name"):
                manager._validate_savepoint_name(name)

    @pytest.mark.asyncio
    async def test_savepoint_validates_name(self, tmp_path):
        """Test savepoint method validates name before executing."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        
        # Valid name should work
        await manager.savepoint(db_path, "valid_savepoint")
        
        # Invalid name should raise ValueError
        with pytest.raises(ValueError, match="Invalid savepoint name"):
            await manager.savepoint(db_path, "DROP TABLE; --")
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_rollback_to_validates_name(self, tmp_path):
        """Test rollback_to method validates name before executing."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        
        # Invalid name should raise ValueError before even checking connection
        with pytest.raises(ValueError, match="Invalid savepoint name"):
            await manager.rollback_to(db_path, "'; DROP TABLE users; --")
        
        await manager.close(db_path)

    @pytest.mark.asyncio
    async def test_release_savepoint_validates_name(self, tmp_path):
        """Test release_savepoint method validates name before executing."""
        db_path = str(tmp_path / "test.db")
        manager = ManagerBase()
        
        await manager.connect(db_path)
        
        # Invalid name should raise ValueError before even checking connection
        with pytest.raises(ValueError, match="Invalid savepoint name"):
            await manager.release_savepoint(db_path, "invalid name")
        
        await manager.close(db_path)
