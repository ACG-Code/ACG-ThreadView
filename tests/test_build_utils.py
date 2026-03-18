"""
test_build_utils.py
--------------------
Unit tests for the pure utility functions in build.py.

Only the stateless / file-IO helpers are tested here; the PyInstaller
invocation itself is not exercised (it requires the full build toolchain).
"""

import pytest
from datetime import datetime
from unittest.mock import patch

# build.py lives in src/, already on sys.path via conftest.py
from build import (
    bump_version,
    read_build_number,
    write_build_number,
    read_year,
    write_year,
    BUILD_FILE,
    YEAR_FILE,
    VERSION_BASE,
)


# ── bump_version ──────────────────────────────────────────────────────────────

class TestBumpVersion:
    """bump_version(args) returns (major, minor, patch) based on the CLI args dict."""

    def test_no_bump_returns_base(self):
        major, minor, patch = bump_version({'--major': False, '--minor': False, '--patch': False})
        assert (major, minor, patch) == VERSION_BASE

    def test_none_args_returns_base(self):
        major, minor, patch = bump_version(None)
        assert (major, minor, patch) == VERSION_BASE

    def test_major_bump(self):
        base_major = VERSION_BASE[0]
        major, minor, patch = bump_version({'--major': True, '--minor': False, '--patch': False})
        assert major == base_major + 1
        assert minor == 0
        assert patch == 0

    def test_minor_bump(self):
        base_minor = VERSION_BASE[1]
        major, minor, patch = bump_version({'--major': False, '--minor': True, '--patch': False})
        assert major == VERSION_BASE[0]
        assert minor == base_minor + 1
        assert patch == 0

    def test_patch_bump(self):
        base_patch = VERSION_BASE[2]
        major, minor, patch = bump_version({'--major': False, '--minor': False, '--patch': True})
        assert major == VERSION_BASE[0]
        assert minor == VERSION_BASE[1]
        assert patch == base_patch + 1

    def test_major_takes_priority_when_multiple_flags(self):
        """Only the first matching branch fires (major > minor > patch)."""
        major, minor, patch = bump_version({'--major': True, '--minor': True, '--patch': True})
        assert major == VERSION_BASE[0] + 1
        assert minor == 0
        assert patch == 0


# ── read_build_number ─────────────────────────────────────────────────────────

class TestReadBuildNumber:
    def test_returns_1_when_file_missing(self, tmp_path):
        with patch('build.ROOT_DIR', tmp_path):
            assert read_build_number() == 1

    def test_returns_incremented_value(self, tmp_path):
        (tmp_path / BUILD_FILE).write_text('5', encoding='utf-8')
        with patch('build.ROOT_DIR', tmp_path):
            assert read_build_number() == 6

    def test_invalid_content_resets_to_1(self, tmp_path):
        (tmp_path / BUILD_FILE).write_text('not_a_number', encoding='utf-8')
        with patch('build.ROOT_DIR', tmp_path):
            assert read_build_number() == 1

    def test_empty_file_resets_to_1(self, tmp_path):
        (tmp_path / BUILD_FILE).write_text('', encoding='utf-8')
        with patch('build.ROOT_DIR', tmp_path):
            assert read_build_number() == 1

    def test_whitespace_only_resets_to_1(self, tmp_path):
        (tmp_path / BUILD_FILE).write_text('   ', encoding='utf-8')
        with patch('build.ROOT_DIR', tmp_path):
            assert read_build_number() == 1


# ── write_build_number ────────────────────────────────────────────────────────

class TestWriteBuildNumber:
    def test_writes_number_to_file(self, tmp_path):
        with patch('build.ROOT_DIR', tmp_path):
            write_build_number(42)
        content = (tmp_path / BUILD_FILE).read_text(encoding='utf-8').strip()
        assert content == '42'

    def test_roundtrip(self, tmp_path):
        with patch('build.ROOT_DIR', tmp_path):
            write_build_number(99)
            assert read_build_number() == 100   # stored 99 → returns 99 + 1


# ── read_year ─────────────────────────────────────────────────────────────────

class TestReadYear:
    def test_returns_file_content_when_present(self, tmp_path):
        (tmp_path / YEAR_FILE).write_text('2023', encoding='utf-8')
        with patch('build.ROOT_DIR', tmp_path):
            assert read_year() == '2023'

    def test_returns_current_year_when_missing(self, tmp_path):
        with patch('build.ROOT_DIR', tmp_path):
            year = read_year()
        assert year == str(datetime.now().year)

    def test_returns_current_year_when_file_empty(self, tmp_path):
        (tmp_path / YEAR_FILE).write_text('', encoding='utf-8')
        with patch('build.ROOT_DIR', tmp_path):
            year = read_year()
        assert year == str(datetime.now().year)

    def test_strips_whitespace(self, tmp_path):
        (tmp_path / YEAR_FILE).write_text('  2025  \n', encoding='utf-8')
        with patch('build.ROOT_DIR', tmp_path):
            assert read_year() == '2025'


# ── write_year ────────────────────────────────────────────────────────────────

class TestWriteYear:
    def test_writes_year_to_file(self, tmp_path):
        with patch('build.ROOT_DIR', tmp_path):
            write_year('2026')
        content = (tmp_path / YEAR_FILE).read_text(encoding='utf-8')
        assert content == '2026'

    def test_roundtrip(self, tmp_path):
        with patch('build.ROOT_DIR', tmp_path):
            write_year('2030')
            assert read_year() == '2030'
