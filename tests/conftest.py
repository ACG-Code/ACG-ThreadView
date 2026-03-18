"""
conftest.py
-----------
Shared pytest configuration.

- Adds src/ to sys.path so tests can import project modules directly.
- Stubs out PyQt5 and TM1py before any test module imports them, so the
  pure-logic helpers in main_window.py are testable without a Qt install.
"""

import sys
import os
from unittest.mock import MagicMock

# ── path setup ────────────────────────────────────────────────────────────────

SRC_DIR = os.path.join(os.path.dirname(__file__), '..', 'src')
sys.path.insert(0, os.path.abspath(SRC_DIR))

# ── Qt / TM1py stubs ──────────────────────────────────────────────────────────
# Mock before any src module is imported so Qt-importing modules load cleanly.

_STUB_MODULES = [
    'PyQt5',
    'PyQt5.sip',
    'PyQt5.QtCore',
    'PyQt5.QtWidgets',
    'PyQt5.QtGui',
    'PyQt5.uic',
    'TM1py',
]

for _mod in _STUB_MODULES:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Give Qt.AlignRight a concrete integer so layout code doesn't crash
sys.modules['PyQt5.QtCore'].Qt.AlignRight = 0x0002
