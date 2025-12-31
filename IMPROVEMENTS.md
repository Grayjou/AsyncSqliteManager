# AsyncSqliteManager Improvements Document

This document identifies performance issues, code quality improvements, expansion paths, and database management enhancements for the AsyncSqliteManager library.

---

## Table of Contents

1. [Performance and Efficiency Issues](#1-performance-and-efficiency-issues)
2. [Code Quality and Convention Improvements](#2-code-quality-and-convention-improvements)
3. [Expansion Paths and New Features](#3-expansion-paths-and-new-features)
4. [Database and Resource Management](#4-database-and-resource-management)
5. [Database Parallel Coordination](#5-database-parallel-coordination)

---

## 1. Performance and Efficiency Issues

### 1.1 Inefficient History Management

**Location:** `manager/history.py` (lines 63-75)

**Issue:** The `append` method flushes to file every time the history buffer is full. This creates unnecessary I/O overhead.

```python
async def append(self, item: HistoryItem) -> None:
    if not self.history or not self.history_dump_generator:
        return
    async with self._history_lock:
        dump = self.history_dump_generator.create(item)
        if isinstance(dump.data, dict):
            dump.data = self.history_format_function(dump.data)
        full = self.history.append(dump)
        if full:
            await self.flush_to_file()  # ← Synchronous I/O on every full buffer
```

**Recommendation:** Implement background flushing with a dedicated asyncio task or use batched writes with a time-based trigger:

```python
async def append(self, item: HistoryItem) -> None:
    if not self.history or not self.history_dump_generator:
        return
    async with self._history_lock:
        dump = self.history_dump_generator.create(item)
        if isinstance(dump.data, dict):
            dump.data = self.history_format_function(dump.data)
        full = self.history.append(dump)
        if full:
            # Schedule background flush instead of blocking
            asyncio.create_task(self._background_flush())
```

### 1.2 Cursor Creation Overhead in `execute()`

**Location:** `manager/manager_base.py` (lines 256-270)

**Issue:** A new cursor is created and closed for every single query when no cursor is provided. This adds overhead for bulk operations.

```python
async with conn.cursor() as new_cursor:
    result = await try_query(...)
```

**Recommendation:** Implement cursor pooling or allow cursor reuse within the same connection context:

```python
# Add cursor caching per connection
self._cursor_cache: Dict[str, AioCursor] = {}

def _get_cached_cursor(self, db_path: str, conn: AioConnection) -> AioCursor:
    if db_path not in self._cursor_cache:
        self._cursor_cache[db_path] = await conn.cursor()
    return self._cursor_cache[db_path]
```

### 1.3 Redundant Connection Lookups

**Location:** `manager/manager_base.py`

**Issue:** The `execute` method calls `connect()` which performs dictionary lookups even when a connection exists. For high-frequency operations, this adds latency.

**Recommendation:** Add a fast-path check:

```python
async def execute(self, db_path: str, query: str, ...):
    # Fast path: check if connection exists first
    conn = self.get_connection(db_path, mode=mode)
    if conn is None:
        conn = await self.connect(db_path, mode=mode, ...)
```

### 1.4 Inefficient Depth Check in `is_depth_at_least()`

**Location:** `utils.py` (lines 39-56)

**Issue:** The function uses recursion without memoization and can be slow for deeply nested structures.

```python
def is_depth_at_least(obj, max_depth, current_depth=0) -> bool:
    if current_depth >= max_depth:
        return True
    if isinstance(obj, (list, tuple, set)):
        for item in obj:
            if is_depth_at_least(item, max_depth, current_depth + 1):
                return True
    return False
```

**Recommendation:** Add early termination optimization:

```python
def is_depth_at_least(obj, target_depth: int, current_depth: int = 0) -> bool:
    """Optimized depth check with early termination."""
    if current_depth >= target_depth:
        return True
    if not isinstance(obj, (list, tuple, set)) or not obj:
        return False
    # Check only first element for performance if homogeneous
    return is_depth_at_least(next(iter(obj)), target_depth, current_depth + 1)
```

### 1.5 JSON Writer Batch Writes Individual Items

**Location:** `async_history_dump/writers.py` (lines 118-134)

**Issue:** `JSONWriter.write_batch` writes items one at a time, defeating the purpose of batching:

```python
async def write_batch(self, ...):
    for item in data_list:
        await self.write_single(...)  # ← Each item triggers read + write
```

**Recommendation:** Accumulate all changes in memory first, then write once:

```python
async def write_batch(self, path, data_list, mode, key, strict_keys):
    existing = await self._read_json(path, key)
    for item in data_list:
        # Apply changes in memory
        existing = self._apply_item(existing, item, mode, key, strict_keys)
    # Single write operation
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(existing, indent=2))
```

---

## 2. Code Quality and Convention Improvements

### 2.1 Missing Type Annotations

**Locations:** Multiple files

**Issue:** Several functions lack complete type annotations, reducing code clarity and IDE support.

**Examples:**
- `execution_async.py:44` - `injection_values` parameter lacks type hint
- `cloggable_list.py:141` - `append` return type should be `Optional[Full]`
- `log.py:46` - `params` parameter needs proper type hint

**Recommendation:** Add comprehensive type hints using `typing` module:

```python
# Before
async def _execute_with_params(cursor, query, injection_values, log, notify_bulk, ...):

# After
async def _execute_with_params(
    cursor: Cursor,
    query: str,
    injection_values: Union[tuple, List[tuple]],
    log: bool,
    notify_bulk: bool,
    force_notify_bulk: bool = False,
    logger: logging.Logger = logging.getLogger(__name__)
) -> None:
```

### 2.2 SQL Injection Vulnerability in Savepoint Methods

**Location:** `manager/manager_base.py` (lines 337-358)

**Issue:** Savepoint names are directly interpolated into SQL strings without validation:

```python
async def savepoint(self, db_path: str, name: str) -> None:
    await conn.execute(f"SAVEPOINT {name}")  # ← SQL Injection risk!

async def rollback_to(self, db_path: str, name: str) -> None:
    await conn.execute(f"ROLLBACK TO {name}")  # ← SQL Injection risk!
```

**Recommendation:** Validate and sanitize savepoint names:

```python
import re

VALID_SAVEPOINT_NAME = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

def _validate_savepoint_name(self, name: str) -> None:
    """Validate savepoint name to prevent SQL injection."""
    if not VALID_SAVEPOINT_NAME.match(name):
        raise ValueError(f"Invalid savepoint name: {name}. Must be alphanumeric with underscores.")

async def savepoint(self, db_path: str, name: str) -> None:
    self._validate_savepoint_name(name)
    conn = self.get_connection(db_path)
    if conn is None:
        return
    await conn.execute(f"SAVEPOINT {name}")
```

### 2.3 Inconsistent Error Handling

**Location:** Multiple files

**Issue:** Some methods silently return `None` on error, while others raise exceptions. This inconsistency makes debugging difficult.

**Example in `manager_base.py`:**
```python
async def commit(self, db_path: str, ...):
    conn = self.get_connection(db_path)
    if conn is None:
        return  # ← Silent failure
```

**Recommendation:** Add consistent error handling with optional strict mode:

```python
async def commit(self, db_path: str, *, strict: bool = False, ...) -> bool:
    """Commit the current transaction.
    
    Args:
        strict: If True, raises ConnectionError when no connection exists.
        
    Returns:
        True if commit succeeded, False if no connection.
        
    Raises:
        ConnectionError: If strict=True and no connection exists.
    """
    conn = self.get_connection(db_path)
    if conn is None:
        if strict:
            raise ConnectionError(f"No connection for {db_path}")
        return False
    await conn.commit()
    return True
```

### 2.4 Missing Docstrings

**Locations:** Multiple private methods

**Issue:** Many private methods lack docstrings, making maintenance difficult.

**Recommendation:** Add docstrings following Google-style conventions:

```python
def _should_commit(self, commit: bool, override_autocommit: bool = False, 
                   mode: Literal["read", "write"] = "write") -> bool:
    """Determine whether to commit the transaction.
    
    Args:
        commit: Explicit commit flag from caller.
        override_autocommit: If True, ignores autocommit setting.
        mode: Connection mode; commits only occur on "write" mode.
        
    Returns:
        True if transaction should be committed.
    """
    return (commit or (self.autocommit and not override_autocommit)) and mode == "write"
```

### 2.5 Magic Numbers and Strings

**Location:** Multiple files

**Issue:** Hard-coded values without named constants:

```python
# execution_async.py
if arg in ("one", "fetchone"): return FetchOne()
if arg in ("all", "fetchall"): return FetchAll()

# async_history_dump.py
filetypes = {"json", "csv", "txt"}
modes = {"overwrite", "append", "update", "extend"}
```

**Recommendation:** Use enums or constants:

```python
from enum import Enum

class FetchType(str, Enum):
    ONE = "fetchone"
    ALL = "fetchall"
    MANY = "fetchmany"

class WriteMode(str, Enum):
    OVERWRITE = "overwrite"
    APPEND = "append"
    UPDATE = "update"
    EXTEND = "extend"
```

### 2.6 Decorator Order Issue

**Location:** `cloggable_list.py` (lines 139-142)

**Issue:** Decorator order matters and current order may cause issues:

```python
@proceed_if_tolerable
@return_full
def append(self, object) -> Optional[Full]:
    super().append(object)
```

**Recommendation:** The order is correct but should be documented. Add a comment explaining the decorator chain:

```python
# Decorators execute bottom-up: 
# 1. return_full wraps the actual append
# 2. proceed_if_tolerable checks tolerance before calling return_full
@proceed_if_tolerable
@return_full
def append(self, item: Any) -> Optional[Full]:
    """Append item if within tolerance, return Full if buffer is full."""
    super().append(item)
```

---

## 3. Expansion Paths and New Features

### 3.1 Connection Pool Support

**Feature:** Add connection pooling for better resource management in high-throughput scenarios.

```python
from dataclasses import dataclass
from typing import Optional
import asyncio

@dataclass
class PoolConfig:
    min_connections: int = 1
    max_connections: int = 10
    max_idle_time: float = 300.0  # seconds
    
class ConnectionPool:
    """Async connection pool for SQLite databases."""
    
    def __init__(self, db_path: str, config: PoolConfig):
        self.db_path = db_path
        self.config = config
        self._available: asyncio.Queue[AioConnection] = asyncio.Queue()
        self._in_use: set[AioConnection] = set()
        self._lock = asyncio.Lock()
        
    async def acquire(self) -> AioConnection:
        """Acquire a connection from the pool."""
        async with self._lock:
            if not self._available.empty():
                conn = await self._available.get()
            elif len(self._in_use) < self.config.max_connections:
                conn = await aiosqlite.connect(self.db_path)
            else:
                conn = await self._available.get()  # Wait for available
            self._in_use.add(conn)
            return conn
            
    async def release(self, conn: AioConnection) -> None:
        """Release a connection back to the pool."""
        async with self._lock:
            self._in_use.discard(conn)
            await self._available.put(conn)
```

### 3.2 Query Builder

**Feature:** Add a fluent query builder for type-safe query construction:

```python
class QueryBuilder:
    """Fluent SQL query builder with parameterized queries."""
    
    def __init__(self, table: str):
        self._table = table
        self._select_cols: List[str] = []
        self._where_clauses: List[str] = []
        self._params: List[Any] = []
        self._order_by: Optional[str] = None
        self._limit: Optional[int] = None
        
    def select(self, *columns: str) -> "QueryBuilder":
        self._select_cols.extend(columns)
        return self
        
    def where(self, condition: str, *params: Any) -> "QueryBuilder":
        self._where_clauses.append(condition)
        self._params.extend(params)
        return self
        
    def order_by(self, column: str, desc: bool = False) -> "QueryBuilder":
        self._order_by = f"{column} {'DESC' if desc else 'ASC'}"
        return self
        
    def limit(self, n: int) -> "QueryBuilder":
        self._limit = n
        return self
        
    def build(self) -> Tuple[str, tuple]:
        cols = ", ".join(self._select_cols) or "*"
        query = f"SELECT {cols} FROM {self._table}"
        if self._where_clauses:
            query += f" WHERE {' AND '.join(self._where_clauses)}"
        if self._order_by:
            query += f" ORDER BY {self._order_by}"
        if self._limit:
            query += f" LIMIT {self._limit}"
        return query, tuple(self._params)

# Usage:
# query, params = QueryBuilder("users").select("id", "name").where("age > ?", 18).limit(10).build()
```

### 3.3 Migration Support

**Feature:** Add schema migration support:

```python
from dataclasses import dataclass
from typing import List, Callable, Awaitable

@dataclass
class Migration:
    version: int
    name: str
    up: Callable[[AioConnection], Awaitable[None]]
    down: Callable[[AioConnection], Awaitable[None]]

class MigrationManager:
    """Database migration manager."""
    
    def __init__(self, manager: Manager, db_path: str):
        self.manager = manager
        self.db_path = db_path
        self.migrations: List[Migration] = []
        
    async def init_migrations_table(self) -> None:
        await self.manager.execute(
            self.db_path,
            """CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            commit=True
        )
        
    async def get_current_version(self) -> int:
        result = await self.manager.execute(
            self.db_path,
            "SELECT MAX(version) FROM _migrations"
        )
        return result[0][0] or 0
        
    async def migrate(self, target_version: Optional[int] = None) -> None:
        current = await self.get_current_version()
        target = target_version or max(m.version for m in self.migrations)
        
        if current < target:
            for migration in self.migrations:
                if current < migration.version <= target:
                    async with self.manager.Transaction(self.db_path) as txn:
                        conn = self.manager.get_connection(self.db_path)
                        await migration.up(conn)
                        await txn.execute(
                            "INSERT INTO _migrations (version, name) VALUES (?, ?)",
                            (migration.version, migration.name)
                        )
```

### 3.4 Metrics and Monitoring

**Feature:** Add built-in metrics collection:

```python
from dataclasses import dataclass, field
from time import time
from typing import Dict

@dataclass
class QueryMetrics:
    total_queries: int = 0
    total_time_ms: float = 0.0
    queries_by_type: Dict[str, int] = field(default_factory=dict)
    slow_queries: List[Tuple[str, float]] = field(default_factory=list)
    slow_threshold_ms: float = 100.0
    
class MetricsCollector:
    """Collect query execution metrics."""
    
    def __init__(self, slow_threshold_ms: float = 100.0):
        self.metrics = QueryMetrics(slow_threshold_ms=slow_threshold_ms)
        self._lock = asyncio.Lock()
        
    async def record(self, query: str, execution_time_ms: float) -> None:
        async with self._lock:
            self.metrics.total_queries += 1
            self.metrics.total_time_ms += execution_time_ms
            
            query_type = query.strip().split()[0].upper()
            self.metrics.queries_by_type[query_type] = \
                self.metrics.queries_by_type.get(query_type, 0) + 1
                
            if execution_time_ms > self.metrics.slow_threshold_ms:
                self.metrics.slow_queries.append((query, execution_time_ms))
                
    def get_stats(self) -> Dict:
        return {
            "total_queries": self.metrics.total_queries,
            "avg_time_ms": self.metrics.total_time_ms / max(1, self.metrics.total_queries),
            "queries_by_type": self.metrics.queries_by_type,
            "slow_query_count": len(self.metrics.slow_queries)
        }
```

### 3.5 Retry Logic with Exponential Backoff

**Feature:** Add automatic retry for transient failures:

```python
import random
from functools import wraps

def with_retry(
    max_attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 10.0,
    exceptions: tuple = (Exception,)
):
    """Decorator for retry with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.1), max_delay)
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator
```

### 3.6 Context Manager for Batch Operations

**Feature:** Add dedicated batch operation context:

```python
class BatchContext:
    """Context manager for efficient batch operations."""
    
    def __init__(self, manager: Manager, db_path: str, batch_size: int = 1000):
        self.manager = manager
        self.db_path = db_path
        self.batch_size = batch_size
        self._buffer: List[Tuple[str, tuple]] = []
        
    async def __aenter__(self):
        self._conn = await self.manager.connect(self.db_path)
        self._cursor = await self._conn.cursor()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and self._buffer:
            await self._flush()
        await self._cursor.close()
        if exc_type is None:
            await self._conn.commit()
        else:
            await self._conn.rollback()
            
    async def add(self, query: str, params: tuple = ()) -> None:
        self._buffer.append((query, params))
        if len(self._buffer) >= self.batch_size:
            await self._flush()
            
    async def _flush(self) -> None:
        if not self._buffer:
            return
        for query, params in self._buffer:
            await self._cursor.execute(query, params)
        self._buffer.clear()

# Usage:
# async with manager.batch("mydb.db") as batch:
#     for item in items:
#         await batch.add("INSERT INTO items VALUES (?, ?)", (item.id, item.name))
```

---

## 4. Database and Resource Management

### 4.1 WAL Mode Support

**Feature:** Add Write-Ahead Logging mode for better concurrency:

```python
class WALModeManager:
    """Manage SQLite WAL mode settings."""
    
    @staticmethod
    async def enable_wal(conn: AioConnection) -> None:
        """Enable WAL mode for better concurrent read performance."""
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA wal_autocheckpoint=1000")
        
    @staticmethod
    async def optimize_for_read(conn: AioConnection) -> None:
        """Optimize connection for read-heavy workloads."""
        await conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        await conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap
        await conn.execute("PRAGMA temp_store=MEMORY")
        
    @staticmethod
    async def optimize_for_write(conn: AioConnection) -> None:
        """Optimize connection for write-heavy workloads."""
        await conn.execute("PRAGMA cache_size=-32000")  # 32MB cache
        await conn.execute("PRAGMA temp_store=MEMORY")
        await conn.execute("PRAGMA synchronous=NORMAL")
```

**Integration with Manager:**

```python
async def connect(
    self,
    db_path: str,
    alias: Optional[str] = None,
    *,
    create_read_connection: bool = False,
    mode: Literal["read", "write"] = "write",
    enable_wal: bool = False,  # New parameter
    optimize_for: Optional[Literal["read", "write"]] = None  # New parameter
) -> AioConnection:
    # ... existing code ...
    
    if enable_wal:
        await WALModeManager.enable_wal(write_conn)
        
    if optimize_for == "read":
        await WALModeManager.optimize_for_read(write_conn)
    elif optimize_for == "write":
        await WALModeManager.optimize_for_write(write_conn)
```

### 4.2 Connection Health Checks

**Feature:** Add periodic connection health monitoring:

```python
class ConnectionHealthChecker:
    """Monitor connection health and auto-reconnect."""
    
    def __init__(self, manager: Manager, check_interval: float = 30.0):
        self.manager = manager
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the health check loop."""
        self._running = True
        self._task = asyncio.create_task(self._health_check_loop())
        
    async def stop(self) -> None:
        """Stop the health check loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
    async def _health_check_loop(self) -> None:
        while self._running:
            for db_path in list(self.manager.databases):
                try:
                    conn = self.manager.get_connection(db_path)
                    if conn:
                        await conn.execute("SELECT 1")
                except Exception as e:
                    self.manager.logger.warning(f"Health check failed for {db_path}: {e}")
                    # Attempt reconnect
                    try:
                        await self.manager.close(db_path)
                        await self.manager.connect(db_path)
                    except Exception as reconnect_error:
                        self.manager.logger.error(f"Reconnect failed: {reconnect_error}")
            await asyncio.sleep(self.check_interval)
```

### 4.3 Resource Cleanup with Context Manager

**Feature:** Ensure proper cleanup with an enhanced context manager:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_database(manager: Manager, db_path: str, **connect_kwargs):
    """Context manager that ensures proper database cleanup."""
    conn = await manager.connect(db_path, **connect_kwargs)
    try:
        yield conn
    except Exception:
        await manager.rollback(db_path)
        raise
    finally:
        await manager.close(db_path)

# Usage:
# async with managed_database(manager, "temp.db") as conn:
#     await manager.execute("temp.db", "SELECT 1")
```

### 4.4 Memory-Mapped I/O Settings

**Feature:** Add mmap configuration for large databases:

```python
async def configure_mmap(conn: AioConnection, mmap_size_mb: int = 256) -> None:
    """Configure memory-mapped I/O for better read performance.
    
    Args:
        conn: Database connection
        mmap_size_mb: Memory map size in megabytes (0 to disable)
    """
    mmap_bytes = mmap_size_mb * 1024 * 1024
    await conn.execute(f"PRAGMA mmap_size={mmap_bytes}")
```

### 4.5 Database Vacuum and Optimization

**Feature:** Add database maintenance utilities:

```python
class DatabaseMaintenance:
    """Database maintenance utilities."""
    
    @staticmethod
    async def vacuum(manager: Manager, db_path: str) -> None:
        """Rebuild database to reclaim space and defragment."""
        await manager.execute(db_path, "VACUUM", commit=True)
        
    @staticmethod
    async def analyze(manager: Manager, db_path: str) -> None:
        """Update statistics for query optimizer."""
        await manager.execute(db_path, "ANALYZE", commit=True)
        
    @staticmethod
    async def integrity_check(manager: Manager, db_path: str) -> List[str]:
        """Check database integrity."""
        result = await manager.execute(db_path, "PRAGMA integrity_check")
        return [row[0] for row in result]
        
    @staticmethod
    async def get_db_size(manager: Manager, db_path: str) -> Dict[str, int]:
        """Get database size statistics."""
        page_count = await manager.execute(db_path, "PRAGMA page_count")
        page_size = await manager.execute(db_path, "PRAGMA page_size")
        freelist = await manager.execute(db_path, "PRAGMA freelist_count")
        
        return {
            "total_pages": page_count[0][0],
            "page_size_bytes": page_size[0][0],
            "total_bytes": page_count[0][0] * page_size[0][0],
            "free_pages": freelist[0][0],
            "free_bytes": freelist[0][0] * page_size[0][0]
        }
```

---

## 5. Database Parallel Coordination

### 5.1 Reader-Writer Lock Pattern

**Feature:** Implement proper reader-writer lock for concurrent access:

```python
class ReadWriteLock:
    """Async reader-writer lock allowing multiple readers or single writer."""
    
    def __init__(self):
        self._read_count = 0
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._no_readers = asyncio.Event()
        self._no_readers.set()
        
    @asynccontextmanager
    async def read_lock(self):
        """Acquire read lock (multiple readers allowed)."""
        async with self._read_lock:
            self._read_count += 1
            if self._read_count == 1:
                await self._write_lock.acquire()
                self._no_readers.clear()
        try:
            yield
        finally:
            async with self._read_lock:
                self._read_count -= 1
                if self._read_count == 0:
                    self._write_lock.release()
                    self._no_readers.set()
                    
    @asynccontextmanager
    async def write_lock(self):
        """Acquire write lock (exclusive access)."""
        await self._no_readers.wait()
        async with self._write_lock:
            yield
```

### 5.2 Connection Semaphore for Rate Limiting

**Feature:** Add semaphore-based rate limiting:

```python
class RateLimitedManager:
    """Rate-limited wrapper for Manager operations."""
    
    def __init__(self, manager: Manager, max_concurrent: int = 10):
        self.manager = manager
        self._semaphore = asyncio.Semaphore(max_concurrent)
        
    async def execute(self, *args, **kwargs):
        async with self._semaphore:
            return await self.manager.execute(*args, **kwargs)
```

### 5.3 Distributed Lock Manager (for multi-process scenarios)

**Feature:** Add file-based locking for multi-process coordination:

```python
import fcntl
import os

class FileLock:
    """File-based lock for multi-process coordination."""
    
    def __init__(self, db_path: str):
        self.lock_path = f"{db_path}.lock"
        self._fd: Optional[int] = None
        
    async def acquire(self) -> None:
        """Acquire the file lock."""
        loop = asyncio.get_event_loop()
        self._fd = await loop.run_in_executor(
            None, lambda: os.open(self.lock_path, os.O_CREAT | os.O_RDWR)
        )
        await loop.run_in_executor(None, lambda: fcntl.flock(self._fd, fcntl.LOCK_EX))
        
    async def release(self) -> None:
        """Release the file lock."""
        if self._fd is not None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: fcntl.flock(self._fd, fcntl.LOCK_UN))
            await loop.run_in_executor(None, lambda: os.close(self._fd))
            self._fd = None
            
    async def __aenter__(self):
        await self.acquire()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
```

### 5.4 Queue-Based Write Coordination

**Feature:** Add write queue for serializing writes across connections:

```python
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

@dataclass
class WriteTask:
    query: str
    params: tuple
    future: asyncio.Future
    
class WriteQueue:
    """Queue for serializing write operations."""
    
    def __init__(self, manager: Manager, db_path: str):
        self.manager = manager
        self.db_path = db_path
        self._queue: asyncio.Queue[WriteTask] = asyncio.Queue()
        self._running = False
        self._worker: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the write worker."""
        self._running = True
        self._worker = asyncio.create_task(self._process_writes())
        
    async def stop(self) -> None:
        """Stop the write worker."""
        self._running = False
        await self._queue.put(None)  # Sentinel to stop worker
        if self._worker:
            await self._worker
            
    async def write(self, query: str, params: tuple = ()) -> Any:
        """Queue a write operation and wait for result."""
        future = asyncio.get_event_loop().create_future()
        await self._queue.put(WriteTask(query, params, future))
        return await future
        
    async def _process_writes(self) -> None:
        """Process write tasks from the queue."""
        while self._running:
            task = await self._queue.get()
            if task is None:
                break
            try:
                result = await self.manager.execute(
                    self.db_path, task.query, params=task.params, commit=True
                )
                task.future.set_result(result)
            except Exception as e:
                task.future.set_exception(e)
```

### 5.5 Optimistic Locking Support

**Feature:** Add version-based optimistic locking:

```python
class OptimisticLock:
    """Optimistic locking for concurrent updates."""
    
    def __init__(self, manager: Manager, db_path: str, table: str, version_column: str = "version"):
        self.manager = manager
        self.db_path = db_path
        self.table = table
        self.version_column = version_column
        
    async def read_with_version(self, id_column: str, id_value: Any) -> Tuple[Any, int]:
        """Read a record with its version."""
        result = await self.manager.execute(
            self.db_path,
            f"SELECT *, {self.version_column} FROM {self.table} WHERE {id_column} = ?",
            params=(id_value,),
            return_type="fetchone"
        )
        if not result:
            raise ValueError(f"Record not found: {id_value}")
        return result[0][:-1], result[0][-1]  # Data without version, version
        
    async def update_with_version(
        self,
        id_column: str,
        id_value: Any,
        expected_version: int,
        update_clause: str,
        params: tuple
    ) -> bool:
        """Update a record only if version matches."""
        result = await self.manager.execute(
            self.db_path,
            f"""UPDATE {self.table} 
                SET {update_clause}, {self.version_column} = {self.version_column} + 1 
                WHERE {id_column} = ? AND {self.version_column} = ?""",
            params=(*params, id_value, expected_version),
            commit=True
        )
        # Check if update affected any rows
        cursor_result = await self.manager.execute(
            self.db_path, "SELECT changes()"
        )
        return cursor_result[0][0] > 0
```

### 5.6 Transaction Isolation Levels

**Feature:** Add support for different isolation levels:

```python
from enum import Enum

class IsolationLevel(str, Enum):
    DEFERRED = "DEFERRED"
    IMMEDIATE = "IMMEDIATE"
    EXCLUSIVE = "EXCLUSIVE"

class IsolatedTransaction(Transaction):
    """Transaction with configurable isolation level."""
    
    def __init__(
        self,
        database_path: str,
        isolation_level: IsolationLevel = IsolationLevel.DEFERRED,
        **kwargs
    ):
        super().__init__(database_path, **kwargs)
        self.isolation_level = isolation_level
        
    async def __aenter__(self):
        self._connection = await self.manager.connect(self.database_path)
        if self._connection is None:
            raise TransactionError(f"Failed to connect: {self.database_path}")
            
        self._cursor = await self._connection.cursor()
        
        try:
            await self._cursor.execute(f"BEGIN {self.isolation_level.value}")
        except Exception as e:
            await self._cursor.close()
            raise TransactionError(f"Failed to begin transaction: {e}") from e
            
        return self
```

---

## Implementation Priority

### High Priority (Security & Stability)
1. SQL Injection fix in savepoint methods (Section 2.2)
2. Consistent error handling (Section 2.3)
3. WAL mode support (Section 4.1)

### Medium Priority (Performance)
1. Background history flushing (Section 1.1)
2. Cursor caching (Section 1.2)
3. JSON writer batch optimization (Section 1.5)
4. Connection health checks (Section 4.2)

### Low Priority (Features)
1. Connection pooling (Section 3.1)
2. Query builder (Section 3.2)
3. Metrics collection (Section 3.4)
4. Migration support (Section 3.3)

---

## Conclusion

This document provides a comprehensive roadmap for improving the AsyncSqliteManager library. The suggestions range from critical security fixes to advanced features for enterprise use cases. Implementation should be prioritized based on the project's current needs and user requirements.
