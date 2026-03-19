# ACG-ThreadView

A desktop application for monitoring and managing active threads on IBM Planning Analytics / TM1 servers in real time.

---

## Features

- **Live thread monitoring** — polls the server on a configurable interval and displays all active threads
- **Multi-connection support** — save and switch between multiple named server connections
- **Broad server compatibility** — supports On-Premises TM1, Planning Analytics on Cloud (PAoC), and Planning Analytics SaaS (v12)
- **Multiple security modes** — Standard, CAM, and CAM SSO authentication for On-Prem servers
- **Thread termination** — right-click any thread row to kill it
- **Configurable refresh rate** — set the polling interval (5–300 seconds) from the main screen

---

## Requirements

| Dependency | Version  |
|---|---|
| Python     | 3.10+    |
| PyQt5      | 5.15+    |
| TM1py      | latest   |
| requests   | latest   |
| certifi    | latest   |

---

## Installation

```bash
git clone https://github.com/acgi/ACG-ThreadView.git
cd ACG-ThreadView
pip install -r requirements.txt
python src/main.py
```

---

## Building the Executable

The build script produces a single self-contained `.exe` via PyInstaller.

```bash
# Standard build (no version bump)
python src/build.py

# Bump patch version  (e.g. 1.0.0 → 1.0.1)
python src/build.py --patch

# Bump minor version  (e.g. 1.0.1 → 1.1.0)
python src/build.py --minor

# Bump major version  (e.g. 1.1.0 → 2.0.0)
python src/build.py --major
```

Output is written to `dist/ACG-ThreadView.exe`.

**Build dependencies:**
```bash
pip install pyinstaller docopt
```

---

## Configuration

Connections are stored in `config/connections.json` next to the executable (created automatically on first save).

### Connection Types

| Type     | Required Fields                             |
|---|---|
| On-Prem  | Address, Port, Instance, SSL, Security Mode |
| PAoC     | Address, Instance                           |
| PA SaaS  | Address, Instance, Tenant ID                |

### Security Modes (On-Prem only)

| Mode     | Additional Fields              |
|---|---|
| Standard | _(none)_                       |
| CAM      | CAM Namespace ID               |
| CAM SSO  | CAM Namespace ID, SSO Gateway  |

---

## Thread Table Columns

| Column          | Description                                  |
|---|---|
| ID              | TM1 thread ID                                |
| Name            | Thread name                                  |
| State           | Current state (Running, Waiting, etc.)       |
| Type            | Thread type                                  |
| Function        | TM1 function being executed                  |
| Wait (sec.)     | Time spent waiting                           |
| Elapsed (sec.)  | Total elapsed time                           |
| W/R/Ix locks    | Write / Read / Intent-exclusive lock counts  |
| Context         | Thread context                               |
| Info            | Additional info                              |
| Object name     | Object being acted upon                      |
| Object type     | Type of that object                          |

---

## Project Structure

```
ACG-ThreadView/
├── src/
│   ├── main.py               # Application entry point
│   ├── main_window.py        # Main window logic
│   ├── config_manager.py     # Connection config persistence
│   ├── base_code.py          # Shared utilities (resource_path, APPLICATION_PATH)
│   ├── build.py              # PyInstaller build script
│   ├── ui/
│   │   ├── main_window.ui    # Main window layout (Qt Designer)
│   │   └── setup_window.ui   # Connection setup dialog (Qt Designer)
│   └── images/
│       └── ACG.ico           # Application icon
├── tests/                    # Unit tests
├── dist/                     # Build output (generated)
└── build/                    # PyInstaller work dir (generated)
```

---

## Running Tests

```bash
pytest tests/
```

---

*© Application Consulting Group, Inc.*
