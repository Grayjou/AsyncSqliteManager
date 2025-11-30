import aiosqlite
from aiosqlite import Cursor
from typing import Optional, List, Any, Union
import logging
from ..utils import is_depth_at_least
from .fetch_types import ReturnType, FetchMany, normalize_return_type


def question_to_dollar(query: str) -> str:
    """
    Convert SQL positional placeholders from "?" to PostgreSQL-style "$n".
    This function scans the input SQL string for "?" characters and reconstructs
    the query by numbering each placeholder in order of appearance starting from 1
    (i.e., ?, ?, ? -> $1, $2, $3).
    Args:
        query (str): A SQL query string that may contain "?" placeholders.
    Returns:
        str: The transformed SQL string with placeholders numbered as "$1", "$2", etc.
             If the input contains no "?" characters, this implementation returns an
             empty string.
    Notes:
        - This implementation naively splits on "?" and does not account for
          question marks inside string literals or comments.
        - When multiple placeholders are present, the initial segment before the
          first "?" is prepended for each occurrence due to the current construction.
          This can lead to repeated prefixes in the output (see example below).
    Examples:
        Single placeholder:
            >>> question_to_dollar("INSERT INTO t(a) VALUES (?)")
            'INSERT INTO t(a) VALUES ($1)'
        Multiple placeholders (note repeated prefix in output):
            >>> question_to_dollar("SELECT * FROM t WHERE a = ? AND b = ?")
            'SELECT * FROM t WHERE a = $1 AND b = SELECT * FROM t WHERE a = $2'
        No placeholders:
            >>> question_to_dollar("SELECT 1")
            ''
    """

    parts = query.split("?")
    return "".join(parts[0] + f"${i}" + parts[i] for i in range(1, len(parts)))

# === Async Execution ===

async def _execute_with_params(cursor: Cursor, query: str, injection_values, log: bool, notify_bulk: bool, force_notify_bulk: bool= False,
                               logger: logging.Logger = logging.getLogger(__name__)):
    """
    Executes a SQL query with the provided parameters, supporting both single and bulk operations.
    Args:
        cursor (Cursor): The database cursor to execute the query with.
        query (str): The SQL query to execute.
        injection_values: The values to inject into the query. Can be a single set of parameters or a list of parameter sets for bulk operations.
        log (bool): Whether to log the execution of the query.
        notify_bulk (bool): Whether to notify when a bulk operation is performed.
        force_notify_bulk (bool, optional): If True, forces notification of bulk operation regardless of other flags. Defaults to False.
        logger (logging.Logger, optional): Logger instance to use for logging. Defaults to a logger named after the current module.
    Returns:
        None
    Notes:
        - If `injection_values` is a sequence of sequences (depth >= 2), a bulk operation is performed using `executemany`.
        - Logs information about bulk operations if `notify_bulk` and `log` are True, or if `force_notify_bulk` is True.
    """    
    is_bulk = is_depth_at_least(injection_values, 2)
    if is_bulk:
        if (notify_bulk and log) or force_notify_bulk:
            logger.info(f"Executing bulk operation with {len(injection_values)} records.")
        await cursor.executemany(query, injection_values)
    else:
        await cursor.execute(query, injection_values)

async def _fetch_results(cursor: Cursor, return_type: ReturnType, 
    logger: logging.Logger = logging.getLogger(__name__)
                         ) -> Optional[List[Any]]:
    """
    Fetch rows from an asynchronous database cursor according to the specified return type.
    This coroutine normalizes fetch results to a list:
    - "fetchone": awaits cursor.fetchone() and returns [row] or [] if no row exists.
    - "fetchall": awaits cursor.fetchall() and returns the full list of rows.
    - FetchMany(n): awaits cursor.fetchmany(n) and returns up to n rows.
    If an unsupported return_type is provided, an error is logged and None is returned.
    Args:
        cursor (Cursor): An async database cursor implementing fetchone, fetchall, and fetchmany.
        return_type (ReturnType): Selector indicating which fetch method to use. Accepted values are
            "fetchone", "fetchall", or an instance of FetchMany with attribute 'n'.
        logger (logging.Logger, optional): Logger used to report unsupported return types. Defaults to
            a module-level logger.
    Returns:
        Optional[List[Any]]: A list of fetched rows. For "fetchone", returns [row] or [] if no row is
        available. For "fetchall" and FetchMany, returns the rows as provided by the cursor. Returns
        None if the return_type is unsupported.
    Raises:
        Exception: Propagates any exceptions raised by the underlying cursor fetch methods.
    """

    
    if return_type.type == "fetchone":
        result = await cursor.fetchone()
        return [result] if result else []
    elif return_type.type == "fetchall":
        result = await cursor.fetchall()
        return result  # type: ignore
    elif isinstance(return_type, FetchMany):
        result = await cursor.fetchmany(return_type.n)
        return result # type: ignore
    logger.error("Unsupported return_type encountered.")
    return None

