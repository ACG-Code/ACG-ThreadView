"""
Usage:
    build.py [--major | --minor | --patch]
    build.py (-h | --help)

Options:
    --major     Bump major version (resets minor and patch)
    --minor     Bump minor version (resets patch)
    --patch     Bump patch version
    -h --help   Show this help message
"""

import subprocess
import sys
from pathlib import Path
from typing import Tuple
from datetime import datetime

try:
    from docopt import docopt
except ImportError:
    print("Warning: docopt not installed. Install with: pip install docopt")
    print("   Running without version bump options...")
    docopt = None

# ─── Constants ────────────────────────────────────────────────────────────────

APP_NAME     = "ACG-ThreadView"
SCRIPT_NAME  = "main.py"
BUILD_FILE   = "build_number.txt"
VERSION_FILE = "version.txt"
YEAR_FILE    = "app_year.txt"
VERSION_BASE = (1, 0, 0)  # major.minor.patch

# ─── Paths ────────────────────────────────────────────────────────────────────

ROOT_DIR  = Path(__file__).resolve().parent          # src/
ICON_PATH = (ROOT_DIR / 'images' / 'ACG.ico').resolve()
DIST_PATH = (ROOT_DIR.parent / 'dist').resolve()
WORK_PATH = (ROOT_DIR.parent / 'build').resolve()

# ─── Utilities ────────────────────────────────────────────────────────────────

def read_year() -> str:
    year_file = ROOT_DIR / YEAR_FILE
    if year_file.exists():
        return year_file.read_text(encoding='utf-8').strip() or str(datetime.now().year)
    return str(datetime.now().year)


def write_year(year: str) -> None:
    (ROOT_DIR / YEAR_FILE).write_text(year, encoding='utf-8')


def read_build_number() -> int:
    build_file = ROOT_DIR / BUILD_FILE
    if build_file.exists():
        try:
            return int(build_file.read_text(encoding='utf-8').strip()) + 1
        except ValueError:
            print(f"Warning: invalid build number in {BUILD_FILE}, resetting to 1")
            return 1
    return 1


def write_build_number(build: int) -> None:
    (ROOT_DIR / BUILD_FILE).write_text(str(build), encoding='utf-8')
    print(f"Build number: {build}")


def bump_version(args: dict) -> Tuple[int, int, int]:
    major, minor, patch = VERSION_BASE
    if args and args.get('--major'):
        major += 1; minor = 0; patch = 0
        print("Bumping major version")
    elif args and args.get('--minor'):
        minor += 1; patch = 0
        print("Bumping minor version")
    elif args and args.get('--patch'):
        patch += 1
        print("Bumping patch version")
    else:
        print("No version bump (using base version)")
    return major, minor, patch


