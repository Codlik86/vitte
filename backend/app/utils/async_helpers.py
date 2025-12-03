from typing import Any, AsyncIterator, Iterable, TypeVar

T = TypeVar("T")


async def aiter(iterable: Iterable[T]) -> AsyncIterator[T]:
    for item in iterable:
        yield item


def ensure_async_iter(iterable: Any) -> AsyncIterator[Any]:
    if hasattr(iterable, "__aiter__"):
        return iterable  # type: ignore[return-value]
    return aiter(iterable)
