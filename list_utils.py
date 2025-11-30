from __future__ import annotations
from typing import Union

class Full:
    def __init__(self, tag: str = ""):
        tag = str(tag)
        self.tag = tag
    def __str__(self):
        return f"Full({self.tag})"
    def bool(self):
        return True
    def __repr__(self):
        return f"Full({self.tag})"
class Interval:

    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end
    

    def valid(self) -> bool:
        """
        Check if the interval is valid (start <= end).

        Returns:
            bool: True if the interval is valid, False otherwise.
        """
        return self.start <= self.end


    def __repr__(self):
        return f"Interval({self.start}, {self.end})"
    def __str__(self):
        return f"[{self.start}, {self.end}]"
    def __eq__(self, other):
        if isinstance(other, Interval):
            return self.start == other.start and self.end == other.end
        return False
    def __hash__(self):
        return hash((self.start, self.end))
    def __iter__(self):
        return iter(range(self.start, self.end + 1))
    def __contains__(self, item: int) -> bool:
        """
        Check if an integer is within the interval.

        Args:
            item (int): The integer to check.

        Returns:
            bool: True if the integer is within the interval, False otherwise.
        """
        if not isinstance(item, int):
            raise TypeError("Item must be an integer")
        return self.start <= item <= self.end
    def __add__(self, other: Interval) -> Interval | IntervalUnion:
        """
        Add two intervals together. If they overlap, return a single interval.
        If they do not overlap, return an IntervalUnion.

        Args:
            other (Interval): The other interval to add.

        Returns:
            Interval or IntervalUnion: The resulting interval or union of intervals.
        """
        if not self.valid() or not other.valid():
            raise ValueError("Invalid interval to add")
        if other.start in self:
            if other.end in self:
                return self
            else:
                return Interval(self.start, other.end)
        elif other.end in self:
            return Interval(other.start, self.end)
        elif self.start in other:
            if self.end in other:
                return other
            else:
                return Interval(other.start, self.end)
        return IntervalUnion(self, other)
                
    @staticmethod
    def flatten(*int_or_intervals: Union[int, Interval]) -> list:
        """
        Flatten a list of integers and intervals into a single list of integers.

        Args:
            *int_or_intervals: Integers or Interval objects.

        Returns:
            A list of integers.
        """
        result = []
        for item in int_or_intervals:
            if isinstance(item, int):
                result.append(item)
            elif isinstance(item, Interval):
                result.extend(range(item.start, item.end + 1))
            else:
                raise TypeError(f"Invalid argument type: {type(item)}")
        return list(dict.fromkeys(result))  # Remove duplicates while preserving order
class IntervalUnion:
    def __init__(self, *intervals: Interval):
        self.intervals = intervals

    def __repr__(self):
        return f"IntervalUnion({self.intervals})"

    def __str__(self):
        return f"[{', '.join(map(str, self.intervals))}]"

    def __iter__(self):
        seen = set()
        for interval in self.intervals:
            for num in interval:
                if num not in seen:
                    seen.add(num)
                    yield num

    def iter_intervals(self):
        """
        Iterate over the intervals in the union.

        Yields:
            Interval: Each interval in the union.
        """
        for interval in self.intervals:
            yield interval

    def __contains__(self, item: int | Interval | IntervalUnion) -> bool:
        """
        Check if:
          - an integer is within any of the intervals, or
          - an Interval is fully contained in the union, or
          - an IntervalUnion is fully contained in the union.

        Args:
            item: int, Interval, or IntervalUnion.

        Returns:
            bool: True if contained as above, False otherwise.
        """
        # Case 1: integer membership
        if isinstance(item, int):
            return any(item in interval for interval in self.intervals)

        # Case 2: Interval membership (subset check)
        elif isinstance(item, Interval):
            if not item.valid():
                raise ValueError("Invalid interval to check")
            # Ensure every point in the interval is in the union
            return all(x in self for x in item)

        # Case 3: IntervalUnion membership (subset of this union)
        elif isinstance(item, IntervalUnion):
            return all(interval in self for interval in item.iter_intervals())

        # Unsupported type
        raise TypeError("Item must be int, Interval, or IntervalUnion")
