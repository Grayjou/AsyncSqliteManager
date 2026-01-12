# tests/manager/test_custom_type_conversion.py
"""Tests for customizable type conversion at execute level."""
import pytest
from ...manager.manager import Manager


class TestCustomTypeConversion:
    """Tests for custom type conversion with expected_types parameter."""
    
    @pytest.mark.asyncio
    async def test_bool_and_int_conversion(self, tmp_path):
        """Test conversion with (bool, int) types."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (a TEXT, b TEXT, c TEXT, d TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('1', '0', 'blablabla', 'uuu')", commit=True)
        
        # Query with expected_types=(bool, int)
        result = await manager.execute(
            db_path, 
            "SELECT * FROM test",
            return_type="fetchone",
            expected_types=(bool, int)
        )
        
        row = result[0]
        # First column should be bool True
        assert row[0] is True
        assert isinstance(row[0], bool)
        
        # Second column should be int 0
        assert row[1] == 0
        assert isinstance(row[1], int)
        
        # Third and fourth columns use default conversion (remain strings)
        assert row[2] == 'blablabla'
        assert isinstance(row[2], str)
        assert row[3] == 'uuu'
        assert isinstance(row[3], str)
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_none_skips_conversion(self, tmp_path):
        """Test that None in expected_types skips conversion."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (a TEXT, b TEXT, c TEXT, d TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('1', '0', 'blablabla', 'uuu')", commit=True)
        
        # Query with expected_types=(None, int) - skip first, convert second
        result = await manager.execute(
            db_path, 
            "SELECT * FROM test",
            return_type="fetchone",
            expected_types=(None, int)
        )
        
        row = result[0]
        # First column skipped - remains as string '1'
        assert row[0] == '1'
        assert isinstance(row[0], str)
        
        # Second column converted to int 0
        assert row[1] == 0
        assert isinstance(row[1], int)
        
        # Third and fourth columns use default conversion
        assert row[2] == 'blablabla'
        assert row[3] == 'uuu'
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_no_conversion_without_expected_types(self, tmp_path):
        """Test that default conversion happens when expected_types is not provided."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (a TEXT, b TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('1', 'hello')", commit=True)
        
        # Query without expected_types - uses default automatic conversion
        result = await manager.execute(
            db_path, 
            "SELECT * FROM test",
            return_type="fetchone"
        )
        
        row = result[0]
        # First column automatically converted to int by default
        assert row[0] == 1
        assert isinstance(row[0], int)
        
        # Second column remains string
        assert row[1] == 'hello'
        assert isinstance(row[1], str)
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_shorter_tuple_uses_default_for_rest(self, tmp_path):
        """Test that shorter expected_types tuple uses default conversion for remaining columns."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(
            db_path, 
            "CREATE TABLE test (a TEXT, b TEXT, c TEXT, d TEXT)",
            commit=True
        )
        await manager.execute(
            db_path,
            "INSERT INTO test VALUES ('1', '0', '123', 'hello')",
            commit=True
        )
        
        # Only specify types for first two columns
        result = await manager.execute(
            db_path, 
            "SELECT * FROM test",
            return_type="fetchone",
            expected_types=(bool, int)
        )
        
        row = result[0]
        assert row[0] is True  # bool conversion
        assert row[1] == 0     # int conversion
        assert row[2] == 123   # default automatic conversion to int
        assert row[3] == 'hello'  # remains string
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_empty_tuple_uses_default_conversion(self, tmp_path):
        """Test that empty tuple uses default conversion."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (a TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('123')", commit=True)
        
        # Empty tuple should use default conversion
        result = await manager.execute(
            db_path, 
            "SELECT * FROM test",
            return_type="fetchone",
            expected_types=()
        )
        
        row = result[0]
        # Should use default automatic conversion
        assert row[0] == 123
        assert isinstance(row[0], int)
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_transaction_with_custom_types(self, tmp_path):
        """Test that Transaction.execute supports expected_types."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(
            db_path,
            "CREATE TABLE test (status TEXT, count TEXT)",
            commit=True
        )
        
        async with manager.Transaction(db_path, autocommit=True) as txn:
            await txn.execute(
                "INSERT INTO test VALUES ('1', '42')"
            )
            result = await txn.execute(
                "SELECT * FROM test",
                return_type="fetchone",
                expected_types=(bool, int)
            )
        
        row = result[0]
        assert row[0] is True
        assert row[1] == 42
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_bool_conversion_various_values(self, tmp_path):
        """Test bool conversion with various string values."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (val TEXT)", commit=True)
        
        # Test True values
        for val in ['1', 'True', 'true', 'TRUE']:
            await manager.execute(db_path, "DELETE FROM test", commit=True)
            await manager.execute(db_path, f"INSERT INTO test VALUES ('{val}')", commit=True)
            result = await manager.execute(
                db_path,
                "SELECT * FROM test",
                return_type="fetchone",
                expected_types=(bool,)
            )
            assert result[0][0] is True, f"Failed for value: {val}"
        
        # Test False values
        for val in ['0', 'False', 'false', 'FALSE', '']:
            await manager.execute(db_path, "DELETE FROM test", commit=True)
            if val == '':
                await manager.execute(db_path, "INSERT INTO test VALUES ('')", commit=True)
            else:
                await manager.execute(db_path, f"INSERT INTO test VALUES ('{val}')", commit=True)
            result = await manager.execute(
                db_path,
                "SELECT * FROM test",
                return_type="fetchone",
                expected_types=(bool,)
            )
            assert result[0][0] is False, f"Failed for value: {val}"
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_custom_conversion_preserves_none(self, tmp_path):
        """Test that None values are preserved with custom type conversion."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (a TEXT, b TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES (NULL, NULL)", commit=True)
        
        result = await manager.execute(
            db_path,
            "SELECT * FROM test",
            return_type="fetchone",
            expected_types=(bool, int)
        )
        
        row = result[0]
        assert row[0] is None
        assert row[1] is None
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_string_not_converted_when_not_desired(self, tmp_path):
        """Test that numeric strings remain strings when conversion is not specified."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (title TEXT, value TEXT)", commit=True)
        # Insert numeric string that should NOT be converted
        await manager.execute(db_path, "INSERT INTO test VALUES ('100', 'Item')", commit=True)
        
        # Use None to skip conversion for both columns
        result = await manager.execute(
            db_path,
            "SELECT * FROM test",
            return_type="fetchone",
            expected_types=(None, None)
        )
        
        row = result[0]
        # Both should remain as strings
        assert row[0] == '100'
        assert isinstance(row[0], str)
        assert row[1] == 'Item'
        assert isinstance(row[1], str)
        
        await manager.disconnect_all()
    
    @pytest.mark.asyncio
    async def test_multiple_rows_with_custom_types(self, tmp_path):
        """Test custom type conversion with multiple rows."""
        db_path = str(tmp_path / "test.db")
        manager = Manager()
        
        await manager.connect(db_path)
        await manager.execute(db_path, "CREATE TABLE test (flag TEXT, count TEXT)", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('1', '10')", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('0', '20')", commit=True)
        await manager.execute(db_path, "INSERT INTO test VALUES ('1', '30')", commit=True)
        
        result = await manager.execute(
            db_path,
            "SELECT * FROM test",
            return_type="fetchall",
            expected_types=(bool, int)
        )
        
        assert len(result) == 3
        assert result[0] == (True, 10)
        assert result[1] == (False, 20)
        assert result[2] == (True, 30)
        
        await manager.disconnect_all()
