AsyncSqliteManager Documentation
=================================

Welcome to AsyncSqliteManager's documentation!

AsyncSqliteManager is an async SQLite database connection manager for Python, built on top of `aiosqlite`. It provides a high-level API for managing multiple database connections, transactions, and query history with advanced features like customizable type conversion.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   quickstart
   features
   api/index
   examples
   changelog

Features
--------

* **Async/Await Support**: Built on `aiosqlite` for non-blocking database operations
* **Multiple Database Connections**: Manage connections to multiple SQLite databases simultaneously
* **Read/Write Connection Separation**: Support for separate read and write connections for improved concurrency
* **Customizable Type Conversion**: Flexible type conversion with per-query control
* **Transaction Management**: Context managers for safe transaction handling with status tracking
* **Path Aliases**: Reference databases using custom aliases instead of full paths
* **Query History**: Track query execution history with optional file dumping
* **Autocommit Mode**: Optional automatic commit after each query
* **Logging Integration**: Built-in logging support for query tracking

Quick Start
-----------

.. code-block:: python

    import asyncio
    from manager import Manager

    async def main():
        # Create a manager instance
        manager = Manager(autocommit=False, omni_log=True)
        
        # Connect to a database
        await manager.connect("example.db", alias="mydb")
        
        # Execute queries
        await manager.execute("mydb", "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
        await manager.execute("mydb", "INSERT INTO users (name) VALUES (?)", params=("Alice",), commit=True)
        
        # Query data
        rows = await manager.execute("mydb", "SELECT * FROM users")
        print(rows)  # [(1, 'Alice')]
        
        # Use transactions with status tracking
        async with manager.Transaction("mydb") as txn:
            await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Bob",))
            await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Charlie",))
        
        # Check transaction status
        if txn.succeeded:
            print("Transaction committed successfully!")
        
        # Shutdown gracefully
        await manager.shutdown()

    asyncio.run(main())

Installation
------------

.. code-block:: bash

    pip install aiosqlite aiofiles

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
