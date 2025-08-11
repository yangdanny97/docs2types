from typing import overload

class Bar:
    @overload
    def foo(self, a: str) -> str: ...
    @overload
    def foo(self, a: int) -> int: ...

def foo(a=None) -> None:
    ...
