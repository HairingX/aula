
from typing import Iterable, List, TypeVar

T = TypeVar('T')

def list_without_none(data: Iterable[T|None]) -> List[T]:
    return [d for d in data if d is not None ]