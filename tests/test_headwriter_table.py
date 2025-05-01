import font_patcher
import shutil
import tempfile
from pathlib import Path
import os

import pytest
from collections.abc import Generator
from typing import Any

ROOT_PATH = Path(__file__).resolve().parent.parent

try:
    # Try the normal civilized way: relative import.
    # This is what makes Pylance happy.
    # NOTE: This is symlinked because Pylance complains when there's a hyphen and no .py
    # The symlink is ../font-patcher -> ../font_patcher.py
    from .. import font_patcher  # YAY autocomplete!
except (ImportError, SystemError):
    # Plan B: Runtime is stupid and can't handle packages properly. *eye_roll*
    # Fall back to manually loading the font_patcher script like a barbarian

    import importlib.util
    import importlib.machinery

    # Construct the path to the font-patcher script (with no .py)
    FONT_PATCHER_PATH = ROOT_PATH / "font-patcher"

    # Create a module spec pretending that font-patcher is a real Python module
    loader = importlib.machinery.SourceFileLoader(
        "font_patcher", str(FONT_PATCHER_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if not spec or not spec.loader:
        raise ImportError(
            "Plan B has failed. There is no Plan C. You are now officially doomed. Check to make sure the 'font-patcher' script exists.")

    # Load the module like a sorcerer
    font_patcher = importlib.util.module_from_spec(spec)
    loader.exec_module(font_patcher)

    # Font-patcher has now been imported through witchcraft!

# Now font_patcher is usable regardless of a clean or dirty import
TableHEADWriter = font_patcher.TableHEADWriter


@pytest.fixture
def tmp_font() -> Generator[str, Any, Any]:
    """
    Copy a TTF font into a temp file so each test starts with a clean slate
    """
    src = ROOT_PATH / "src/unpatched-fonts/Hack/Regular/Hack-Regular.ttf"
    td = tempfile.NamedTemporaryFile(suffix=".ttf", delete=False)
    td.close()
    shutil.copy(src, td.name)
    yield td.name
    Path(td.name).unlink()

# -----------------------------------
# Tests for correctness
# ------------------------------------


def test_get_and_put_long(tmp_font: str) -> None:
    writer = TableHEADWriter(tmp_font)
    orig = writer.getlong('checksumAdjustment')
    test_val = 0x12345678

    writer.putlong(test_val, 'checksumAdjustment')
    writer.f.flush()

    # reopen to avoid any in-memory cachign
    writer2 = TableHEADWriter(tmp_font)
    new = writer2.getlong('checksumAdjustment')
    assert new == test_val
