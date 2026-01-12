Exceptions API
==============

AsyncSqliteManager defines custom exception classes for error handling.

Exception Classes
-----------------

ConnectionError
~~~~~~~~~~~~~~~

Raised when a database connection fails or is not available.

**Inherits from:** `Exception`

**Use Cases:**

* Failed to connect to a database file
* Database file doesn't exist or is inaccessible
* Connection is not found when attempting to access it

**Examples:**

.. code-block:: python

    from manager import Manager, ConnectionError
    
    try:
        manager = Manager()
        await manager.connect("/nonexistent/path/db.sqlite")
    except ConnectionError as e:
        print(f"Connection failed: {e}")
        # Handle connection error (e.g., retry, use fallback, notify user)

TransactionError
~~~~~~~~~~~~~~~~

Raised when a transaction operation fails.

**Inherits from:** `Exception`

**Use Cases:**

* Failed to begin a transaction
* Failed to commit or rollback
* Transaction was created without a manager instance
* Transaction connection issues

**Examples:**

.. code-block:: python

    from manager import Transaction, TransactionError
    
    try:
        # This will raise TransactionError because manager is None
        txn = Transaction("test.db", manager=None)
    except TransactionError as e:
        print(f"Transaction error: {e}")
    
    # Handle BEGIN failure
    try:
        async with manager.Transaction("mydb") as txn:
            await txn.execute("INSERT INTO users VALUES (?)", params=("Alice",))
    except TransactionError as e:
        print(f"Transaction failed: {e}")
        # Handle error (e.g., retry, log, notify)

HistoryError
~~~~~~~~~~~~

Raised when a history management operation fails.

**Inherits from:** `Exception`

**Use Cases:**

* Failed to write history to file
* Failed to flush history
* History configuration errors

**Examples:**

.. code-block:: python

    from manager import Manager, HistoryError
    
    manager = Manager(history_length=10)
    
    try:
        await manager.flush_history_to_file()
    except HistoryError as e:
        print(f"History operation failed: {e}")
        # Handle error (e.g., try alternative storage, log warning)

Error Handling Best Practices
------------------------------

1. **Catch Specific Exceptions**

   Always catch specific exceptions rather than generic `Exception` when possible:

   .. code-block:: python

       try:
           await manager.execute("mydb", "INSERT INTO users VALUES (?)", params=("Alice",))
       except ConnectionError:
           # Handle connection-specific issues
           await reconnect()
       except TransactionError:
           # Handle transaction-specific issues
           await rollback_and_retry()

2. **Use Context Managers**

   Transactions automatically handle rollback on exceptions:

   .. code-block:: python

       try:
           async with manager.Transaction("mydb", autocommit=True) as txn:
               await txn.execute("INSERT INTO users VALUES (?)", params=("Alice",))
       except Exception as e:
           # Transaction already rolled back automatically
           logger.error(f"Transaction failed: {e}")

3. **Check Transaction Status**

   Use the new status properties for follow-up logic:

   .. code-block:: python

       async with manager.Transaction("mydb", autocommit=True) as txn:
           try:
               await txn.execute("INSERT INTO users VALUES (?)", params=("Alice",))
           except Exception as e:
               logger.error(f"Error during transaction: {e}")
       
       # Check status after exit
       if txn.failed:
           # Handle failure case
           await send_alert("Transaction failed")

4. **Graceful Degradation**

   Implement fallback strategies:

   .. code-block:: python

       try:
           await manager.connect("primary.db", alias="db")
       except ConnectionError:
           # Fallback to secondary database
           try:
               await manager.connect("backup.db", alias="db")
           except ConnectionError:
               # Last resort: in-memory database
               await manager.connect(":memory:", alias="db")
