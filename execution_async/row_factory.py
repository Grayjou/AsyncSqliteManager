"""
Row factory implementations for SQLite type conversion.

This module provides row factory functions that handle automatic type conversion
for SQLite query results, particularly useful for converting string representations
of integers back to int type, which is needed for IntEnum construction.
"""
from typing import Any, Tuple, Optional
import sqlite3


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
