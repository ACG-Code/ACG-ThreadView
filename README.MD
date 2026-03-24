# ACG-ThreadView

A desktop application for real-time monitoring and management of active threads on IBM Planning Analytics / TM1 servers.

---

## Features

- **Live thread monitoring** — polls the server on a configurable interval and displays all active, non-idle threads
- **Multi-connection support** — save and switch between multiple named server connections
- **Broad server compatibility** — supports On-Premises TM1 v11, Planning Analytics on Cloud (PAoC), and Planning Analytics SaaS (v12)
- **Multiple security modes** — Standard, CAM, and CAM SSO authentication for On-Prem servers
- **Thread termination** — right-click any thread row to cancel it
- **Configurable refresh rate** — set the polling interval (5–300 seconds) from the main screen
- **Lock monitoring** — displays Write / Read / Intent-exclusive lock counts per thread

---

## Requirements

| Dependency   | Version  |
|--------------|----------|
| Python       | 3.10+    |
| PyQt5        | 5.15+    |
| TM1py        | latest   |
| requests     | latest   |
| certifi      | latest   |

---

## Quick Start

```bash
git clone https://github.com/acgi/ACG-ThreadView.git
cd ACG-ThreadView
pip install -r requirements.txt
python src/main.py
```

Or run the pre-built executable from `dist/ACG-ThreadView.exe` — no Python installation required.

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

Connections are stored in `config/connections.json` next to the executable (created automatically on first save). Use **Setup → Setup Connection** from the menu to add and manage connections.

### Connection Types

| Type      | Required Fields                              |
|-----------|----------------------------------------------|
| On-Prem   | Address, Port, Instance, SSL, Security Mode  |
| PAoC      | Address, Instance                            |
| PA SaaS   | Address, Instance, Tenant ID                 |

### Security Modes (On-Prem only)

| Mode      | Additional Fields               |
|-----------|---------------------------------|
| Standard  | _(none)_                        |
| CAM       | CAM Namespace ID                |
| CAM SSO   | CAM Namespace ID, SSO Gateway   |

> **Default port:** On-Prem connections default to port `8010` (`HTTPPortNumber` from `Tm1s.cfg`).

---

## Thread Table Columns

| Column          | Description                                                         |
|-----------------|---------------------------------------------------------------------|
| ID              | TM1 thread ID (unique identifier)                                   |
| Name            | Thread name                                                         |
| State           | Current state (Run, Wait, etc.)                                     |
| Type            | Thread type (User, System, etc.)                                    |
| Function        | TM1 function or REST endpoint being executed                        |
| Wait (sec.)     | Time the thread has spent waiting                                   |
| Elapsed (sec.)  | Total elapsed time since the thread started                         |
| W/R/Ix locks    | Write / Read / Intent-exclusive lock counts (e.g. `1/4/0`)         |
| Context         | Thread context (e.g. Workspace, Client)                             |
| Info            | Additional information string                                       |
| Object name     | Name of the object being acted upon                                 |
| Object type     | Type of that object (e.g. Cube, Dimension, Process)                 |

---

## Project Structure

```
ACG-ThreadView/
├── src/
│   ├── main.py               # Application entry point
│   ├── main_window.py        # Main window, dialogs, and core logic
│   ├── config_manager.py     # Connection config persistence and validation
│   ├── base_code.py          # Shared utilities (resource_path, APPLICATION_PATH)
│   ├── build.py              # PyInstaller build script with version management
│   ├── config/
│   │   └── connections.json  # Saved connection profiles (auto-created)
│   ├── ui/
│   │   ├── main_window.ui    # Main window layout (Qt Designer)
│   │   └── setup_window.ui   # Connection setup dialog (Qt Designer)
│   └── images/
│       ├── ACG.ico           # Application icon
│       └── acg_logo.jpg      # Logo asset
├── tests/                    # Unit tests (pytest)
├── dist/                     # Build output (generated)
├── build/                    # PyInstaller work dir (generated)
├── USER_GUIDE.md             # End-user guide with step-by-step instructions
└── LICENSE                   # MIT License
```

---

## Running Tests

```bash
pytest tests/
```

The test suite covers all `ConfigManager` functionality including connection CRUD, field validation, and error handling.

---

## Documentation

- **[USER_GUIDE.md](USER_GUIDE.md)** — step-by-step instructions for end users

---

*© Application Consulting Group, Inc.*
