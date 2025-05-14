"""
This module contains cursed logic to load 'font-patcher' scripts from two divergent timelines.
Warning: Contains sarcastic comments. Not intended to offend, just to cope.
"""

import shutil
import importlib.machinery
import importlib.util
from pathlib import Path

import pytest


def load_font_patcher(name: str, path: Path):
    """
    Load the 'font-patcher' script from a specific path using forbidden Python magic.

    This is necessary because:
      - The script is named 'font-patcher' (with a hyphen), which Python absolutely hates.
      - It lacks a .py extension, because chaos reigns.
      - It's not part of a package, because life is hard.
      - We still want to use it like a module, because pretending it's normal makes us feel better.

    Parameters:
        name (str): The fake module name to register it as. You can name it anything,
                    e.g., 'font_patcher_ref', 'font_patcher_new', or 'that_which_should_not_be_imported'.
        path (Path): Path to the 'font-patcher' script, wherever your sins are stored.

    Returns:
        The loaded module object, now masquerading as a real boy.
    """
    loader = importlib.machinery.SourceFileLoader(name, str(path))

    # Try to summon a module spec from the underworld
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if not spec or not spec.loader:
        raise ImportError(
            f"Plan B has failed. There is no Plan C. "
            f"The script at {path} cannot be loaded. "
            f"Try renaming it to something Python won't cry about."
        )

    # Construct a module from the void
    mod = importlib.util.module_from_spec(spec)

    # Breathe life into the empty shell
    loader.exec_module(mod)

    # YOU'RE A WIZARD HARRY
    return mod


ROOT_PATH = Path(__file__).resolve().parent.parent.parent

# NOTE: This setup assumes you're using a Git worktree.
# Specifically, the branch `refactor/modernize-head-table` should be checked out
# in a worktree located at: ../nerd-fonts-refactor
# relative to the main repository root (which has the `nerd-fonts` directory).
#
# Your directory layout should look like this:
#
# ROOT_PATH/
# ├── nerd-fonts/
# │   └── font-patcher/
# │       └── [legacy chaos lives here – ancient, unrefactored evil]
# └── nerd-fonts-refactor/
#     └── font-patcher/
#         └── [hope, order, maybe comments? – the refactored savior]

# Load the ancient, unrefactored evil
font_patcher_ref = load_font_patcher(
    "font_patcher_ref", ROOT_PATH / "nerd-fonts" / "font-patcher"
)

# Try the civilized route first for the local refactored version
try:
    from .. import (
        font_patcher as font_patcher_new,
    )  # to make Pylance a happy boy/girl/it whatever it wishes to identify as
except (ImportError, SystemExit):
    # Apparently this import can kill the interpreter (this actually happened).
    # Descend into madness, load it manually
    font_patcher_new = load_font_patcher(
        "font_patcher_new", ROOT_PATH / "nerd-fonts-refactor" / "font-patcher"
    )

# ----------------------------------------------------------------------
# HEAD table field offsets relative to tab_offset
# ----------------------------------------------------------------------

HEAD_POSITIONS = {
    "checksumAdjustment": 2 + 2 + 4,
    "flags": 2 + 2 + 4 + 4 + 4,
    "lowestRecPPEM": 2 + 2 + 4 + 4 + 4 + 2 + 2 + 8 + 8 + 2 + 2 + 2 + 2 + 2,
    "avgWidth": 2,
}

# ----------------------------------------------------------------------
# Fixtures to give each implementation its own temp file & writer
# ----------------------------------------------------------------------


@pytest.fixture
def ref_font_path(tmp_path, sample_font_path):
    """Copy the master font into a temp file for the *original* writer."""
    p = tmp_path / "orig.ttf"
    shutil.copy2(sample_font_path, p)
    return p


@pytest.fixture
def new_font_path(tmp_path, sample_font_path):
    """Copy the master font into a temp file for the *refactored* writer."""
    p = tmp_path / "new.ttf"
    shutil.copy2(sample_font_path, p)
    return p


@pytest.fixture
def ref_writer(ref_font_path):
    w = font_patcher_ref.TableHEADWriter(str(ref_font_path))
    yield w
    w.close()


@pytest.fixture
def new_writer(new_font_path):
    w = font_patcher_new.TableHEADWriter(str(new_font_path))
    yield w
    w.close()


@pytest.fixture
def writers(ref_writer, new_writer):
    """Yield a tuple of (original_writer, new_writer)."""
    return ref_writer, new_writer


# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------


def test_getshort_getlong_equivalence(writers):
    """
    Ensure both implementations read identical values for every HEAD field.
    Regression caught: any change in byte-order, pos resolution, or struct versus bytewise logic.
    """
    ref, new = writers
    for name, _ in HEAD_POSITIONS.items():
        if name == "checksumAdjustment":
            v_ref = ref.getlong(name)
            v_new = new.getlong(name)
        else:
            v_ref = ref.getshort(name)
            v_new = new.getshort(name)
        assert v_ref == v_new, f"Value mismatch on {name}: {v_ref} != {v_new}"


