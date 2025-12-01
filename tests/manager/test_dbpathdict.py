# tests/manager/test_dbpathdict.py
import pytest
from unittest.mock import MagicMock
from ...manager.dbpathdict import PathConnection, DbPathDict


class MockConnection:
    """Mock for aiosqlite.Connection to avoid real database connections."""
    pass


@pytest.fixture
def mock_conn():
    """Create a mock connection."""
    conn = MagicMock(spec_set=['__class__'])
    conn.__class__ = type('Connection', (), {})
    return conn


class TestPathConnection:
    """Tests for PathConnection class."""

    def test_init_with_path_and_conn(self, mock_conn):
        """Test PathConnection initialization with path and write_conn."""
        pc = PathConnection("test.db", mock_conn)
        assert pc.path == "test.db"
        assert pc.write_conn is mock_conn
        assert pc.conn is mock_conn  # Backwards compatibility
        assert pc.read_conn is None
        assert pc.alias is None

    def test_init_with_alias(self, mock_conn):
        """Test PathConnection initialization with alias."""
        pc = PathConnection("test.db", mock_conn, alias="mydb")
        assert pc.path == "test.db"
        assert pc.alias == "mydb"
        assert pc.write_conn is mock_conn
        assert pc.conn is mock_conn

    def test_init_with_read_conn(self, mock_conn):
        """Test PathConnection initialization with separate read connection."""
        read_conn = MagicMock(spec_set=['__class__'])
        pc = PathConnection("test.db", mock_conn, read_conn=read_conn, alias="mydb")
        assert pc.write_conn is mock_conn
        assert pc.read_conn is read_conn
        assert pc.conn is mock_conn  # conn is alias for write_conn

    def test_conn_property_is_alias_for_write_conn(self, mock_conn):
        """Test that conn property is an alias for write_conn."""
        pc = PathConnection("test.db", mock_conn)
        assert pc.conn is pc.write_conn
        
        # Test setter
        new_conn = MagicMock(spec_set=['__class__'])
        pc.conn = new_conn
        assert pc.write_conn is new_conn
        assert pc.conn is new_conn

    def test_get_conn_write_mode(self, mock_conn):
        """Test get_conn returns write_conn for write mode."""
        pc = PathConnection("test.db", mock_conn)
        assert pc.get_conn("write") is mock_conn

    def test_get_conn_read_mode_with_read_conn(self, mock_conn):
        """Test get_conn returns read_conn for read mode when available."""
        read_conn = MagicMock(spec_set=['__class__'])
        pc = PathConnection("test.db", mock_conn, read_conn=read_conn)
        assert pc.get_conn("read") is read_conn

    def test_get_conn_read_mode_fallback_to_write(self, mock_conn):
        """Test get_conn falls back to write_conn when read_conn is None."""
        pc = PathConnection("test.db", mock_conn)
        assert pc.get_conn("read") is mock_conn

    def test_get_conn_default_mode_is_write(self, mock_conn):
        """Test get_conn defaults to write mode."""
        pc = PathConnection("test.db", mock_conn)
        assert pc.get_conn() is mock_conn

    def test_repr(self, mock_conn):
        """Test PathConnection string representation."""
        pc = PathConnection("test.db", mock_conn, alias="mydb")
        repr_str = repr(pc)
        assert "test.db" in repr_str
        assert "mydb" in repr_str
        assert "PathConnection" in repr_str
        assert "write_conn" in repr_str

    def test_eq_same_path(self, mock_conn):
        """Test equality comparison based on path."""
        pc1 = PathConnection("test.db", mock_conn)
        pc2 = PathConnection("test.db", mock_conn)
        assert pc1 == pc2

    def test_eq_different_path(self, mock_conn):
        """Test inequality for different paths."""
        pc1 = PathConnection("test1.db", mock_conn)
        pc2 = PathConnection("test2.db", mock_conn)
        assert pc1 != pc2

    def test_eq_with_non_path_connection(self, mock_conn):
        """Test equality with non-PathConnection returns False."""
        pc = PathConnection("test.db", mock_conn)
        assert pc != "test.db"
        assert pc != {"path": "test.db"}

    def test_hash(self, mock_conn):
        """Test hash is based on path."""
        pc1 = PathConnection("test.db", mock_conn)
        pc2 = PathConnection("test.db", mock_conn)
        assert hash(pc1) == hash(pc2)

    def test_bool_true(self, mock_conn):
        """Test bool is True for non-empty path."""
        pc = PathConnection("test.db", mock_conn)
        assert bool(pc) is True

    def test_bool_false(self, mock_conn):
        """Test bool is False for empty path."""
        pc = PathConnection("", mock_conn)
        assert bool(pc) is False


