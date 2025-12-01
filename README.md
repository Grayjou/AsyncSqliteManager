# AsyncSqliteManager

An async SQLite database connection manager for Python, built on top of `aiosqlite`. Provides a high-level API for managing multiple database connections, transactions, and query history.

## Features

- **Async/Await Support**: Built on `aiosqlite` for non-blocking database operations
- **Multiple Database Connections**: Manage connections to multiple SQLite databases simultaneously
- **Read/Write Connection Separation**: Support for separate read and write connections for improved concurrency
- **Path Aliases**: Reference databases using custom aliases instead of full paths
- **Transaction Management**: Context managers for safe transaction handling with automatic commit/rollback
- **Query History**: Track query execution history with optional file dumping
- **Autocommit Mode**: Optional automatic commit after each query
- **Logging Integration**: Built-in logging support for query tracking

## Installation

```bash
pip install aiosqlite aiofiles
```

## Quick Start

```python
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
    
    # Use transactions
    async with manager.Transaction("mydb") as txn:
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Bob",))
        await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Charlie",))
    
    # Shutdown gracefully
    await manager.shutdown()

asyncio.run(main())
```

## API Reference

### Manager

The main entry point for database operations.

```python
from manager import Manager

manager = Manager(
    autocommit=False,          # Auto-commit after each query
    omni_log=False,            # Log all queries
    history_length=10,         # Maximum history entries to keep
    log_results=True,          # Include results in history
    logger=None,               # Custom logger instance
    history_tolerance=5,       # Tolerance for history overflow
)
```

### Connection Management

#### connect()

Connect to a SQLite database.

```python
# Basic connection
conn = await manager.connect("path/to/database.db")

# With alias
conn = await manager.connect("path/to/database.db", alias="mydb")

# With separate read connection (for improved concurrency)
conn = await manager.connect("path/to/database.db", create_read_connection=True)
```

#### get_connection()

Get an existing connection by path or alias.

```python
# Get write connection (default)
write_conn = manager.get_connection("mydb")
write_conn = manager.get_connection("mydb", mode="write")

# Get read connection (falls back to write if not available)
read_conn = manager.get_connection("mydb", mode="read")
```

#### get_path_connection()

Get the PathConnection object for a database.

```python
pc = manager.get_path_connection("mydb")
print(pc.path)       # Full path to database
print(pc.alias)      # Alias if set
print(pc.write_conn) # Write connection
print(pc.read_conn)  # Read connection (may be None)
print(pc.conn)       # Alias for write_conn (backwards compatible)
```

#### close() / disconnect()

Close a database connection.

```python
await manager.close("mydb")
# or
await manager.disconnect("mydb")
```

#### disconnect_all()

Close all open connections.

```python
await manager.disconnect_all()
```

### Query Execution

#### execute()

Execute a SQL query.

```python
# Simple query
result = await manager.execute("mydb", "SELECT * FROM users")

# With parameters
result = await manager.execute(
    "mydb",
    "INSERT INTO users (name, email) VALUES (?, ?)",
    params=("Alice", "alice@example.com"),
    commit=True
)

# Different return types
result = await manager.execute("mydb", "SELECT * FROM users", return_type="fetchone")
result = await manager.execute("mydb", "SELECT * FROM users", return_type="fetchall")
```

### Transaction Management

#### Transaction Context Manager

```python
async with manager.Transaction("mydb", autocommit=True) as txn:
    await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Alice",))
    await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Bob",))
    # Automatically commits on success, rolls back on exception
```

#### Safe Transaction (with locking)

```python
async with manager.safe_transaction("mydb") as txn:
    await txn.execute("INSERT INTO users (name) VALUES (?)", params=("Alice",))
    # Prevents concurrent access to the same database
```

#### Manual Transaction Control

```python
await manager.commit("mydb")
await manager.rollback("mydb")
```

#### Savepoints

```python
await manager.savepoint("mydb", "sp1")
await manager.execute("mydb", "INSERT INTO users (name) VALUES (?)", params=("Alice",))
await manager.rollback_to("mydb", "sp1")  # Undo changes since savepoint
await manager.release_savepoint("mydb", "sp1")  # Release savepoint
```

### PathConnection

Represents a connection to a database with optional separate read/write connections.

```python
from manager import PathConnection

# Create a PathConnection with both read and write connections
pc = PathConnection(
    path="database.db",
    write_conn=write_connection,
    read_conn=read_connection,  # Optional
    alias="mydb"                # Optional
)

# Get connection by mode
write_conn = pc.get_conn("write")  # Returns write_conn
read_conn = pc.get_conn("read")    # Returns read_conn or falls back to write_conn
default_conn = pc.get_conn()       # Defaults to write mode

# Backwards compatible property
conn = pc.conn  # Alias for write_conn
```

### DbPathDict

A dictionary-like structure for managing multiple PathConnection objects.

```python
from manager import DbPathDict, PathConnection

db_dict = DbPathDict()

# Add connection using path
db_dict["database.db"] = connection

# Add PathConnection directly
pc = PathConnection("database.db", write_conn, read_conn, alias="mydb")
db_dict["database.db"] = pc

# Access connections
pc = db_dict["database.db"]  # Returns PathConnection
pc = db_dict["mydb"]         # Access via alias

# Get connection by mode
conn = db_dict.get_connection("mydb", mode="read")
conn = db_dict.get_connection("mydb", mode="write")

# Set alias
db_dict.setalias("database.db", "newdb")

# Change path
db_dict.setpath("oldpath.db", "newpath.db")

# List all paths
paths = db_dict.paths
```

## Read/Write Connection Separation

For improved concurrency, you can create separate connections for read and write operations:

```python
# Connect with separate read connection
await manager.connect("database.db", create_read_connection=True)

# Get connections by mode
write_conn = manager.get_connection("database.db", mode="write")
read_conn = manager.get_connection("database.db", mode="read")

# Read operations can use the read connection
# Write operations should use the write connection
```

**Note**: When `read_conn` is not set, `get_connection(mode="read")` falls back to the write connection for backwards compatibility.

## History Management

Track query execution history:

```python
# Get current history length
length = manager.history_length

# Set history length (None to disable)
manager.history_length = 20

# Flush history to file
await manager.flush_history_to_file()
```

## Lifecycle Management

```python
# Graceful shutdown
await manager.shutdown()  # Disconnects all, flushes history
```

## Error Handling

The library defines custom exceptions:

```python
from manager import ConnectionError, TransactionError, HistoryError

try:
    await manager.connect("/nonexistent/path/db.sqlite")
except ConnectionError as e:
    print(f"Connection failed: {e}")
```

## License

MIT License