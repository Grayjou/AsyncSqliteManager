Row Factory API
===============

The row_factory module provides functions for customizable type conversion when fetching data from SQLite.

Type Conversion Functions
-------------------------

convert_value(value)
~~~~~~~~~~~~~~~~~~~~

Convert a value to its appropriate Python type.

Attempts to convert string representations of decimal integers to `int` type. This is the default conversion used by AsyncSqliteManager.

**Parameters:**

* **value** (*Any*): The value to convert (typically from a SQLite row)

**Returns:**

* The converted value. If value is a string representing a decimal integer, returns an int. Otherwise, returns the original value unchanged.

**Examples:**

.. code-block:: python

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

**Conversion Rules:**

* Only decimal integer strings are converted (e.g., '123', '-456')
* Strings with prefixes like '0x' (hex), '0o' (octal), or '0b' (binary) are preserved as strings
* Float strings like '123.45' are preserved as strings
* `None` values are preserved
* Other types (actual integers, floats, bytes) are unchanged

convert_value_with_type(value, expected_type)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**NEW in this version!** Convert a value to a specific expected type.

**Parameters:**

* **value** (*Any*): The value to convert
* **expected_type** (*Optional[Type]*): The expected type to convert to. If None, no conversion is performed.

**Returns:**

* The converted value, or the original value if conversion is not possible or not requested

**Examples:**

.. code-block:: python

    >>> convert_value_with_type('1', bool)
    True
    >>> convert_value_with_type('0', bool)
    False
    >>> convert_value_with_type('123', int)
    123
    >>> convert_value_with_type('hello', int)
    'hello'  # Conversion failed, returns original
    >>> convert_value_with_type('123', None)
    '123'  # None type skips conversion

**Boolean Conversion Rules:**

String values converted to bool:

* **True**: ``'1'``, ``'True'``, ``'true'``, ``'TRUE'``
* **False**: ``'0'``, ``'False'``, ``'false'``, ``'FALSE'``, ``''``

Numeric values are converted using Python's `bool()` function.

**Special Handling:**

* If `expected_type` is `None`, no conversion is performed
* If value is `None`, it's preserved as `None`
* If value is already the expected type, it's returned as-is
* If conversion fails, the original value is returned

Row Factory Functions
---------------------

type_converting_row_factory(cursor, row)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Row factory that converts column values to appropriate types.

This is the default row factory used by AsyncSqliteManager. It processes each value in a row and attempts to convert string representations of integers back to int type.

**Parameters:**

* **cursor**: The SQLite cursor object
* **row**: The raw row tuple from SQLite

**Returns:**

* A tuple with converted values

**Use Cases:**

* Columns defined as TEXT but contain integer values
* Queries using CAST operations that convert integers to text
* Working with IntEnum which requires int values, not string representations

**Example:**

.. code-block:: python

    conn.row_factory = type_converting_row_factory
    cursor = conn.execute("SELECT '0', '1', 'hello'")
    result = cursor.fetchone()
    # Result: (0, 1, 'hello')

custom_row_factory(expected_types)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**NEW in this version!** Create a custom row factory with expected types for each column.

**Parameters:**

* **expected_types** (*Optional[Tuple[Optional[Type], ...]]*): A tuple of expected types for each column. 
  Can be shorter than the number of columns (remaining columns use automatic conversion). 
  Use None for a column to skip conversion for that column.

**Returns:**

* A row factory function that can be used with SQLite connections

**Early Escape Optimization:**

If `expected_types` is not provided or is an empty tuple, returns the default `type_converting_row_factory` for optimal performance.

**Examples:**

.. code-block:: python

    # Convert first two columns: bool and int, leave rest with default conversion
    factory = custom_row_factory((bool, int))
    conn.row_factory = factory
    cursor = conn.execute("SELECT '1', '0', 'blablabla', 'uuu'")
    result = cursor.fetchone()
    # Result: (True, 0, 'blablabla', 'uuu')
    
    # Skip first column, convert second to int
    factory = custom_row_factory((None, int))
    conn.row_factory = factory
    cursor = conn.execute("SELECT '1', '0', 'blablabla', 'uuu'")
    result = cursor.fetchone()
    # Result: ('1', 0, 'blablabla', 'uuu')
    
    # Shorter tuple - only specify first column
    factory = custom_row_factory((bool,))
    conn.row_factory = factory  
    cursor = conn.execute("SELECT '1', '123', 'hello'")
    result = cursor.fetchone()
    # Result: (True, 123, 'hello')  # First is bool, second auto-converts to int

**Column Handling:**

* Columns with specified types: Converted using `convert_value_with_type`
* Columns beyond the tuple length: Use automatic conversion via `convert_value`
* None in the tuple: Skips conversion for that specific column

dict_row_factory(cursor, row)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Row factory that returns rows as dictionaries with type conversion.

Similar to `type_converting_row_factory` but returns a dictionary mapping column names to converted values instead of a tuple.

**Parameters:**

* **cursor**: The SQLite cursor object
* **row**: The raw row tuple from SQLite

**Returns:**

* A dictionary mapping column names to converted values

**Example:**

.. code-block:: python

    conn.row_factory = dict_row_factory
    cursor = conn.execute("SELECT '0' as id, 'hello' as name")
    result = cursor.fetchone()
    # Result: {'id': 0, 'name': 'hello'}