class TestDbPathDict:
    """Tests for DbPathDict class."""

    @pytest.fixture
    def aio_conn(self):
        """Create a mock AioConnection."""
        from aiosqlite import Connection as AioConnection
        return MagicMock(spec=AioConnection)

    def test_init(self):
        """Test DbPathDict initialization."""
        db_dict = DbPathDict()
        assert db_dict.path_connections == set()

    def test_get_connection_existing(self, aio_conn):
        """Test get_connection for existing path."""
        db_dict = DbPathDict()
        db_dict["test.db"] = aio_conn
        assert db_dict.get_connection("test.db") is aio_conn

    def test_get_connection_nonexistent(self):
        """Test get_connection returns None for nonexistent path."""
        db_dict = DbPathDict()
        assert db_dict.get_connection("nonexistent.db") is None

    def test_get_connection_with_mode(self, aio_conn):
        """Test get_connection with read/write mode."""
        from aiosqlite import Connection as AioConnection
        db_dict = DbPathDict()
        read_conn = MagicMock(spec=AioConnection)
        pc = PathConnection("test.db", aio_conn, read_conn=read_conn)
        db_dict["test.db"] = pc
        
        assert db_dict.get_connection("test.db", "write") is aio_conn
        assert db_dict.get_connection("test.db", "read") is read_conn

    def test_get_path_connection(self, aio_conn):
        """Test get_path_connection returns PathConnection object."""
        db_dict = DbPathDict()
        db_dict["test.db"] = aio_conn
        pc = db_dict.get_path_connection("test.db")
        assert isinstance(pc, PathConnection)
        assert pc.write_conn is aio_conn

    def test_getitem(self, aio_conn):
        """Test __getitem__ returns PathConnection."""
        db_dict = DbPathDict()
        db_dict["test.db"] = aio_conn
        pc = db_dict["test.db"]
        assert isinstance(pc, PathConnection)
        assert pc.write_conn is aio_conn

    def test_getitem_nonexistent_raises_keyerror(self):
        """Test __getitem__ raises KeyError for nonexistent key."""
        db_dict = DbPathDict()
        with pytest.raises(KeyError):
            _ = db_dict["nonexistent.db"]

    def test_contains_with_string(self, aio_conn):
        """Test __contains__ with string key."""
        db_dict = DbPathDict()
        db_dict["test.db"] = aio_conn
        assert "test.db" in db_dict
        assert "other.db" not in db_dict

    def test_contains_with_none(self):
        """Test __contains__ with None returns False."""
        db_dict = DbPathDict()
        assert (None in db_dict) is False

    def test_contains_with_path_connection(self, aio_conn):
        """Test __contains__ with PathConnection."""
        db_dict = DbPathDict()
        db_dict["test.db"] = aio_conn
        pc = PathConnection("test.db", aio_conn)
        assert pc in db_dict

    def test_get_with_default(self, aio_conn):
        """Test get returns default for nonexistent key."""
        db_dict = DbPathDict()
        db_dict["test.db"] = aio_conn
        pc = db_dict.get("test.db")
        assert pc is not None
        assert pc.write_conn is aio_conn
        assert db_dict.get("nonexistent.db", "default") == "default"
        assert db_dict.get("nonexistent.db") is None

    def test_setitem_string_key(self, aio_conn):
        """Test __setitem__ with string key."""
        db_dict = DbPathDict()
        db_dict["test.db"] = aio_conn
        assert "test.db" in db_dict
        assert len(db_dict.path_connections) == 1

    def test_setitem_path_connection_key(self, aio_conn):
        """Test __setitem__ with PathConnection key."""
        db_dict = DbPathDict()
        pc = PathConnection("test.db", aio_conn, alias="mydb")
        db_dict[pc] = pc
        assert "test.db" in db_dict
        assert "mydb" in db_dict

    def test_setitem_with_path_connection_value(self, aio_conn):
        """Test __setitem__ with PathConnection value."""
        from aiosqlite import Connection as AioConnection
        db_dict = DbPathDict()
        read_conn = MagicMock(spec=AioConnection)
        pc = PathConnection("test.db", aio_conn, read_conn=read_conn, alias="mydb")
        db_dict["test.db"] = pc
        
        stored_pc = db_dict["test.db"]
        assert stored_pc.write_conn is aio_conn
        assert stored_pc.read_conn is read_conn
        assert stored_pc.alias == "mydb"

    def test_setitem_updates_existing(self, aio_conn):
        """Test __setitem__ updates existing connection."""
        db_dict = DbPathDict()
        from aiosqlite import Connection as AioConnection
        conn1 = MagicMock(spec=AioConnection)
        conn2 = MagicMock(spec=AioConnection)
        db_dict["test.db"] = conn1
        db_dict["test.db"] = conn2
        pc = db_dict["test.db"]
        assert pc.write_conn is conn2
        assert len(db_dict.path_connections) == 1

    def test_setitem_empty_key_raises(self, aio_conn):
        """Test __setitem__ with empty key raises ValueError."""
        db_dict = DbPathDict()
        with pytest.raises(ValueError):
            db_dict[""] = aio_conn

    def test_setitem_invalid_conn_raises(self):
        """Test __setitem__ with invalid connection raises ValueError."""
        db_dict = DbPathDict()
        with pytest.raises(ValueError):
            db_dict["test.db"] = "not_a_connection"

    def test_delitem(self, aio_conn):
        """Test __delitem__ removes connection."""
        db_dict = DbPathDict()
        db_dict["test.db"] = aio_conn
        del db_dict["test.db"]
        assert "test.db" not in db_dict
        assert len(db_dict.path_connections) == 0

    def test_delitem_nonexistent_raises_keyerror(self):
        """Test __delitem__ raises KeyError for nonexistent key."""
        db_dict = DbPathDict()
        with pytest.raises(KeyError):
            del db_dict["nonexistent.db"]

    def test_setalias(self, aio_conn):
        """Test setalias adds alias to existing path."""
        db_dict = DbPathDict()
        db_dict["test.db"] = aio_conn
        db_dict.setalias("test.db", "mydb")
        pc_mydb = db_dict["mydb"]
        pc_test = db_dict["test.db"]
        assert pc_mydb is pc_test
        assert pc_mydb.write_conn is aio_conn

    def test_setalias_update_existing(self, aio_conn):
        """Test setalias updates existing alias."""
        db_dict = DbPathDict()
        db_dict["test.db"] = aio_conn
        db_dict.setalias("test.db", "alias1")
        db_dict.setalias("test.db", "alias2")
        assert "alias1" not in db_dict
        pc = db_dict["alias2"]
        assert pc.write_conn is aio_conn

    def test_setalias_remove_alias(self, aio_conn):
        """Test setalias with None removes alias."""
        db_dict = DbPathDict()
        db_dict["test.db"] = aio_conn
        db_dict.setalias("test.db", "mydb")
        db_dict.setalias("test.db", None)
        assert "mydb" not in db_dict

    def test_setalias_nonexistent_key_raises(self):
        """Test setalias raises KeyError for nonexistent key."""
        db_dict = DbPathDict()
        with pytest.raises(KeyError):
            db_dict.setalias("nonexistent.db", "mydb")

    def test_setalias_existing_alias_raises(self, aio_conn):
        """Test setalias raises KeyError when alias already exists."""
        from aiosqlite import Connection as AioConnection
        db_dict = DbPathDict()
        conn1 = MagicMock(spec=AioConnection)
        conn2 = MagicMock(spec=AioConnection)
        db_dict["test1.db"] = conn1
        db_dict["test2.db"] = conn2
        db_dict.setalias("test1.db", "mydb")
        with pytest.raises(KeyError):
            db_dict.setalias("test2.db", "mydb")

    def test_setpath(self, aio_conn):
        """Test setpath changes path for existing connection."""
        db_dict = DbPathDict()
        db_dict["old.db"] = aio_conn
        db_dict.setpath("old.db", "new.db")
        assert "new.db" in db_dict
        assert "old.db" not in db_dict

    def test_setpath_nonexistent_raises(self):
        """Test setpath raises KeyError for nonexistent key."""
        db_dict = DbPathDict()
        with pytest.raises(KeyError):
            db_dict.setpath("nonexistent.db", "new.db")

    def test_setpath_existing_path_raises(self, aio_conn):
        """Test setpath raises KeyError when new path already exists."""
        from aiosqlite import Connection as AioConnection
        db_dict = DbPathDict()
        conn1 = MagicMock(spec=AioConnection)
        conn2 = MagicMock(spec=AioConnection)
        db_dict["test1.db"] = conn1
        db_dict["test2.db"] = conn2
        with pytest.raises(KeyError):
            db_dict.setpath("test1.db", "test2.db")

    def test_paths_property(self, aio_conn):
        """Test paths property returns list of all paths."""
        from aiosqlite import Connection as AioConnection
        db_dict = DbPathDict()
        conn1 = MagicMock(spec=AioConnection)
        conn2 = MagicMock(spec=AioConnection)
        db_dict["test1.db"] = conn1
        db_dict["test2.db"] = conn2
        paths = db_dict.paths
        assert len(paths) == 2
        assert "test1.db" in paths
        assert "test2.db" in paths

    def test_check_key_empty_string_raises(self):
        """Test _check_key raises ValueError for empty string."""
        with pytest.raises(ValueError):
            DbPathDict._check_key("")

    def test_check_key_invalid_type_raises(self):
        """Test _check_key raises ValueError for invalid type."""
        with pytest.raises(ValueError):
            DbPathDict._check_key(123)

    def test_check_key_empty_path_connection_raises(self, aio_conn):
        """Test _check_key raises ValueError for PathConnection with empty path."""
        pc = PathConnection("", aio_conn)
        with pytest.raises(ValueError):
            DbPathDict._check_key(pc)
