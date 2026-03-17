"""
config_manager.py
-----------------
Manages TM1 connection configurations stored as a JSON file at:
    <APPLICATION_PATH>/config/connections.json

Supports three connection profiles:
    - On-Prem   : TM1 Server v11, on-premises
                  Fields: address, port, instance, ssl
                  Security modes: Standard (basic), CAM (+ namespace), CAM SSO (+ namespace + gateway)
    - PAoC      : Planning Analytics on Cloud v11
                  Fields: address, instance
    - PA SaaS   : Planning Analytics SaaS v12
                  Fields: address, instance, namespace (used as Tenant ID)
"""

import json
import os

# ── field keys ────────────────────────────────────────────────────────────────
FIELD_NAME       = 'name'
FIELD_CLOUD      = 'cloud_type'    # 'On-Prem' | 'PAoC' | 'PA SaaS'
FIELD_SECURITY   = 'security_mode' # On-Prem only: 'Standard' | 'CAM' | 'CAM SSO'
FIELD_ADDRESS    = 'address'
FIELD_PORT       = 'port'
FIELD_INSTANCE   = 'instance'
FIELD_SSL        = 'ssl'           # 'True' | 'False'
FIELD_NAMESPACE  = 'namespace'     # CAM Namespace ID (On-Prem CAM/SSO) or Tenant ID (PA SaaS)
FIELD_GATEWAY    = 'gateway'       # SSO Gateway (On-Prem CAM SSO only)

# Security mode options (On-Prem only)
SECURITY_OPTIONS = ['Standard', 'CAM', 'CAM SSO']

# Fields required per cloud type (security-mode-dependent fields handled separately)
PROFILE_FIELDS = {
    'On-Prem': [FIELD_ADDRESS, FIELD_PORT, FIELD_INSTANCE, FIELD_SSL],
    'PAoC':    [FIELD_ADDRESS, FIELD_INSTANCE],
    'PA SaaS': [FIELD_ADDRESS, FIELD_INSTANCE, FIELD_NAMESPACE],
}

# Human-readable label for the namespace field per cloud type
NAMESPACE_LABEL = {
    'On-Prem': 'CAM Namespace ID',
    'PAoC':    'CAM Namespace ID',
    'PA SaaS': 'Tenant ID',
}

# Default port per profile (empty string = not applicable)
DEFAULT_PORTS = {
    'On-Prem': '8010',
    'PAoC':    '',
    'PA SaaS': '',
}

EMPTY_CONNECTION = {
    FIELD_NAME:      '',
    FIELD_CLOUD:     '',
    FIELD_SECURITY:  'Standard',
    FIELD_ADDRESS:   '',
    FIELD_PORT:      '',
    FIELD_INSTANCE:  '',
    FIELD_SSL:       '',
    FIELD_NAMESPACE: '',
    FIELD_GATEWAY:   '',
}


