from extract_and_apply_defaults import process_file
from pathlib import Path

def test_rewrite(tmp_path: Path) -> None:
    """Test that if a file has both `foo` and `Bar.foo`, then overwrites
    indeded for `foo` don't also get applied to `Bar.foo`.
    """ 
    content = (
        "from typing import overload\n"
        "\n"
        "class Bar:\n"
        "    @overload\n"
        "    def foo(self, a: str) -> str: ...\n"
        "    @overload\n"
        "    def foo(self, a: int) -> int: ...\n"
        "\n"
        "def foo(a=...) -> None:\n"
        "    ...\n"
    )
    root = (tmp_path / 'test_package')
    root.mkdir()
    file = (root / '__init__.pyi')
    file.write_text(content)
    process_file(str(root), str(file), 'test_package')

    with open(file) as fd:
        result = fd.read()
    
    expected = (
        "from typing import overload\n"
        "\n"
        "class Bar:\n"
        "    @overload\n"
        "    def foo(self, a: str) -> str: ...\n"
        "    @overload\n"
        "    def foo(self, a: int) -> int: ...\n"
        "\n"
        "def foo(a=None) -> None:\n"
        "    ...\n"
    )
    assert result == expected
