Changelog
=========

Version 1.0.0
-------------

**New Features**

* **Customizable Type Conversion**: Added `expected_types` parameter to `execute()` and `Transaction.execute()` methods

  * Specify exact types for each column with a tuple of types
  * Use `None` in the tuple to skip conversion for specific columns
  * Support for shorter tuples (remaining columns use automatic conversion)
  * Early escape optimization when no types are provided
  * Special handling for `bool` type conversion from various string representations

* **Transaction Status Properties**: Added `succeeded` and `failed` properties to `Transaction` class

  * Track transaction outcome after context exit
  * Use for follow-up logic based on commit/rollback status
  * Properties are `None` during transaction, set to appropriate boolean after exit

**Improvements**

* Enhanced type conversion flexibility to prevent unwanted conversions
* Better support for applications that prefer to handle type conversion themselves
* Improved documentation with Sphinx

**Bug Fixes**

* Fixed row factory handling for transaction cursors
* Ensured type conversion works correctly in all scenarios

**Breaking Changes**

* None

**Migration Guide**

This version is backward compatible. No changes are required to existing code. To use the new features:

.. code-block:: python

    # Old way (still works)
    result = await manager.execute("mydb", "SELECT * FROM users")
    
    # New way with custom type conversion
    result = await manager.execute(
        "mydb",
        "SELECT active, count FROM users",
        expected_types=(bool, int)
    )
    
    # Transaction status tracking
    async with manager.Transaction("mydb") as txn:
        await txn.execute("INSERT INTO users VALUES (?)", params=("Alice",))
    
    if txn.succeeded:
        print("Transaction was successful")
