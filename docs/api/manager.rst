Manager API
===========

The Manager class is the main entry point for database operations.

Manager Class
-------------

.. code-block:: python

    from manager import Manager
    
    manager = Manager(
        autocommit=False,          # Auto-commit after each query
        omni_log=False,            # Log all queries
        history_length=10,         # Maximum history entries to keep
        log_results=True,          # Include results in history
        logger=None,               # Custom logger instance
        history_tolerance=5,       # Tolerance for history overflow
    )

Connection Management
~~~~~~~~~~~~~~~~~~~~~

**connect(db_path, alias=None, create_read_connection=False, mode="write")**

Connect to a SQLite database.

* **db_path** (*str*): Path to the SQLite database file
* **alias** (*Optional[str]*): Optional alias for the database path
* **create_read_connection** (*bool*): If True, creates a separate read connection
* **mode** (*Literal["read", "write"]*): Which connection to return
* **Returns**: The requested connection to the database

**get_connection(path_or_alias, mode="write")**

Get the connection associated with a given path or alias.

* **path_or_alias** (*str*): The path or alias of the database
* **mode** (*Literal["read", "write"]*): "read" or "write", defaults to "write"
* **Returns**: The connection for the specified mode, or None if not found

**close(db_path)** / **disconnect(db_path)**

Close a database connection (both read and write connections).

* **db_path** (*str*): The path or alias of the database to close

**disconnect_all()**

Close all open connections.

**shutdown()**

Gracefully shutdown: disconnect all connections and flush history.

Query Execution
~~~~~~~~~~~~~~~

**execute(db_path, query, params=None, return_type="fetchall", cursor=None, commit=False, override_autocommit=False, log=False, override_omnilog=False, mode="write", create_read_connection=True, expected_types=None)**

Execute a SQL query on the specified database.

* **db_path** (*str*): Path or alias of the target SQLite database
* **query** (*str*): SQL query to execute
* **params** (*Optional[QueryParams]*): Parameters to inject
* **return_type** (*str*): Return strategy ('fetchall', 'fetchone', etc.)
* **cursor** (*Optional[AioCursor]*): Cursor to use for execution
* **commit** (*bool*): Whether to commit after execution
* **override_autocommit** (*bool*): Force override of autocommit behavior
* **log** (*bool*): Whether to log this query
* **override_omnilog** (*bool*): Force override of omni_log behavior
* **mode** (*Literal["read", "write"]*): Connection mode to use
* **create_read_connection** (*bool*): If True and mode="read", creates a separate read connection
* **expected_types** (*Optional[Tuple[Optional[Type], ...]]*): **NEW!** A tuple of expected types for type conversion
* **Returns**: Query results, if any

The `expected_types` parameter enables customizable type conversion:

.. code-block:: python

    # Convert first two columns: bool and int
    result = await manager.execute(
        "mydb",
        "SELECT flag, count, name FROM items",
        expected_types=(bool, int)
    )
    
    # Skip first column, convert second to int
    result = await manager.execute(
        "mydb",
        "SELECT id, count FROM items",
        expected_types=(None, int)
    )

Transaction Management
~~~~~~~~~~~~~~~~~~~~~~

**commit(db_path, log=False, override_omnilog=False)**

Commit the current transaction.

**rollback(db_path, log=False, override_omnilog=False)**

Rollback the current transaction.

**savepoint(db_path, name)**

Create a named savepoint.

**rollback_to(db_path, name)**

Roll back to a savepoint.

**release_savepoint(db_path, name)**

Release a savepoint.

Context Managers
~~~~~~~~~~~~~~~~

**Transaction(database_path, autocommit=True, log_all=False, manager=None, logger=None)**

Create a Transaction context manager.

.. code-block:: python

    async with manager.Transaction("mydb", autocommit=True) as txn:
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Alice",))

**safe_transaction(db_path, \*\*kw)**

Transaction that automatically acquires the per-DB lock.

.. code-block:: python

    async with manager.safe_transaction("mydb") as txn:
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Alice",))

**queue(db_path)**

Serialize all queries and transactions for this database path.

.. code-block:: python

    async with manager.queue("mydb"):
        # All operations here are serialized
        await manager.execute("mydb", "SELECT * FROM users")

Properties
~~~~~~~~~~

**databases**

Returns a list of all connected database paths.

**history_length**

Get or set the history length. Set to None to disable history.

**history_tolerance**

Get or set the history tolerance.
