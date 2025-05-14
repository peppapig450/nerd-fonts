import os
import shutil
import importlib.machinery
import importlib.util
from pathlib import Path
import pytest

# ----------------------------------------------------------------------
# Dynamic loading of original and refactored font-patcher modules
# ----------------------------------------------------------------------


def load_font_patcher(name: str, path: Path):
    """
    Load a hyphenated, extensionless 'font-patcher' script as a Python module.
    """
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


# Determine root paths
ROOT_PATH = Path(__file__).resolve().parent.parent.parent

# Load original (unrefactored) font-patcher
font_patcher_ref = load_font_patcher(
    "font_patcher_ref", ROOT_PATH / "nerd-fonts" / "font-patcher"
)

# Load local refactored font-patcher, falling back if needed
try:
    from .. import font_patcher as font_patcher_new
except (ImportError, SystemExit):
    font_patcher_new = load_font_patcher(
        "font_patcher_new", ROOT_PATH / "nerd-fonts-refactor" / "font-patcher"
    )

# Aliases to HEADWriter implementations
OriginalHEADWriter = font_patcher_ref.TableHEADWriter
RefactoredHEADWriter = font_patcher_new.TableHEADWriter

# ----------------------------------------------------------------------
# HEAD table field offsets
# ----------------------------------------------------------------------

HEAD_POSITIONS = {
    "checksumAdjustment": 2 + 2 + 4,
    "flags": 2 + 2 + 4 + 4 + 4,
    "lowestRecPPEM": 2 + 2 + 4 + 4 + 4 + 2 + 2 + 8 + 8 + 2 + 2 + 2 + 2 + 2,
    "avgWidth": 2,
}


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
# Benchmarks for get/put methods
# ----------------------------------------------------------------------


@pytest.mark.benchmark
@pytest.mark.parametrize("field", list(HEAD_POSITIONS.keys()))
@pytest.mark.parametrize(
    "impl", [OriginalHEADWriter, RefactoredHEADWriter], ids=["original", "refactored"]
)
def test_benchmark_get_methods(benchmark, field, impl, tmp_path, sample_font_path):
    tmp_font = tmp_path / f"{impl.__name__}.ttf"
    shutil.copy2(sample_font_path, tmp_font)
    writer = impl(str(tmp_font))
    if field == "checksumAdjustment":
        bench_fn = lambda: writer.getlong(field)
    else:
        bench_fn = lambda: writer.getshort(field)
    benchmark(bench_fn)
    writer.close()


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "impl", [OriginalHEADWriter, RefactoredHEADWriter], ids=["original", "refactored"]
)
def test_benchmark_put_methods(benchmark, impl, tmp_path, sample_font_path):
    tmp_font = tmp_path / f"{impl.__name__}.ttf"
    shutil.copy2(sample_font_path, tmp_font)
    writer = impl(str(tmp_font))
    _ = writer.getlong("checksumAdjustment")
    _ = writer.getshort("flags")

    def write_ops():
        writer.putlong(0x12345678, "checksumAdjustment")
        writer.putshort(0x9ABC, "flags")

    benchmark(write_ops)
    writer.close()


# ----------------------------------------------------------------------
# Benchmarks for checksum methods (parametrized to avoid reusing fixture)
# ----------------------------------------------------------------------


@pytest.mark.benchmark(max_time=20)
@pytest.mark.parametrize("which", ["table", "full"], ids=["table", "full"])
def test_benchmark_checksum_methods(benchmark, writers, which):
    """Benchmark HEAD table vs full-file checksum methods."""
    _, writer = writers
    bench_fn = (
        writer.calc_table_checksum if which == "table" else writer.calc_full_checksum
    )
    benchmark(bench_fn)


@pytest.mark.benchmark(max_time=20)
@pytest.mark.parametrize("scope", ["partial", "full"], ids=["partial", "full"])
def test_benchmark_calc_raw_checksum(benchmark, writers, scope):
    """Benchmark raw calc_checksum on partial and full ranges."""
    _, writer = writers
    start = writer.tab_offset
    end = (
        (start + writer.tab_length // 2)
        if scope == "partial"
        else (start + writer.tab_length - 1)
    )
    benchmark(lambda: writer.calc_checksum(start, end))


@pytest.mark.benchmark(max_time=20)
def test_benchmark_table_lookup(benchmark, tmp_path, sample_font_path):
    tmp_font = tmp_path / "lookup.ttf"
    shutil.copy2(sample_font_path, tmp_font)

    def lookup():
        w = RefactoredHEADWriter(str(tmp_font))
        w.close()

    benchmark(lookup)
