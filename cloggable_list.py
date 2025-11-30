from typing import Optional, Union, Tuple
from .list_utils import Full, Interval

def convertible_to_non_neg_int(value) -> Tuple[bool, int]:
    try:
        ivalue = int(value)
        if ivalue < 0:
            return (False, 0)
        return (True, ivalue)
    except (TypeError, ValueError):
        return (False, 0)

def validate_non_neg_int(value: Optional[int]) -> int:
    ivalue, can_convert = convertible_to_non_neg_int(value)
    if not can_convert:
        raise ValueError("history_length must be a non negative integer")
    return ivalue

def validate_none_or_non_neg_int(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    ivalue, can_convert = convertible_to_non_neg_int(value)
    if not can_convert:
        raise ValueError("history_tolerance must be a non negative integer or None")
    return ivalue

class CloggableList(list):
    """
    A list subclass with overflow control, designed to simulate a capacity-limited buffer.

    The `CloggableList` enforces a maximum length (`max_length`) and allows a limited 
    overflow tolerance (`tolerance`). It restricts additions once the tolerable limit is 
    exceeded and provides utility methods for controlled extraction and flushing.

    Attributes:
        max_length (int): The maximum number of elements before the list is considered full.
        tolerance (int): Number of elements allowed beyond `max_length` before raising an error. If `None`, the list is considered unlimited.

    Properties:
        full (bool): True if the list has reached or exceeded `max_length`.

    Methods:
        tolerable() -> bool:
            Returns True if the current list size is within `max_length + tolerance`.

        intolerable() -> bool:
            Returns True if the list size exceeds `max_length + tolerance`.

        flush() -> tuple:
            Removes all elements from the list and returns them as a tuple.

        extract(*args: Union[int, Interval]) -> tuple:
            Removes and returns elements at specified indices or within interval ranges.
            If no arguments are provided, behaves like `flush()`.

    Decorators:
        proceed_if_tolerable(method):
            Prevents method execution and raises `OverflowError` if the list is beyond tolerance.

        return_full(method):
            Executes the method and returns a `Full` instance if the list becomes full afterward.

    Overridden Methods:
        append(object):
            Appends an element if within tolerable limits. Returns `Full` if list becomes full.

        extend(iterable):
            Extends the list if within tolerable limits. Returns `Full` if list becomes full.

    Raises:
        OverflowError: When appending or extending the list past the tolerable limit.
        IndexError: When invalid indices are used in the `extract` method.
        TypeError: If `extract` arguments are not integers or `Interval` instances.

    Example:
        >>> cl = CloggableList(max_length=3, tolerance=1)
        >>> cl.append(1)
        >>> cl.extend([2, 3])
        >>> cl.append(4)  # still within tolerance
        >>> cl.append(5)  # raises OverflowError
    """

    def __init__(self, max_length: int = 1, tolerance: Optional[int] = 0):
        
        super().__init__()
        self.max_length = max_length
        self.tolerance = tolerance
    def _full(self) -> bool:
        """
        Check if the list is full.
        """
        return len(self) >= self.max_length
    full = property(_full)

    @property
    def max_length(self) -> int:
        return self._max_length

    @max_length.setter
    def max_length(self, value: int) -> None:
        ivalue = validate_non_neg_int(value)
        self._max_length = ivalue
    @property
    def tolerance(self) -> Optional[int]:
        return self._tolerance
    @tolerance.setter
    def tolerance(self, value: Optional[int]) -> None:
        value = validate_none_or_non_neg_int(value)
        self._tolerance = value

    def tolerable(self) -> bool:
        """
        Check if the list is within tolerance.
        """
        if self.tolerance is None:
            return True
        return len(self) <= self.max_length + self.tolerance
    def intolerable(self) -> bool:
        """
        Check if the list is intolerable.
        """
        return not self.tolerable()
    @staticmethod
    def proceed_if_tolerable(method):
        def wrapper(self: "CloggableList", *args, **kwargs):
            if self.intolerable():
                raise OverflowError("List is full")
            return method(self, *args, **kwargs)
        return wrapper
    
    @staticmethod
    def return_full(method):
        def wrapper(self: "CloggableList", *args, **kwargs):
            method(self, *args, **kwargs)
            if self.full:
                return Full()
        return wrapper

    @proceed_if_tolerable
    @return_full
    def append(self, object) -> Optional[Full]:
        super().append(object)

    @proceed_if_tolerable
    @return_full
    def extend(self, iterable) -> Optional[Full]:
        super().extend(iterable)

    def flush(self) -> tuple:
        """
        Flush the list, removing all elements.
        """
        output = tuple(self)
        self.clear()
        return output
    
    def extract(self, *args: Union[int, Interval]) -> tuple:
        indices = set(Interval.flatten(*args))
        if any(i < 0 or i >= len(self) for i in indices):
            raise IndexError("Index out of range")

        extracted = [self[i] for i in sorted(indices)]
        for i in sorted(indices, reverse=True):
            del self[i]
        return tuple(extracted)
    
    def remove(self, value) -> None:
        """
        Remove the first occurrence of a value from the list.
        """
        super().remove(value)
