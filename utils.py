from typing import Iterable




def is_iterable(obj) -> bool:
    """
    Check if the object is iterable (excluding strings and bytes).

    Args:
        obj: The object to check.

    Returns:
        bool: True if the object is iterable, False otherwise.
    """
    return isinstance(obj, Iterable) and not isinstance(obj, (str, bytes))

def no_underscore_or_space(s: str) -> str:
    """
    Replaces underscores and spaces in a string with an empty string.

    Args:
        s (str): The input string.

    Returns:
        str: The modified string with underscores and spaces removed.
    """
    return s.replace("_", "").replace(" ", "")


def get_max_depth(obj) -> int:
    if is_iterable(obj):
        if not obj:
            return 1  # An empty container still counts as depth 1
        return 1 + max(get_max_depth(item) for item in obj)
    else:
        return 0
    
def is_depth_at_least(obj, max_depth, current_depth=0) -> bool:
    """
    Checks whether the nested depth of a given object is at least a specified maximum depth.
    Args:
        obj: The object to check. Can be a list, tuple, set, or any other type.
        max_depth (int): The minimum depth to check for.
        current_depth (int, optional): The current depth in the recursive traversal. Defaults to 0.
    Returns:
        bool: True if the object's nesting depth is at least `max_depth`, False otherwise.
    """
    
    if current_depth >= max_depth:
        return True
    if isinstance(obj, (list, tuple, set)):
        for item in obj:
            if is_depth_at_least(item, max_depth, current_depth + 1):
                return True
    return False

