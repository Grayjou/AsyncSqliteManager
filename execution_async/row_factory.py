"""
Row factory implementations for SQLite type conversion.

This module provides row factory functions that handle automatic type conversion
for SQLite query results, particularly useful for converting string representations
of integers back to int type, which is needed for IntEnum construction.
"""
from typing import Any, Tuple, Optional, Callable, Type
import sqlite3

# Constants for boolean string conversion
FALSY_STRINGS = ('0', 'False', 'false', 'FALSE', '')
TRUTHY_STRINGS = ('1', 'True', 'true', 'TRUE')


def convert_value(value: Any) -> Any:
    """
    Convert a value to its appropriate Python type.
    
    Attempts to convert string representations of decimal integers to int type.
    This is particularly useful for handling TEXT columns that contain integer values
    or CAST operations that convert integers to text.
    
    Args:
        value: The value to convert (typically from a SQLite row).
        
    Returns:
        The converted value. If value is a string representing a decimal integer
        (including negative integers), returns an int. Otherwise, returns the 
        original value unchanged.
        
    Examples:
        >>> convert_value('123')
        123
        >>> convert_value('0')
        0
        >>> convert_value('hello')
        'hello'
        >>> convert_value(123)
        123
        >>> convert_value(None)
        None
        
    Note:
        Only decimal integer strings are converted. Strings with prefixes like
        '0x' (hex), '0o' (octal), or '0b' (binary) are treated as non-numeric
        and preserved as strings. Float strings like '123.45' are also preserved.
    """
    if value is None:
        return None
    
    # Only try to convert strings
    if not isinstance(value, str):
        return value
    
    # Skip empty strings
    if not value:
        return value
    
    # Try to convert to integer
    try:
        # Only convert if it looks like a decimal integer (no decimal point, no prefixes)
        # This check is faster than trying int() conversion on complex strings
        if '.' in value or value.startswith(('0x', '0X', '0o', '0O', '0b', '0B')):
            return value
            
        int_value = int(value)
        # Verify round-trip conversion to ensure we're not losing information
        if str(int_value) == value:
            return int_value
    except (ValueError, OverflowError):
        pass
    
    # If conversion failed or string doesn't match, return original
    return value


def type_converting_row_factory(cursor: sqlite3.Cursor, row: Tuple) -> Tuple:
    """
    Row factory that converts column values to appropriate types.
    
    This row factory processes each value in a row and attempts to convert
    string representations of integers back to int type. This is useful when:
    - Columns are defined as TEXT but contain integer values
    - Queries use CAST operations that convert integers to text
    - Working with IntEnum which requires int values, not string representations
    
    Args:
        cursor: The SQLite cursor object.
        row: The raw row tuple from SQLite.
        
    Returns:
        A tuple with converted values.
        
    Examples:
        When used as a row factory:
        >>> conn.row_factory = type_converting_row_factory
        >>> cursor = conn.execute("SELECT '0', '1', 'hello'")
        >>> cursor.fetchone()
        (0, 1, 'hello')
    """
    return tuple(convert_value(value) for value in row)


def dict_row_factory(cursor: sqlite3.Cursor, row: Tuple) -> dict:
    """
    Row factory that returns rows as dictionaries with type conversion.
    
    Similar to type_converting_row_factory but returns a dictionary mapping
    column names to (converted) values instead of a tuple.
    
    Args:
        cursor: The SQLite cursor object.
        row: The raw row tuple from SQLite.
        
    Returns:
        A dictionary mapping column names to converted values.
        
    Examples:
        >>> conn.row_factory = dict_row_factory
        >>> cursor = conn.execute("SELECT '0' as id, 'hello' as name")
        >>> cursor.fetchone()
        {'id': 0, 'name': 'hello'}
    """
    fields = [column[0] for column in cursor.description]
    return {key: convert_value(value) for key, value in zip(fields, row)}


def convert_value_with_type(value: Any, expected_type: Optional[Type]) -> Any:
    """
    Convert a value to a specific expected type.
    
    Args:
        value: The value to convert.
        expected_type: The expected type to convert to. If None, no conversion is performed.
        
    Returns:
        The converted value, or the original value if conversion is not possible or not requested.
        
    Examples:
        >>> convert_value_with_type('1', bool)
        True
        >>> convert_value_with_type('0', bool)
        False
        >>> convert_value_with_type('123', int)
        123
        >>> convert_value_with_type('hello', int)
        'hello'
        >>> convert_value_with_type('123', None)
        '123'
    """
    # If None type is specified, skip conversion
    if expected_type is None:
        return value
    
    # If value is None, return as-is
    if value is None:
        return value
    
    # If value is already the expected type, return as-is
    if isinstance(value, expected_type):
        return value
    
    # Special handling for bool type
    if expected_type is bool:
        # Convert string representations to bool
        if isinstance(value, str):
            if value in FALSY_STRINGS:
                return False
            elif value in TRUTHY_STRINGS:
                return True
        # Convert numeric types to bool
        elif isinstance(value, (int, float)):
            return bool(value)
        return value
    
    # Try to convert to the expected type
    try:
        return expected_type(value)
    except (ValueError, TypeError):
        # If conversion fails, return original value
        return value


def custom_row_factory(expected_types: Optional[Tuple[Optional[Type], ...]] = None) -> Callable:
    """
    Create a custom row factory with expected types for each column.
    
    Args:
        expected_types: A tuple of expected types for each column. Can be shorter than 
                       the number of columns (remaining columns use automatic conversion).
                       Use None for a column to skip conversion for that column.
                       
    Returns:
        A row factory function that can be used with SQLite connections.
        
    Examples:
        >>> # Convert first two columns: bool and int, leave rest as-is
        >>> conn.row_factory = custom_row_factory((bool, int))
        >>> cursor = conn.execute("SELECT '1', '0', 'blablabla', 'uuu'")
        >>> cursor.fetchone()
        (True, 0, 'blablabla', 'uuu')
        
        >>> # Skip first column, convert second to int
        >>> conn.row_factory = custom_row_factory((None, int))
        >>> cursor = conn.execute("SELECT '1', '0', 'blablabla', 'uuu'")
        >>> cursor.fetchone()
        ('1', 0, 'blablabla', 'uuu')
    """
    # Early escape if no types provided - use default conversion
    if not expected_types:
        return type_converting_row_factory
    
    def row_factory(cursor: sqlite3.Cursor, row: Tuple) -> Tuple:
        """Custom row factory that applies expected types."""
        result = []
        for i, value in enumerate(row):
            if i < len(expected_types):
                # Apply expected type conversion
                result.append(convert_value_with_type(value, expected_types[i]))
            else:
                # Use automatic conversion for remaining columns
                result.append(convert_value(value))
        return tuple(result)
    
    return row_factory
