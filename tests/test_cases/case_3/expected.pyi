from typing import overload

class Bar:
    @overload
    def foo(self, b: str) -> str: ...
    @overload
    def foo(self, b: int) -> int: ...

def foo(a=None) -> None:
    ...
