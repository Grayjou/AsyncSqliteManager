Transaction API
===============

The Transaction class provides a context manager for handling SQLite transactions with automatic commit/rollback and status tracking.

Transaction Class
-----------------

.. code-block:: python

    from manager import Manager
    
    manager = Manager()
    
    # Create a transaction
    async with manager.Transaction("mydb", autocommit=True) as txn:
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Alice",))

**Constructor Parameters:**

* **database_path** (*str*): Path or alias of the database
* **autocommit** (*bool*): Whether to commit automatically on success (default: True)
* **log_all** (*bool*): Whether to log all operations (default: False)
* **manager** (*ManagerBase*): The manager instance (required)
* **logger** (*Optional[Logger]*): Custom logger instance

Transaction Methods
-------------------

**execute(query, params=None, return_type="fetchall", commit=False, override_autocommit=False, log=False, override_omnilog=False, mode="write", expected_types=None)**

Execute a SQL query within the transaction.

* **query** (*str*): SQL query to execute
* **params** (*QueryParams*): Parameters to inject
* **return_type** (*str*): Return strategy ('fetchall', 'fetchone', etc.)
* **commit** (*bool*): Whether to commit after execution
* **override_autocommit** (*bool*): Force override of autocommit behavior
* **log** (*bool*): Whether to log this query
* **override_omnilog** (*bool*): Force override of omni_log behavior
* **mode** (*Literal["read", "write"]*): Connection mode to use
* **expected_types** (*Optional[Tuple[Optional[Type], ...]]*): **NEW!** A tuple of expected types for type conversion

The `execute` method supports the same `expected_types` parameter as `Manager.execute`:

.. code-block:: python

    async with manager.Transaction("mydb", autocommit=True) as txn:
        result = await txn.execute(
            "SELECT status, count FROM items",
            expected_types=(bool, int)
        )

**commit(log=False, override_omnilog=False)**

Manually commit the transaction.

**rollback(log=False, override_omnilog=False)**

Manually rollback the transaction.

**savepoint(name)**

Create a named savepoint within the transaction.

**rollback_to(name)**

Roll back to a savepoint.

**release_savepoint(name)**

Release a savepoint.

Transaction Status Properties
------------------------------

**NEW in this version!** Transactions now expose status properties that can be accessed after the transaction context exits.

**succeeded**

Check if the transaction succeeded (committed).

* **Type**: Optional[bool]
* **Returns**: True if transaction was committed, False if rolled back, None if still in progress

.. code-block:: python

    async with manager.Transaction("mydb", autocommit=True) as txn:
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Alice",))
    
    if txn.succeeded:
        print("Transaction was committed successfully")
        # Perform follow-up actions

**failed**

Check if the transaction failed (rolled back).

* **Type**: Optional[bool]
* **Returns**: True if transaction was rolled back, False if committed, None if still in progress

.. code-block:: python

    txn = manager.Transaction("mydb", autocommit=True)
    try:
        async with txn:
            await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Bob",))
            raise ValueError("Simulated error")
    except ValueError:
        pass
    
    if txn.failed:
        print("Transaction was rolled back")
        # Handle failure

**Status Values:**

* **During transaction**: Both properties return `None`
* **After successful commit**: `succeeded` is `True`, `failed` is `False`
* **After rollback** (exception or autocommit=False): `succeeded` is `False`, `failed` is `True`

**Use Cases:**

The status properties are particularly useful for:

* Logging audit trails based on transaction outcomes
* Sending notifications on transaction failure
* Implementing retry logic
* Recording metrics and analytics
* Conditional cleanup or follow-up operations

.. code-block:: python

    # Example: Audit logging based on transaction status
    async with manager.Transaction("mydb", autocommit=True) as txn:
        await txn.execute("UPDATE account SET balance = balance - ?", params=(100,))
    
    if txn.succeeded:
        await manager.execute(
            "audit_db",
            "INSERT INTO audit_log VALUES (?, ?, ?)",
            params=("withdraw", 100, "success"),
            commit=True
        )
    else:
        await manager.execute(
            "audit_db",
            "INSERT INTO audit_log VALUES (?, ?, ?)",
            params=("withdraw", 100, "failed"),
            commit=True
        )
