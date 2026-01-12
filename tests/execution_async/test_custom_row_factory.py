# tests/execution_async/test_custom_row_factory.py
"""Tests for custom row factory with expected types."""
import pytest
from ...execution_async.row_factory import (
    convert_value_with_type,
    custom_row_factory
)


class TestConvertValueWithType:
    """Tests for convert_value_with_type function."""
    
    def test_bool_conversion_from_string_true(self):
        """Test bool conversion for true values."""
        assert convert_value_with_type('1', bool) is True
        assert convert_value_with_type('True', bool) is True
        assert convert_value_with_type('true', bool) is True
        assert convert_value_with_type('TRUE', bool) is True
    
    def test_bool_conversion_from_string_false(self):
        """Test bool conversion for false values."""
        assert convert_value_with_type('0', bool) is False
        assert convert_value_with_type('False', bool) is False
        assert convert_value_with_type('false', bool) is False
        assert convert_value_with_type('FALSE', bool) is False
        assert convert_value_with_type('', bool) is False
    
    def test_bool_conversion_from_int(self):
        """Test bool conversion from integers."""
        assert convert_value_with_type(1, bool) is True
        assert convert_value_with_type(0, bool) is False
        assert convert_value_with_type(42, bool) is True
    
    def test_int_conversion_from_string(self):
        """Test int conversion from strings."""
        assert convert_value_with_type('123', int) == 123
        assert convert_value_with_type('0', int) == 0
        assert convert_value_with_type('-456', int) == -456
    
    def test_none_type_skips_conversion(self):
        """Test that None type skips conversion."""
        assert convert_value_with_type('123', None) == '123'
        assert convert_value_with_type('hello', None) == 'hello'
        assert convert_value_with_type(123, None) == 123
    
    def test_none_value_preserved(self):
        """Test that None values are preserved."""
        assert convert_value_with_type(None, bool) is None
        assert convert_value_with_type(None, int) is None
        assert convert_value_with_type(None, str) is None
    
    def test_already_correct_type(self):
        """Test that values already of correct type are preserved."""
        assert convert_value_with_type(123, int) == 123
        assert convert_value_with_type(True, bool) is True
        assert convert_value_with_type('hello', str) == 'hello'
    
    def test_failed_conversion_returns_original(self):
        """Test that failed conversions return original value."""
        assert convert_value_with_type('hello', int) == 'hello'
        assert convert_value_with_type('not_a_bool', bool) == 'not_a_bool'
    
    def test_str_conversion(self):
        """Test str conversion."""
        assert convert_value_with_type(123, str) == '123'
        assert convert_value_with_type(True, str) == 'True'
    
    def test_float_conversion(self):
        """Test float conversion."""
        assert convert_value_with_type('123.45', float) == 123.45
        assert convert_value_with_type('0.0', float) == 0.0
        assert convert_value_with_type(123, float) == 123.0


class TestCustomRowFactory:
    """Tests for custom_row_factory function."""
    
    def test_custom_factory_with_bool_and_int(self):
        """Test custom factory with (bool, int) types."""
        class MockCursor:
            description = [('a',), ('b',), ('c',), ('d',)]
        
        factory = custom_row_factory((bool, int))
        cursor = MockCursor()
        row = ('1', '0', 'blablabla', 'uuu')
        
        result = factory(cursor, row)
        
        assert result[0] is True
        assert result[1] == 0
        assert result[2] == 'blablabla'
        assert result[3] == 'uuu'
    
    def test_custom_factory_with_none_skips(self):
        """Test custom factory with None to skip conversion."""
        class MockCursor:
            description = [('a',), ('b',), ('c',), ('d',)]
        
        factory = custom_row_factory((None, int))
        cursor = MockCursor()
        row = ('1', '0', 'blablabla', 'uuu')
        
        result = factory(cursor, row)
        
        assert result[0] == '1'  # Skipped
        assert result[1] == 0    # Converted to int
        assert result[2] == 'blablabla'  # Default conversion (remains string)
        assert result[3] == 'uuu'  # Default conversion (remains string)
    
    def test_custom_factory_shorter_tuple(self):
        """Test custom factory with shorter tuple than row length."""
        class MockCursor:
            description = [('a',), ('b',), ('c',)]
        
        factory = custom_row_factory((bool,))
        cursor = MockCursor()
        row = ('1', '123', 'hello')
        
        result = factory(cursor, row)
        
        assert result[0] is True  # Custom bool conversion
        assert result[1] == 123   # Default automatic conversion to int
        assert result[2] == 'hello'  # Remains string
    
    def test_custom_factory_empty_tuple_uses_default(self):
        """Test custom factory with empty tuple uses default conversion."""
        class MockCursor:
            description = [('a',), ('b',)]
        
        factory = custom_row_factory(())
        cursor = MockCursor()
        row = ('123', 'hello')
        
        result = factory(cursor, row)
        
        # Should use default automatic conversion
        assert result[0] == 123
        assert result[1] == 'hello'
    
    def test_custom_factory_none_values(self):
        """Test custom factory preserves None values."""
        class MockCursor:
            description = [('a',), ('b',)]
        
        factory = custom_row_factory((bool, int))
        cursor = MockCursor()
        row = (None, None)
        
        result = factory(cursor, row)
        
        assert result[0] is None
        assert result[1] is None
    
    def test_custom_factory_mixed_types(self):
        """Test custom factory with various type conversions."""
        class MockCursor:
            description = [('flag',), ('count',), ('price',), ('name',)]
        
        factory = custom_row_factory((bool, int, float))
        cursor = MockCursor()
        row = ('1', '42', '19.99', 'Product')
        
        result = factory(cursor, row)
        
        assert result[0] is True
        assert result[1] == 42
        assert result[2] == 19.99
        assert result[3] == 'Product'