def write_version_file(major: int, minor: int, patch: int, build: int, year: str) -> None:
    version_str = f"{major}.{minor}.{patch}.{build}"

    # Simple version string for runtime reading
    simple_version_file = ROOT_DIR / "simple_version.txt"
    simple_version_file.write_text(version_str, encoding='utf-8')
    print(f"Simple version: {version_str}")

    content = f"""# UTF-8
#
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({major}, {minor}, {patch}, {build}),
    prodvers=({major}, {minor}, {patch}, {build}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Application Consulting Group, Inc.'),
          StringStruct('FileDescription', '{APP_NAME}'),
          StringStruct('FileVersion', '{version_str}'),
          StringStruct('InternalName', '{APP_NAME}'),
          StringStruct('LegalCopyright', '{year} Application Consulting Group, Inc.'),
          StringStruct('OriginalFilename', '{APP_NAME}.exe'),
          StringStruct('ProductName', '{APP_NAME}'),
          StringStruct('ProductVersion', '{version_str}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    (ROOT_DIR / VERSION_FILE).write_text(content, encoding='utf-8')
    print(f"Version file written: {version_str}")


def validate_environment() -> None:
    errors = []

    for file_path, desc in [
        (ROOT_DIR / SCRIPT_NAME, "Main script"),
        (ICON_PATH,              "Icon file"),
        (ROOT_DIR / 'ui' / 'main_window.ui',  "main_window.ui"),
        (ROOT_DIR / 'ui' / 'setup_window.ui', "setup_window.ui"),
    ]:
        if not file_path.exists():
            errors.append(f"Missing {desc}: {file_path}")

    try:
        from PyQt5.QtCore import PYQT_VERSION_STR
        print(f"PyQt5 found: {PYQT_VERSION_STR}")
    except ImportError:
        errors.append("PyQt5 not installed")

    try:
        import TM1py
        print(f"TM1py found")
    except ImportError:
        errors.append("TM1py not installed")

    try:
        result = subprocess.run(
            ['pyinstaller', '--version'],
            capture_output=True, text=True, check=False
        )
        if result.returncode != 0:
            errors.append("PyInstaller not found or not working")
        else:
            print(f"PyInstaller: {result.stdout.strip()}")
    except FileNotFoundError:
        errors.append("PyInstaller not installed")

    if errors:
        print("\nBuild validation failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)


def build_executable(major: int, minor: int, patch: int, build: int) -> None:
    print("\nBuilding executable...")

    main_script        = ROOT_DIR / SCRIPT_NAME
    version_file       = ROOT_DIR / VERSION_FILE
    simple_version_file = ROOT_DIR / "simple_version.txt"
    year_file          = ROOT_DIR / YEAR_FILE
    build_file         = ROOT_DIR / BUILD_FILE
    ui_dir             = ROOT_DIR / 'ui'
    images_dir         = ROOT_DIR / 'images'

    DIST_PATH.mkdir(parents=True, exist_ok=True)
    WORK_PATH.mkdir(parents=True, exist_ok=True)

    sep = ';' if sys.platform == 'win32' else ':'

    import importlib.util

    # Validate sip is importable before invoking PyInstaller
    sip_spec = importlib.util.find_spec('PyQt5.sip')
    if sip_spec is None or sip_spec.origin is None:
        print("ERROR: PyQt5.sip not found — run: pip install PyQt5-sip")
        sys.exit(1)
    print(f"  PyQt5.sip: {sip_spec.origin}")

    cmd = [
        'pyinstaller',
        '--clean',
        '--onefile',
        '--windowed',                          # no console window
        '--name', APP_NAME,
        '--icon', str(ICON_PATH),
        '--distpath', str(DIST_PATH),
        '--workpath', str(WORK_PATH),
        '--version-file', str(version_file),
        # Bundle UI files and images into the executable
        f'--add-data={ui_dir}{sep}ui',
        f'--add-data={images_dir}{sep}images',
        # Bundle version / build tracking files
        f'--add-data={simple_version_file}{sep}.',
        f'--add-data={year_file}{sep}.',
        f'--add-data={build_file}{sep}.',
        # Ensure active env packages are found
        '--paths', str(ROOT_DIR),
        # sip has an ABI-tagged name (e.g. sip.cp313-win_amd64.pyd); collect only
        # its binary so the frozen app can import PyQt5.sip without dragging in
        # every Qt DLL the way --collect-binaries PyQt5 would.
        '--collect-binaries', 'PyQt5.sip',
        '--hidden-import', 'PyQt5.sip',
        '--hidden-import', 'PyQt5.QtCore',
        '--hidden-import', 'PyQt5.QtWidgets',
        '--hidden-import', 'PyQt5.QtGui',
        '--hidden-import', 'PyQt5.uic',
        # Hidden imports that PyInstaller may miss
        '--hidden-import', 'requests',
        '--hidden-import', 'certifi',
        '--hidden-import', 'TM1py',
        # Exclude large unused packages to reduce EXE size
        '--exclude-module', 'tkinter',
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'numpy',
        '--exclude-module', 'scipy',
        '--exclude-module', 'PIL',
        '--exclude-module', 'PyQt5.QtWebEngine',
        '--exclude-module', 'PyQt5.QtWebEngineWidgets',
        '--exclude-module', 'PyQt5.QtMultimedia',
        '--exclude-module', 'PyQt5.QtSql',
        '--exclude-module', 'PyQt5.QtBluetooth',
        '--exclude-module', 'PyQt5.QtLocation',
        '--exclude-module', 'unittest',
        '--exclude-module', 'xmlrpc',
        '--exclude-module', 'http.server',
        str(main_script),
    ]

    print(f"Running PyInstaller...")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")

        exe_name = f"{APP_NAME}.exe" if sys.platform == 'win32' else APP_NAME
        exe_path = DIST_PATH / exe_name
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"Executable: {exe_path}")
            print(f"Size: {size_mb:.2f} MB")
        else:
            print(f"Warning: executable not found at {exe_path}")

    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed!")
        if e.stdout:
            print(f"Stdout:\n{e.stdout[-3000:]}")
        if e.stderr:
            print(f"Stderr:\n{e.stderr[-3000:]}")
        sys.exit(1)


def clean_build_files() -> None:
    spec_file = ROOT_DIR / f"{APP_NAME}.spec"
    if spec_file.exists():
        spec_file.unlink()
        print("Cleaned spec file")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'=' * 60}")
    print(f"  {APP_NAME} Build Script")
    print(f"{'=' * 60}\n")

    args = None
    if docopt:
        try:
            args = docopt(__doc__)
        except SystemExit:
            return

    year = read_year()
    if not (ROOT_DIR / YEAR_FILE).exists():
        write_year(year)

    build = read_build_number()
    major, minor, patch = bump_version(args)
    version_str = f"{major}.{minor}.{patch}.{build}"

    print(f"\nBuilding version: {version_str}")
    print(f"Copyright year:  {year}\n")

    print("Validating environment...")
    validate_environment()

    print("\nGenerating build files...")
    write_build_number(build)
    write_version_file(major, minor, patch, build, year)

    build_executable(major, minor, patch, build)

    print("\nCleaning up...")
    clean_build_files()

    print(f"\n{'=' * 60}")
    print(f"  Build Complete: {APP_NAME} v{version_str}")
    print(f"{'=' * 60}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nBuild cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nBuild failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
