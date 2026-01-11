# tests/manager/test_type_conversion.py
"""Integration tests for type conversion with Manager."""
import pytest
from enum import IntEnum
from ...manager.manager import Manager


class ListType(IntEnum):
    """Example IntEnum for testing."""
    TYPE_A = 0
    TYPE_B = 1


class TestManagerTypeConversion:
    """Tests for Manager with type conversion."""
    
    @pytest.mark.asyncio
    async def test_text_column_with_integer_values(self, tmp_path):
        """Test that TEXT columns containing integer values are converted to int."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        # Create table with TEXT column
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (list_type TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('0')", commit=True)
        
        # Fetch the value
        result = await manager.execute(db_path, "SELECT list_type FROM test", return_type="fetchone")
        
        # Value should be converted to int
        assert result[0][0] == 0
        assert isinstance(result[0][0], int)
        
        # Should work with IntEnum
        list_type = ListType(result[0][0])
        assert list_type == ListType.TYPE_A
        
        await manager.disconnect_all()
        
    @pytest.mark.asyncio
    async def test_integer_column_returns_int(self, tmp_path):
        """Test that INTEGER columns return int (baseline test)."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        # Create table with INTEGER column
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (list_type INTEGER)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES (0)", commit=True)
        
        # Fetch the value
        result = await manager.execute(db_path, "SELECT list_type FROM test", return_type="fetchone")
        
        # Value should already be int
        assert result[0][0] == 0
        assert isinstance(result[0][0], int)
        
        # Should work with IntEnum
        list_type = ListType(result[0][0])
        assert list_type == ListType.TYPE_A
        
        await manager.disconnect_all()
        
    @pytest.mark.asyncio
    async def test_cast_to_text_is_converted(self, tmp_path):
        """Test that CAST to TEXT operations are converted back to int."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (value INTEGER)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES (1)", commit=True)
        
        # Query with CAST to TEXT
        result = await manager.execute(db_path, "SELECT CAST(value AS TEXT) FROM test", return_type="fetchone")
        
        # Should be converted back to int
        assert result[0][0] == 1
        assert isinstance(result[0][0], int)
        
        # Should work with IntEnum
        list_type = ListType(result[0][0])
        assert list_type == ListType.TYPE_B
        
        await manager.disconnect_all()
        
    @pytest.mark.asyncio
    async def test_mixed_types_in_row(self, tmp_path):
        """Test that mixed types are handled correctly."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(
            db_path, 
            "CREATE TABLE test (id TEXT, name TEXT, count TEXT, active INTEGER)",
            commit=True
        )
        await manager.execute(
            db_path,
            "INSERT INTO test VALUES ('123', 'Product', '5', 1)",
            commit=True
        )
        
        result = await manager.execute(db_path, "SELECT * FROM test", return_type="fetchone")
        row = result[0]
        
        # id should be converted to int
        assert row[0] == 123
        assert isinstance(row[0], int)
        
        # name should remain string
        assert row[1] == 'Product'
        assert isinstance(row[1], str)
        
        # count should be converted to int
        assert row[2] == 5
        assert isinstance(row[2], int)
        
        # active should already be int
        assert row[3] == 1
        assert isinstance(row[3], int)
        
        await manager.disconnect_all()
        
    @pytest.mark.asyncio
    async def test_non_numeric_strings_preserved(self, tmp_path):
        """Test that non-numeric strings are not converted."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (value TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('hello')", commit=True)
        
        result = await manager.execute(db_path, "SELECT value FROM test", return_type="fetchone")
        
        # Should remain string
        assert result[0][0] == 'hello'
        assert isinstance(result[0][0], str)
        
        await manager.disconnect_all()
        
    @pytest.mark.asyncio
    async def test_float_strings_preserved(self, tmp_path):
        """Test that float strings are not converted to int."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (value TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('123.45')", commit=True)
        
        result = await manager.execute(db_path, "SELECT value FROM test", return_type="fetchone")
        
        # Should remain string (we don't convert floats)
        assert result[0][0] == '123.45'
        assert isinstance(result[0][0], str)
        
        await manager.disconnect_all()
        
    @pytest.mark.asyncio
    async def test_null_values_handled(self, tmp_path):
        """Test that NULL values are handled correctly."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (value TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES (NULL)", commit=True)
        
        result = await manager.execute(db_path, "SELECT value FROM test", return_type="fetchone")
        
        # Should be None
        assert result[0][0] is None
        
        await manager.disconnect_all()
        
    @pytest.mark.asyncio
    async def test_negative_integers_converted(self, tmp_path):
        """Test that negative integer strings are converted."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (value TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('-42')", commit=True)
        
        result = await manager.execute(db_path, "SELECT value FROM test", return_type="fetchone")
        
        # Should be converted to int
        assert result[0][0] == -42
        assert isinstance(result[0][0], int)
        
        await manager.disconnect_all()
        
    @pytest.mark.asyncio
    async def test_read_connection_also_has_row_factory(self, tmp_path):
        """Test that read connections also use the type converting row factory."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        # Connect with separate read connection
        await manager.connect(db_path, create_read_connection=True)
        await manager.execute(db_path, "CREATE TABLE test (value TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('99')", commit=True)
        
        # Use read mode
        result = await manager.execute(db_path, "SELECT value FROM test", mode="read", return_type="fetchone")
        
        # Should be converted to int
        assert result[0][0] == 99
        assert isinstance(result[0][0], int)
        
        await manager.disconnect_all()
