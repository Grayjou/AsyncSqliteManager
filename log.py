from typing import Any
from datetime import datetime
from typing import Union, List, Tuple
class Unknown:
    __slots__ = ("name",)
    def __init__(self, name: str):
        self.name = name
    def __repr__(self):
        return f"<Unknown: {self.name}>"
    def __eq__(self, other):
        if isinstance(other, Unknown):
            return self.name == other.name
        return False
    def __hash__(self):
        return hash(self.name)
    def __str__(self):
        return f'Unknown({self.name})'


def is_unknown(value: Any) -> bool:
    """
    Check if the value is an instance of Unknown.

    Args:
        value: The value to check.

    Returns:
        bool: True if the value is an instance of Unknown, False otherwise.
    """
    return isinstance(value, Unknown)

def none_or_unknown(value: Any) -> bool:
    """
    Check if the value is None or an instance of Unknown.

    Args:
        value: The value to check.

    Returns:
        bool: True if the value is None or an instance of Unknown, False otherwise.
    """
    return value is None or is_unknown(value)

class ExecutionLog:
    __slots__ = ("path","query", "params", "return_type", "result")
    def __init__(self, path:str, query: str, params: Union[tuple, List[tuple]], return_type: str, result: Any = Unknown("Result")):
        self.path = path
        self.query = query
        self.params = params
        self.return_type = return_type
        self.result = result
    def __repr__(self):
        return f"ExecutionLog({self.path!r}, {self.query!r}, {self.params!r}, {self.return_type!r}, {self.result!r})"
    def __str__(self):
        return (f"ExecutionLog("
                f"path={self.path!r}, "
                f"query={self.query!r}, params={self.params!r}, return_type={self.return_type}, "
                f"result={self.result}")

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "query": self.query,
            "params": self.params,
            "return_type": self.return_type,
            "result": str(self.result)
        }
    def __eq__(self, other):
        if not isinstance(other, ExecutionLog):
            return False
        return (
            self.path == other.path and
            self.query == other.query and
            self.params == other.params and
            self.return_type == other.return_type and
            self.result == other.result
        )
