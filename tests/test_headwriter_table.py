"""
Regression tests for the original byte-wise implementation of TableHEADWriter

The goal is to lock down semantics before refactoring to struct.unpack_from
and mmap, so that behavior and performance can be compared side-by-side afterwards.
"""

import struct  # Prefer struct over int.from_bytes as it's written in C  & faster
from pathlib import Path

import pytest

# Offsets inside the HEAD table, replicated from TableHEADWriter.goto()
_HEAD_OFFSETS: dict[str, int] = {
    "checksumAdjustment": 2 + 2 + 4,  # 8
    "flags": 2 + 2 + 4 + 4 + 4,  # 16
}

# ---------------------------------------------------------------------------
# Low level helpers
# ---------------------------------------------------------------------------


def _read_be_uint(path: Path, absolute_offset: int, byte_len: int) -> int:
    """
    Read an unsigned big-endian int (2 or 4 bytes) directly from a _path_
    without using TableHEADWriter. This acts as an oracle for the tests.
    """
    with path.open("rb") as fh:
        fh.seek(absolute_offset)
        raw = fh.read(byte_len)
    fmt = ">H" if byte_len == 2 else ">I"
    return struct.unpack_from(fmt, raw)[0]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_getshort_and_getlong_match_struct(head_writer, tmp_font_path: Path):
    """
    Cross-check getshort/getlong against the ground-truth bytes read
    directly from the file with struct.unpack().
    """
    # HEAD table starts at writer.tab_offset
    base = head_writer.tab_offset

    # checksumAdjustment (uint32)
    expected_long = _read_be_uint(
        tmp_font_path, base + _HEAD_OFFSETS["checksumAdjustment"], 4
    )
    value_long = head_writer.getlong("checksumAdjustment")
    assert value_long == expected_long, "getlong() returned wrong value"

    # flags (uint16)
    expected_short = _read_be_uint(tmp_font_path, base + _HEAD_OFFSETS["flags"], 2)
    value_short = head_writer.getshort("flags")
    assert value_short == expected_short, "getshort() returned wrong value"


def test_table_checksum_matches_record(head_writer):
    """
    calc_table_checksum() must reproduce the checksum stored in the font's
    table directory entry for 'head'.
    """
    # Writer captured the on-disk value during __init__
    on_disk = head_writer.tab_check

    # Freshly computed via the original algorithm
    recalculated = head_writer.calc_table_checksum()

    assert recalculated == on_disk, "Table checksum differs, HEAD table may be corrupt"


def test_full_file_checksum_adjustment_is_consistent(head_writer):
    """
    The classic TrueType rule:
        (0&B1B0AFBA - sum_of_all_uint32) & 0xFFFFFFFF == checksumAdjustment
    must hold for a valid font.
    """
    full_sum = head_writer.calc_full_checksum()
    expected_adj = (0xB1B0AFBA - full_sum) & 0xFFFFFFFF

    assert (
        expected_adj == head_writer.checksum_adj
    ), "Whole-file checksum adjustment field is incorrect"
