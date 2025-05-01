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

    # Construct the path to the font-patcher script (with no .py)
    FONT_PATCHER_PATH = ROOT_PATH / "font-patcher"

    # Create a module spec pretending that font-patcher is a real Python module
    spec = importlib.util.spec_from_file_location(
        "font_patcher", FONT_PATCHER_PATH)
    if not spec or not spec.loader:
        raise ImportError(
            "Plan B has failed. There is no Plan C. You are now officially doomed. Check to make sure the 'font-patcher' script exists.")

    # Load the module like a sorcerer
    font_patcher = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(font_patcher)

    # Font-patcher has now been imported through witchcraft!

# Now font_patcher is usable regardless of a clean or dirty import
TableHEADWriter = font_patcher.TableHEADWriter


@pytest.fixture
def tmp_font() -> Generator[str, Any, Any]:
    """
    Copy a TTF font into a temp file so each test starts with a clean slate
    """
    src = ROOT_PATH / "src/unpatched/Hack/Regular/Hack-Regular.ttf"
    td = tempfile.NamedTemporaryFile(suffix=".ttf", delete=False)
    td.close()
    shutil.copy(src, td.name)
    yield td.name
    Path(td.name).unlink()
