
from typing import Optional, Union
from ..utils import no_underscore_or_space



# === ReturnType Classes ===

class ReturnType: 
    """Placeholder base class representing a standardized return type for asynchronous fetch operations.
    This class serves as an extension point for defining structured results returned
    by async database queries, such as success payloads, error details, or metadata.
    Subclass this to create specific, typed return models (e.g., rows, counts, status),
    and document their fields clearly for consistent usage across the codebase.
    """
    type: str


class FetchOne(ReturnType):
    def __init__(self): self.type = "fetchone"
    def __repr__(self): return "FetchOne()"
    def to_string(self) -> str: return self.type
    def __eq__(self, value): return isinstance(value, FetchOne)
    def __hash__(self): return hash(self.type)

class FetchAll(ReturnType):
    def __init__(self): self.type = "fetchall"
    def __repr__(self): return "FetchAll()"
    def to_string(self) -> str: return self.type
    def __eq__(self, value): return isinstance(value, FetchAll)
    def __hash__(self): return hash(self.type)

class FetchMany(ReturnType):
    def __init__(self, n: Optional[int] = None):
        if n is None or n < 1:
            raise ValueError("FetchMany requires a positive integer n >= 1.")
        self.n = n
        self.type = "fetchmany"
    def __repr__(self): return f"FetchMany(n={self.n})"
    def to_string(self) -> str: return f"{self.type} ({self.n})"
    def __eq__(self, value): return isinstance(value, FetchMany) and self.n == value.n
    def __hash__(self): return hash((self.type, self.n))

# === Utility Functions ===

def _fetch_num_arg(arg) -> Union[FetchOne, FetchMany]:
    if arg < 1:
        raise ValueError(f"Invalid integer argument for Fetch: {arg}")
    return FetchOne() if arg == 1 else FetchMany(arg)

def Fetch(arg: Optional[Union[str, int, ReturnType]] = None) -> ReturnType:
    """
    Determines the fetch strategy for database queries based on the provided argument.
    Args:
        arg (Optional[Union[str, int, ReturnType]]): The fetch type specifier. Can be:
            - None: Returns a FetchAll instance.
            - str: Specifies fetch type ("one", "fetchone", "all", "fetchall") or a number as string.
            - int: Specifies the number of rows to fetch.
            - ReturnType: Returns the provided ReturnType instance.
    Returns:
        ReturnType: An instance representing the fetch strategy (e.g., FetchOne, FetchAll, or a custom number of rows).
    Raises:
        ValueError: If a string argument is invalid or cannot be converted to an integer.
        TypeError: If the argument type is not supported.
    """

    if arg is None: return FetchAll()
    if isinstance(arg, str):
        arg = no_underscore_or_space(arg).lower()
        if arg in ("one", "fetchone"): return FetchOne()
        if arg in ("all", "fetchall"): return FetchAll()
        try: return _fetch_num_arg(int(arg))
        except ValueError: pass
        raise ValueError(f"Invalid string argument for Fetch: {arg}")
    if isinstance(arg, int): return _fetch_num_arg(arg)
    if isinstance(arg, ReturnType): return arg
    raise TypeError(f"Invalid argument type: {type(arg).__name__}")



def normalize_return_type(rt: Union[str, int, ReturnType]) -> ReturnType:
    """
    Normalizes the input to a ReturnType instance.
    Args:
        rt (Union[str, int, ReturnType]): The input return type specifier.
    Returns:
        ReturnType: A normalized ReturnType instance.
    """
    return rt if isinstance(rt, ReturnType) else Fetch(rt)