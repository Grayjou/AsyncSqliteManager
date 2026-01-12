Quick Start Guide
=================

This guide will help you get started with AsyncSqliteManager quickly.

Installation
------------

First, install the required dependencies:

.. code-block:: bash

    pip install aiosqlite aiofiles

Basic Usage
-----------

Creating a Manager
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from manager import Manager

    # Create a manager with optional settings
    manager = Manager(
        autocommit=False,          # Auto-commit after each query
        omni_log=False,            # Log all queries
        history_length=10,         # Maximum history entries to keep
        log_results=True,          # Include results in history
    )

Connecting to Databases
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Basic connection
    conn = await manager.connect("path/to/database.db")

    # With alias for easier reference
    conn = await manager.connect("path/to/database.db", alias="mydb")

    # With separate read connection for improved concurrency
    conn = await manager.connect("path/to/database.db", create_read_connection=True)

Executing Queries
~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Simple query
    result = await manager.execute("mydb", "SELECT * FROM users")

    # With parameters
    result = await manager.execute(
        "mydb",
        "INSERT INTO users (name, email) VALUES (?, ?)",
        params=("Alice", "alice@example.com"),
        commit=True
    )

    # With custom type conversion
    result = await manager.execute(
        "mydb",
        "SELECT status, count, name FROM items",
        expected_types=(bool, int)  # Convert first column to bool, second to int
    )

Using Transactions
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Basic transaction with auto-commit
    async with manager.Transaction("mydb", autocommit=True) as txn:
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Alice",))
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Bob",))

    # Check if transaction succeeded
    if txn.succeeded:
        print("Transaction committed successfully!")
    else:
        print("Transaction was rolled back")

    # Manual commit control
    async with manager.Transaction("mydb", autocommit=False) as txn:
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Charlie",))
        await txn.commit()  # Explicitly commit

Customizable Type Conversion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

AsyncSqliteManager provides flexible type conversion to handle SQLite's dynamic typing:

.. code-block:: python

    # Convert specific columns to specific types
    result = await manager.execute(
        "mydb",
        "SELECT flag, count, name, description",
        expected_types=(bool, int)
    )
    # Result: flag is bool, count is int, name and description use automatic conversion

    # Skip conversion for specific columns using None
    result = await manager.execute(
        "mydb",
        "SELECT id, name, count",
        expected_types=(None, None, int)
    )
    # Result: id and name remain as-is, only count is converted to int

    # Shorter tuples automatically pad with default conversion
    result = await manager.execute(
        "mydb",
        "SELECT a, b, c, d",
        expected_types=(bool,)
    )
    # Result: a is bool, b, c, d use automatic conversion

Cleanup
~~~~~~~

.. code-block:: python

    # Close specific connection
    await manager.close("mydb")

    # Close all connections and flush history
    await manager.shutdown()
