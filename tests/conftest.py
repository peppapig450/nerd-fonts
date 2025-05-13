import shutil
from pathlib import Path
import pytest

ROOT_PATH = Path(__file__).resolve().parent.parent

try:
    # Try the normal civilized way: relative import.
    # This is what makes Pylance happy.
    # NOTE: This is symlinked because Pylance complains when
    # the filename has a hyphen and no .py extension
    # The symlink is ../font-patcher -> ../font_patcher.py
    from .. import font_patcher  # YAY autocomplete!
except (ImportError, SystemExit):
    # Plan B: Runtime is stupid and can't handle packages properly. *eye_roll*
    # Fall back to manually loading the font_patcher script like a barbarian.

    import importlib.util
    import importlib.machinery

    # Construct the path to the font-patcher script (with no .py)
    FONT_PATCHER_PATH = ROOT_PATH / "font-patcher"

    # Create a module spec pretending that font-patcher is a real Python module.
    loader = importlib.machinery.SourceFileLoader(
        "font_patcher", str(FONT_PATCHER_PATH)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if not spec or not spec.loader:
        raise ImportError(
            "Plan B has failed. There is no Plan C. You are now officially doomed. Check to make sure the 'font-patcher' script exists."
        )

    # Load the module like a sorcerer
    font_patcher = importlib.util.module_from_spec(spec)
    loader.exec_module(font_patcher)

    # Font-patcher has now been imported through witchcraft!

# Now font_patcher is usable regardless of a clean or dirty import
TableHEADWriter = font_patcher.TableHEADWriter


@pytest.fixture(scope="session")
def sample_font_path() -> Path:
    """
    Absolute path to a reference font to use for testing.
    """
    return (
        ROOT_PATH / "src" / "unpatched-fonts" / "Hack" / "Regular" / "Hack-Regular.ttf"
    )


@pytest.fixture
def tmp_font_path(sample_font_path: Path, tmp_path: Path) -> Path:
    """
    Copy the reference TTF into a pytest-managed temp directory so tests are
    free to open it read-write without risk.
    """
    tmp_file = tmp_path / "Hack-Regular-copy.ttf"
    shutil.copy2(sample_font_path, tmp_file)
    return tmp_file


@pytest.fixture
def head_writer(tmp_font_path: Path):
    """
    A TableHEADWriter instance opened on the temporary font copy.
    Automatically closed after each test.
    """
    writer = TableHEADWriter(str(tmp_font_path))
    try:
        yield writer
    finally:
        writer.close()