def test_goto_updates_ptr_consistently(writers):
    """
    Both writers must compute the same absolute ptr after goto(name).
    Regression caught: off-by-one or wrong base-offset in the new code.
    """
    ref, new = writers
    for name, rel in HEAD_POSITIONS.items():
        ref.goto(name)
        new.goto(name)
        expected = ref.tab_offset + rel
        assert ref.f.tell() == expected, f"Original f.tell wrong for {name}"
        assert new.ptr == expected, f"Refactored.ptr wrong for {name}"


def test_sequential_get_advances_ptr_equally(writers):
    """
    After two back-to-back getlong() calls (no pos arg),
    both implementations must advance ptr the same and return the same data.
    Regression caught: struct.iter_unpack versus bytewise read differences.
    """
    ref, new = writers
    start = ref.tab_offset
    ref.goto(start)
    new.goto(start)

    vals_ref = [ref.getlong(), ref.getlong()]
    vals_new = [new.getlong(), new.getlong()]

    assert vals_ref == vals_new
    assert ref.f.tell() == new.ptr


def test_calc_checksum_with_initial_matches(writers):
    """
    calc_checksum(start,end,checksum=INIT) must match between impls for nonzero INIT.
    Regression caught: padding-tail logic or initial accumulator handling.
    """
    ref, new = writers
    start = ref.tab_offset
    end = start + ref.tab_length
    INIT = 0x12345678

    cs_ref = ref.calc_checksum(start, end, checksum=INIT)
    cs_new = new.calc_checksum(start, end, checksum=INIT)

    assert cs_ref == cs_new


def test_find_table_missing_and_head_errors(writers):
    """
    find_table should return False for a bogus tag,
    and find_head_table(idx>0) must raise on non-TTC fonts in both.
    Regression caught: error-path divergence.
    """
    ref, new = writers
    assert ref.find_table([b"FAKE"], 0) is False
    assert new.find_table([b"FAKE"], 0) is False

    with pytest.raises(Exception):
        ref.find_head_table(1)
    with pytest.raises(Exception):
        new.find_head_table(1)


def test_put_and_get_without_pos_equivalence(writers):
    """
    putshort/putlong without pos (i.e. via ptr) must:
      - write the same bytes,
      - return the same values via get*,
      - advance ptr by the same amount.
    Regression caught: default-pos logic or struct.pack_into mismatch.
    """
    ref, new = writers
    for name, size in (("flags", 2), ("checksumAdjustment", 4)):
        # 1) read original
        ref.goto(name)
        orig_ref = ref.getshort() if size == 2 else ref.getlong()
        new.goto(name)
        orig_new = new.getshort() if size == 2 else new.getlong()
        assert orig_ref == orig_new

        # 2) choose a flipped value
        new_val = orig_ref ^ (0xFFFF if size == 2 else 0xDEADBEEF)

        # 3) write without pos
        ref.goto(name)
        new.goto(name)
        if size == 2:
            ref.putshort(new_val)
            new.putshort(new_val)
        else:
            ref.putlong(new_val)
            new.putlong(new_val)

        # 4) read back at pos
        got_ref = ref.getshort(name) if size == 2 else ref.getlong(name)
        got_new = new.getshort(name) if size == 2 else new.getlong(name)
        assert got_ref == got_new == new_val

        # 5) ensure both pointers advanced by `size`
        expected_ptr = ref.tab_offset + HEAD_POSITIONS[name] + size
        assert ref.f.tell() == expected_ptr
        assert new.ptr == expected_ptr


def test_calc_table_and_full_checksum_agree(writers):
    """
    calc_table_checksum(check=True) and calc_full_checksum(check=True)
    must both succeed and give identical ints.
    Regression caught: the 'check'-mode exit paths must line up.
    """
    ref, new = writers
    assert ref.calc_table_checksum(
        check=True) == new.calc_table_checksum(check=True)
    assert ref.calc_full_checksum(
        check=True) == new.calc_full_checksum(check=True)


def test_reset_table_and_full_checksum_consistency(writers):
    """
    After corrupting both table-entry and full checksumAdjustment,
    reset_table_checksum() and reset_full_checksum() must restore the same
    values in both implementations.
    Regression caught: the write-back logic or byte-order for those fixes.
    """
    ref, new = writers

    # corrupt and reset table checksum
    ref.putlong(0, ref.tab_check_offset)
    new.putlong(0, new.tab_check_offset)
    ref.reset_table_checksum()
    new.reset_table_checksum()
    val_ref = ref.getlong(ref.tab_check_offset)
    val_new = new.getlong(new.tab_check_offset)
    assert val_ref == val_new

    # corrupt and reset full checksumAdjustment
    ref.putlong(0, "checksumAdjustment")
    new.putlong(0, "checksumAdjustment")
    ref.reset_full_checksum()
    new.reset_full_checksum()
    adj_ref = ref.getlong("checksumAdjustment")
    adj_new = new.getlong("checksumAdjustment")
    assert adj_ref == adj_new
