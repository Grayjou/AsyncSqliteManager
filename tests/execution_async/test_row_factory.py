# tests/execution_async/test_row_factory.py
"""Tests for row factory type conversion functionality."""
import pytest
from enum import IntEnum
from ...execution_async.row_factory import (
    convert_value,
    type_converting_row_factory,
    dict_row_factory
)


class ListType(IntEnum):
    """Example IntEnum for testing."""
    TYPE_A = 0
    TYPE_B = 1


class TestConvertValue:
    """Tests for convert_value function."""
    
    def test_convert_integer_string(self):
        """Test conversion of integer strings."""
        assert convert_value('0') == 0
        assert convert_value('123') == 123
        assert convert_value('-456') == -456
        
    def test_preserve_actual_integers(self):
        """Test that actual integers are preserved."""
        assert convert_value(0) == 0
        assert convert_value(123) == 123
        assert convert_value(-456) == -456
        
    def test_preserve_non_numeric_strings(self):
        """Test that non-numeric strings are preserved."""
        assert convert_value('hello') == 'hello'
        assert convert_value('world123') == 'world123'
        assert convert_value('') == ''
        
    def test_preserve_float_strings(self):
        """Test that float strings are preserved as strings."""
        # We don't want to convert floats to ints
        assert convert_value('123.45') == '123.45'
        assert convert_value('0.0') == '0.0'
        
    def test_handle_none(self):
        """Test that None is handled correctly."""
        assert convert_value(None) is None
        
    def test_preserve_other_types(self):
        """Test that other types are preserved."""
        assert convert_value(12.34) == 12.34
        assert convert_value(True) is True
        assert convert_value(False) is False
        assert convert_value(b'bytes') == b'bytes'
        
    def test_preserve_hex_strings(self):
        """Test that hex strings are preserved."""
        assert convert_value('0x10') == '0x10'
        assert convert_value('0X10') == '0X10'
        
    def test_preserve_octal_strings(self):
        """Test that octal strings are preserved."""
        assert convert_value('0o10') == '0o10'
        assert convert_value('0O10') == '0O10'
        
    def test_preserve_binary_strings(self):
        """Test that binary strings are preserved."""
        assert convert_value('0b10') == '0b10'
        assert convert_value('0B10') == '0B10'
        
    def test_handle_empty_string(self):
        """Test that empty strings are handled."""
        assert convert_value('') == ''


class TestTypeConvertingRowFactory:
    """Tests for type_converting_row_factory."""
    
    def test_converts_integer_strings_in_row(self):
        """Test that integer strings in rows are converted."""
        # Mock cursor with description
        class MockCursor:
            description = [('id',), ('value',), ('name',)]
        
        cursor = MockCursor()
        row = ('1', '0', 'Alice')
        result = type_converting_row_factory(cursor, row)
        
        assert result == (1, 0, 'Alice')
        assert isinstance(result[0], int)
        assert isinstance(result[1], int)
        assert isinstance(result[2], str)
        
    def test_preserves_actual_integers(self):
        """Test that actual integers in rows are preserved."""
        class MockCursor:
            description = [('id',), ('value',)]
        
        cursor = MockCursor()
        row = (1, 2)
        result = type_converting_row_factory(cursor, row)
        
        assert result == (1, 2)
        
    def test_handles_mixed_types(self):
        """Test handling of mixed types in rows."""
        class MockCursor:
            description = [('id',), ('name',), ('count',), ('price',)]
        
        cursor = MockCursor()
        row = ('123', 'Product', 5, 19.99)
        result = type_converting_row_factory(cursor, row)
        
        assert result == (123, 'Product', 5, 19.99)
        assert isinstance(result[0], int)
        assert isinstance(result[1], str)
        assert isinstance(result[2], int)
        assert isinstance(result[3], float)
        
    def test_handles_none_values(self):
        """Test handling of None values in rows."""
        class MockCursor:
            description = [('id',), ('value',)]
        
        cursor = MockCursor()
        row = ('1', None)
        result = type_converting_row_factory(cursor, row)
        
        assert result == (1, None)
        
    def test_works_with_intenum(self):
        """Test that converted values work with IntEnum."""
        class MockCursor:
            description = [('list_type',)]
        
        cursor = MockCursor()
        # Simulate TEXT column containing integer
        row = ('0',)
        result = type_converting_row_factory(cursor, row)
        
        # This should work now - no ValueError
        list_type = ListType(result[0])
        assert list_type == ListType.TYPE_A
        assert list_type.value == 0


class TestDictRowFactory:
    """Tests for dict_row_factory."""
    
    def test_returns_dict_with_converted_values(self):
        """Test that dict row factory returns dict with converted values."""
        class MockCursor:
            description = [('id',), ('name',), ('count',)]
        
        cursor = MockCursor()
        row = ('123', 'Alice', '5')
        result = dict_row_factory(cursor, row)
        
        assert isinstance(result, dict)
        assert result == {'id': 123, 'name': 'Alice', 'count': 5}
        assert isinstance(result['id'], int)
        assert isinstance(result['name'], str)
        assert isinstance(result['count'], int)
        
    def test_handles_none_in_dict(self):
        """Test None handling in dict row factory."""
        class MockCursor:
            description = [('id',), ('value',)]
        
        cursor = MockCursor()
        row = ('1', None)
        result = dict_row_factory(cursor, row)
        
        assert result == {'id': 1, 'value': None}
        
    def test_dict_with_intenum(self):
        """Test dict row factory with IntEnum."""
        class MockCursor:
            description = [('id',), ('list_type',)]
        
        cursor = MockCursor()
        row = ('1', '0')
        result = dict_row_factory(cursor, row)
        
        # Should work with IntEnum
        list_type = ListType(result['list_type'])
        assert list_type == ListType.TYPE_A