class ConfigManager:
    """Loads, saves and validates TM1 connection configurations."""

    def __init__(self, app_path: str):
        self._config_dir  = os.path.join(app_path, 'config')
        self._config_file = os.path.join(self._config_dir, 'connections.json')
        self._connections: dict[str, dict] = {}
        self._ensure_dir()
        self.load()

    # ── persistence ───────────────────────────────────────────────────────────

    def _ensure_dir(self):
        os.makedirs(self._config_dir, exist_ok=True)

    def load(self):
        """Load connections from disk; silently start fresh if file is absent/corrupt."""
        if not os.path.isfile(self._config_file):
            self._connections = {}
            return
        try:
            with open(self._config_file, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self._connections = {
                    k: {**EMPTY_CONNECTION, **v}
                    for k, v in data.items()
                    if isinstance(v, dict)
                }
        except (json.JSONDecodeError, OSError):
            self._connections = {}

    def save(self):
        """Persist all connections to disk."""
        self._ensure_dir()
        with open(self._config_file, 'w', encoding='utf-8') as fh:
            json.dump(self._connections, fh, indent=4)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def get_connection_names(self) -> list[str]:
        """Return sorted list of saved connection names."""
        return sorted(self._connections.keys())

    def get_connection(self, name: str) -> dict:
        """Return a copy of the named connection, or an empty template."""
        return dict(self._connections.get(name, EMPTY_CONNECTION))

    def save_connection(self, data: dict) -> tuple[bool, str]:
        """
        Validate and save a connection.

        Returns
        -------
        (True, '')           on success
        (False, error_msg)   on validation failure
        """
        ok, msg = self._validate(data)
        if not ok:
            return False, msg

        name = data[FIELD_NAME].strip()
        self._connections[name] = {k: v.strip() for k, v in data.items()}
        self.save()
        return True, ''

    def delete_connection(self, name: str) -> bool:
        """Remove a connection by name. Returns True if it existed."""
        if name in self._connections:
            del self._connections[name]
            self.save()
            return True
        return False

    def rename_connection(self, old_name: str, new_name: str) -> tuple[bool, str]:
        new_name = new_name.strip()
        if old_name not in self._connections:
            return False, f'Connection "{old_name}" not found.'
        if new_name in self._connections and new_name != old_name:
            return False, f'A connection named "{new_name}" already exists.'
        self._connections[new_name] = self._connections.pop(old_name)
        self._connections[new_name][FIELD_NAME] = new_name
        self.save()
        return True, ''

    # ── validation ────────────────────────────────────────────────────────────

    def _validate(self, data: dict) -> tuple[bool, str]:
        name       = data.get(FIELD_NAME, '').strip()
        cloud_type = data.get(FIELD_CLOUD, '').strip()

        if not name:
            return False, 'Connection name is required.'
        if cloud_type not in PROFILE_FIELDS:
            return False, f'Cloud type must be one of: {", ".join(PROFILE_FIELDS)}.'

        required = PROFILE_FIELDS[cloud_type]

        if FIELD_ADDRESS in required and not data.get(FIELD_ADDRESS, '').strip():
            return False, 'Address is required.'

        if FIELD_PORT in required:
            port_str = data.get(FIELD_PORT, '').strip()
            if not port_str:
                return False, 'HTTP Port is required.'
            try:
                port = int(port_str)
                if not (1 <= port <= 65535):
                    raise ValueError
            except ValueError:
                return False, 'HTTP Port must be a number between 1 and 65535.'

        if FIELD_INSTANCE in required and not data.get(FIELD_INSTANCE, '').strip():
            return False, 'Instance name is required.'

        if FIELD_SSL in required and data.get(FIELD_SSL, '').strip() not in ('True', 'False'):
            return False, 'SSL must be True or False.'

        # Security-mode-specific validation (On-Prem only)
        if cloud_type == 'On-Prem':
            security = data.get(FIELD_SECURITY, 'Standard').strip()
            if security not in SECURITY_OPTIONS:
                return False, f'Security mode must be one of: {", ".join(SECURITY_OPTIONS)}.'
            if security in ('CAM', 'CAM SSO') and not data.get(FIELD_NAMESPACE, '').strip():
                return False, 'CAM Namespace ID is required for CAM and CAM SSO authentication.'
            if security == 'CAM SSO' and not data.get(FIELD_GATEWAY, '').strip():
                return False, 'SSO Gateway is required for CAM SSO authentication.'

        # PA SaaS requires Tenant ID (stored in namespace)
        if cloud_type == 'PA SaaS' and not data.get(FIELD_NAMESPACE, '').strip():
            return False, 'Tenant ID is required for PA SaaS connections.'

        return True, ''

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def visible_fields(cloud_type: str) -> list[str]:
        """Return the list of relevant field keys for a given cloud type."""
        return PROFILE_FIELDS.get(cloud_type, [])

    @staticmethod
    def default_port(cloud_type: str) -> str:
        return DEFAULT_PORTS.get(cloud_type, '')