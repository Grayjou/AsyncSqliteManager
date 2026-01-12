Features
========

AsyncSqliteManager provides a comprehensive set of features for managing SQLite databases in async Python applications.

Async/Await Support
-------------------

Built on top of `aiosqlite`, AsyncSqliteManager provides full async/await support for non-blocking database operations.

.. code-block:: python

    async def fetch_users():
        result = await manager.execute("mydb", "SELECT * FROM users")
        return result

Multiple Database Connections
------------------------------

Manage connections to multiple SQLite databases simultaneously, each with its own alias for easy reference.

.. code-block:: python

    await manager.connect("users.db", alias="users")
    await manager.connect("products.db", alias="products")
    
    users = await manager.execute("users", "SELECT * FROM users")
    products = await manager.execute("products", "SELECT * FROM products")

Read/Write Connection Separation
---------------------------------

Improve concurrency by using separate connections for read and write operations.

.. code-block:: python

    # Create connection with separate read connection
    await manager.connect("database.db", create_read_connection=True)
    
    # Read operations use read connection
    users = await manager.execute("database.db", "SELECT * FROM users", mode="read")
    
    # Write operations use write connection
    await manager.execute("database.db", "INSERT INTO users VALUES (?, ?)", 
                         params=(1, "Alice"), commit=True, mode="write")

Customizable Type Conversion
-----------------------------

New in this version! Control how data is converted from SQLite to Python types on a per-query basis.

Default Automatic Conversion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, AsyncSqliteManager automatically converts string representations of integers to `int` type:

.. code-block:: python

    # Even if the column is TEXT, integer strings are converted to int
    await manager.execute("mydb", "CREATE TABLE tasks (status TEXT)", commit=True)
    await manager.execute("mydb", "INSERT INTO tasks VALUES ('0')", commit=True)
    
    result = await manager.execute("mydb", "SELECT status FROM tasks", return_type="fetchone")
    status_value = result[0][0]  # Returns 0 as int, not '0' as string

Custom Type Conversion
~~~~~~~~~~~~~~~~~~~~~~

Use the `expected_types` parameter to specify exactly how each column should be converted:

.. code-block:: python

    # Convert first column to bool, second to int
    result = await manager.execute(
        "mydb",
        "SELECT '1', '0', 'blablabla', 'uuu'",
        expected_types=(bool, int)
    )
    # Result: (True, 0, 'blablabla', 'uuu')
    
    # Skip conversion for specific columns using None
    result = await manager.execute(
        "mydb",
        "SELECT '1', '0', 'blablabla', 'uuu'",
        expected_types=(None, int)
    )
    # Result: ('1', 0, 'blablabla', 'uuu')

This prevents issues where numeric strings (like titles or descriptions) are silently converted to integers when you don't want them to be.

Transaction Management with Status Tracking
--------------------------------------------

New in this version! Transactions now provide status properties to track success or failure.

Transaction Context Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async with manager.Transaction("mydb", autocommit=True) as txn:
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Alice",))
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Bob",))
        # Automatically commits on success, rolls back on exception

Transaction Status Properties
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async with manager.Transaction("mydb", autocommit=True) as txn:
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Alice",))
    
    # Check transaction status after exit
    if txn.succeeded:
        print("Transaction was committed")
        # Perform follow-up actions
    
    if txn.failed:
        print("Transaction was rolled back")
        # Handle failure

Safe Transactions
~~~~~~~~~~~~~~~~~

Use safe transactions with automatic locking to prevent concurrent access:

.. code-block:: python

    async with manager.safe_transaction("mydb") as txn:
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Alice",))
        # Prevents concurrent access to the same database

Transaction Custom Type Conversion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Transactions support the same custom type conversion as regular execute calls:

.. code-block:: python

    async with manager.Transaction("mydb", autocommit=True) as txn:
        result = await txn.execute(
            "SELECT status, count FROM items",
            expected_types=(bool, int)
        )

Savepoints
~~~~~~~~~~

.. code-block:: python

    await manager.savepoint("mydb", "sp1")
    await manager.execute("mydb", "INSERT INTO users (name) VALUES (?)", params=("Alice",))
    await manager.rollback_to("mydb", "sp1")  # Undo changes since savepoint
    await manager.release_savepoint("mydb", "sp1")  # Release savepoint

Query History
-------------

Track query execution history with optional file dumping:

.. code-block:: python

    # Get current history length
    length = manager.history_length
    
    # Set history length (None to disable)
    manager.history_length = 20
    
    # Flush history to file
    await manager.flush_history_to_file()

Logging Integration
-------------------

Built-in logging support for query tracking:

.. code-block:: python

    import logging
    
    logger = logging.getLogger("my_app")
    manager = Manager(logger=logger, omni_log=True)

Path Aliases
------------

Reference databases using custom aliases instead of full paths:

.. code-block:: python

    await manager.connect("/long/path/to/database.db", alias="mydb")
    
    # Use alias instead of full path
    result = await manager.execute("mydb", "SELECT * FROM users")

Autocommit Mode
---------------

Optional automatic commit after each query:

.. code-block:: python

    manager = Manager(autocommit=True)
    
    # This query will be automatically committed
    await manager.execute("mydb", "INSERT INTO users VALUES (?, ?)", params=(1, "Alice"))
