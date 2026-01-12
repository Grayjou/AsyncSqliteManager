Examples
========

This page contains practical examples of using AsyncSqliteManager.

Basic Database Operations
--------------------------

Creating Tables and Inserting Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio
    from manager import Manager

    async def setup_database():
        manager = Manager()
        await manager.connect("app.db", alias="app")
        
        # Create table
        await manager.execute(
            "app",
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                active INTEGER DEFAULT 1
            )""",
            commit=True
        )
        
        # Insert data
        users = [
            ("Alice", "alice@example.com"),
            ("Bob", "bob@example.com"),
            ("Charlie", "charlie@example.com")
        ]
        
        for name, email in users:
            await manager.execute(
                "app",
                "INSERT INTO users (name, email) VALUES (?, ?)",
                params=(name, email),
                commit=True
            )
        
        await manager.shutdown()

    asyncio.run(setup_database())

Querying Data
~~~~~~~~~~~~~

.. code-block:: python

    async def query_users():
        manager = Manager()
        await manager.connect("app.db", alias="app")
        
        # Fetch all users
        all_users = await manager.execute("app", "SELECT * FROM users")
        print("All users:", all_users)
        
        # Fetch one user
        user = await manager.execute(
            "app",
            "SELECT * FROM users WHERE name = ?",
            params=("Alice",),
            return_type="fetchone"
        )
        print("User:", user[0] if user else None)
        
        await manager.shutdown()

    asyncio.run(query_users())

Advanced Type Conversion Examples
----------------------------------

Working with Boolean Flags
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async def handle_boolean_flags():
        manager = Manager()
        await manager.connect("app.db", alias="app")
        
        # Create table with TEXT columns for flags
        await manager.execute(
            "app",
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                enabled TEXT,
                value TEXT
            )""",
            commit=True
        )
        
        # Insert settings with string representations
        await manager.execute(
            "app",
            "INSERT INTO settings VALUES ('feature_x', '1', '100')",
            commit=True
        )
        
        # Query with custom type conversion
        result = await manager.execute(
            "app",
            "SELECT enabled, value FROM settings WHERE key = ?",
            params=("feature_x",),
            return_type="fetchone",
            expected_types=(bool, int)  # Convert enabled to bool, value to int
        )
        
        enabled, value = result[0]
        print(f"Feature X: enabled={enabled} (type: {type(enabled).__name__}), "
              f"value={value} (type: {type(value).__name__})")
        # Output: Feature X: enabled=True (type: bool), value=100 (type: int)
        
        await manager.shutdown()

    asyncio.run(handle_boolean_flags())

Preventing Unwanted Conversions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async def prevent_conversion():
        manager = Manager()
        await manager.connect("app.db", alias="app")
        
        # Create table for products
        await manager.execute(
            "app",
            """CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                sku TEXT,
                name TEXT,
                quantity INTEGER
            )""",
            commit=True
        )
        
        # Insert product with numeric SKU
        await manager.execute(
            "app",
            "INSERT INTO products VALUES (1, '12345', 'Widget', 100)",
            commit=True
        )
        
        # Query WITHOUT type conversion for SKU (it should remain a string)
        result = await manager.execute(
            "app",
            "SELECT sku, name, quantity FROM products WHERE id = 1",
            return_type="fetchone",
            expected_types=(None, None, int)  # Skip SKU and name, convert quantity
        )
        
        sku, name, quantity = result[0]
        print(f"Product: SKU={sku} (type: {type(sku).__name__}), "
              f"name={name}, quantity={quantity} (type: {type(quantity).__name__})")
        # Output: Product: SKU=12345 (type: str), name=Widget, quantity=100 (type: int)
        
        await manager.shutdown()

    asyncio.run(prevent_conversion())

Transaction Examples
--------------------

Basic Transaction
~~~~~~~~~~~~~~~~~

.. code-block:: python

    async def basic_transaction():
        manager = Manager()
        await manager.connect("app.db", alias="app")
        
        # Transaction with auto-commit
        async with manager.Transaction("app", autocommit=True) as txn:
            await txn.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                params=("David", "david@example.com")
            )
            await txn.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                params=("Eve", "eve@example.com")
            )
        # Automatically committed
        
        await manager.shutdown()

    asyncio.run(basic_transaction())

Transaction with Status Checking
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async def transaction_with_status():
        manager = Manager()
        await manager.connect("app.db", alias="app")
        
        # Successful transaction
        async with manager.Transaction("app", autocommit=True) as txn:
            await txn.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                params=("Frank", "frank@example.com")
            )
        
        if txn.succeeded:
            print("✓ Transaction committed successfully")
            # Log to audit table
            await manager.execute(
                "app",
                "INSERT INTO audit_log VALUES (?, ?)",
                params=("user_created", "Frank"),
                commit=True
            )
        
        # Failed transaction
        txn2 = manager.Transaction("app", autocommit=True)
        try:
            async with txn2:
                await txn2.execute(
                    "INSERT INTO users (name, email) VALUES (?, ?)",
                    params=("Grace", "grace@example.com")
                )
                # Simulate an error
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        if txn2.failed:
            print("✗ Transaction rolled back due to error")
            # Send alert
            print("Alert: Transaction failed for user Grace")
        
        await manager.shutdown()

    asyncio.run(transaction_with_status())

Transaction with Custom Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async def transaction_custom_types():
        manager = Manager()
        await manager.connect("app.db", alias="app")
        
        async with manager.Transaction("app", autocommit=True) as txn:
            # Query with custom type conversion within transaction
            result = await txn.execute(
                "SELECT enabled, priority FROM settings",
                expected_types=(bool, int)
            )
            
            for enabled, priority in result:
                if enabled and priority > 5:
                    print(f"High priority setting: {priority}")
        
        await manager.shutdown()

    asyncio.run(transaction_custom_types())

Multiple Databases
------------------

Working with Multiple Databases
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async def multiple_databases():
        manager = Manager()
        
        # Connect to multiple databases
        await manager.connect("users.db", alias="users")
        await manager.connect("products.db", alias="products")
        await manager.connect("orders.db", alias="orders")
        
        # Query from different databases
        users = await manager.execute("users", "SELECT * FROM users")
        products = await manager.execute("products", "SELECT * FROM products")
        
        # Create an order using data from multiple databases
        async with manager.Transaction("orders", autocommit=True) as txn:
            for user in users[:5]:  # First 5 users
                for product in products[:3]:  # First 3 products
                    await txn.execute(
                        "INSERT INTO orders (user_id, product_id) VALUES (?, ?)",
                        params=(user[0], product[0])
                    )
        
        if txn.succeeded:
            print(f"Created orders for {len(users[:5])} users")
        
        await manager.shutdown()

    asyncio.run(multiple_databases())

Read/Write Separation
---------------------

Using Separate Read Connections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    async def read_write_separation():
        manager = Manager()
        
        # Connect with separate read connection
        await manager.connect("app.db", alias="app", create_read_connection=True)
        
        # Write operation (uses write connection)
        await manager.execute(
            "app",
            "INSERT INTO users (name, email) VALUES (?, ?)",
            params=("Henry", "henry@example.com"),
            commit=True,
            mode="write"
        )
        
        # Read operations (use read connection for better concurrency)
        users = await manager.execute(
            "app",
            "SELECT * FROM users",
            mode="read"
        )
        
        count = await manager.execute(
            "app",
            "SELECT COUNT(*) FROM users",
            return_type="fetchone",
            mode="read"
        )
        
        print(f"Total users: {count[0][0]}")
        
        await manager.shutdown()

    asyncio.run(read_write_separation())