async def try_query(
    cursor: Cursor,
    query: str,
    commit: bool = False,
    injection_values: Optional[Union[tuple, List[tuple]]] = None,
    error_message: Optional[str] = None,
    return_type: Union[str, int, ReturnType] = "fetchall",
    log: bool = False,
    raise_on_fail: bool = False,
    *,
    notify_bulk=False,
    force_notify_bulk=False,
    convert_to_dollar=False,
    logger = logging.getLogger(__name__),
    **kwargs
) -> Optional[List[Any]]:

    """
    Execute a SQLite query asynchronously with comprehensive error handling and flexible return options.
    Args:
        cursor (Cursor): The aiosqlite cursor object to execute the query.
        query (str): The SQL query string to execute.
        commit (bool, optional): Whether to commit the transaction after execution. Defaults to False.
        injection_values (Optional[Union[tuple, List[tuple]]], optional): Parameter values for parameterized queries.
            Can be a single tuple for one execution or a list of tuples for executemany. Defaults to None.
        error_message (Optional[str], optional): Custom error message to log on failure. Defaults to None.
        return_type (Union[str, int, ReturnType], optional): Specifies how to return results.
            Options: "fetchall", "fetchone", "fetchmany", or ReturnType enum. Defaults to "fetchall".
        log (bool, optional): Whether to log the query execution details. Defaults to False.
        raise_on_fail (bool, optional): Whether to re-raise exceptions after logging. Defaults to False.
        notify_bulk (bool, optional): Enable bulk operation notifications. Defaults to False.
        force_notify_bulk (bool, optional): Force bulk operation notifications regardless of other settings. Defaults to False.
        convert_to_dollar (bool, optional): Convert query placeholders from '?' to '$' notation. Defaults to False.
        logger (logging.Logger, optional): Logger instance for logging operations. Defaults to module logger.
        **kwargs: Additional keyword arguments (currently unused, reserved for future extensions).
    Returns:
        Optional[List[Any]]: Query results based on return_type specification, or None if an error occurred
            and raise_on_fail is False.
    Raises:
        aiosqlite.Error: If a SQLite-specific error occurs and raise_on_fail is True.
        Exception: If any other exception occurs and raise_on_fail is True.
    Examples:
        >>> results = await try_query(cursor, "SELECT * FROM users", return_type="fetchall")
        >>> user = await try_query(cursor, "SELECT * FROM users WHERE id = ?", 
        ...                        injection_values=(1,), return_type="fetchone")
        >>> await try_query(cursor, "INSERT INTO users VALUES (?, ?)",
        ...                injection_values=[(1, "Alice"), (2, "Bob")], commit=True)
    """


    if convert_to_dollar:
        query = question_to_dollar(query)
    if log:
        logger.info(f"Executing query: {query} | Params: {injection_values or 'None'}")

    try:
        rt = normalize_return_type(return_type)

        if injection_values is not None:
            await _execute_with_params(cursor, query, injection_values, log, notify_bulk, force_notify_bulk)
        else:
            await cursor.execute(query)

        if commit:
            await cursor.connection.commit() # type: ignore

        return await _fetch_results(cursor, rt)

    except aiosqlite.Error as db_error:
        logger.error(f"SQLite error during query: {db_error}")
        if raise_on_fail:
            raise
    except Exception as e:
        logger.error(f"{error_message or 'Error executing query'}: {e}")
        if raise_on_fail:
            raise

    return None
