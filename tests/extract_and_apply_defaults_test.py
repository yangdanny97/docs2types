from extract_and_apply_defaults import process_file
from pathlib import Path
import pytest
import shutil

TEST_CASES = list((Path("tests") / "test_cases").glob("case*"))


@pytest.mark.parametrize("test_case", TEST_CASES)
def test_rewrites(tmp_path: Path, test_case: Path) -> None:
    root = tmp_path / "test_package"
    root.mkdir()
    file_path = root / "__init__.pyi"
    stub, expected_path = list(test_case.glob("*"))
    shutil.copy2(stub, file_path)
    process_file(str(root), str(file_path), "test_package")

    with open(file_path) as fd:
        result = fd.read()
    expected = expected_path.read_text()

    assert result == expected
