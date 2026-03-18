"""
test_config_manager.py
-----------------------
Unit tests for ConfigManager — covers persistence, CRUD, and all validation
branches without requiring Qt or a live TM1 server.
"""

import json
import os
import pytest

from config_manager import (
    ConfigManager,
    EMPTY_CONNECTION,
    FIELD_NAME, FIELD_CLOUD, FIELD_SECURITY,
    FIELD_ADDRESS, FIELD_PORT, FIELD_INSTANCE,
    FIELD_SSL, FIELD_NAMESPACE, FIELD_GATEWAY,
    PROFILE_FIELDS, DEFAULT_PORTS, NAMESPACE_LABEL,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def cfg(tmp_path):
    """Fresh ConfigManager backed by a temporary directory."""
    return ConfigManager(str(tmp_path))


def _onprem(**overrides) -> dict:
    """Minimal valid On-Prem connection dict with optional field overrides."""
    base = {
        FIELD_NAME:     'MyServer',
        FIELD_CLOUD:    'On-Prem',
        FIELD_SECURITY: 'Standard',
        FIELD_ADDRESS:  'tm1.example.com',
        FIELD_PORT:     '8010',
        FIELD_INSTANCE: 'prod',
        FIELD_SSL:      'True',
        FIELD_NAMESPACE: '',
        FIELD_GATEWAY:  '',
    }
    base.update(overrides)
    return base


def _paoc(**overrides) -> dict:
    base = {
        FIELD_NAME:     'CloudServer',
        FIELD_CLOUD:    'PAoC',
        FIELD_SECURITY: 'Standard',
        FIELD_ADDRESS:  'pa.cloud.ibm.com',
        FIELD_PORT:     '',
        FIELD_INSTANCE: 'myinstance',
        FIELD_SSL:      '',
        FIELD_NAMESPACE: '',
        FIELD_GATEWAY:  '',
    }
    base.update(overrides)
    return base


def _saas(**overrides) -> dict:
    base = {
        FIELD_NAME:      'SaaSServer',
        FIELD_CLOUD:     'PA SaaS',
        FIELD_SECURITY:  'Standard',
        FIELD_ADDRESS:   'pa.saas.ibm.com',
        FIELD_PORT:      '',
        FIELD_INSTANCE:  'mydb',
        FIELD_SSL:       '',
        FIELD_NAMESPACE: 'mytenant',
        FIELD_GATEWAY:   '',
    }
    base.update(overrides)
    return base


# ── load / persistence ────────────────────────────────────────────────────────

class TestLoad:
    def test_empty_on_missing_file(self, cfg):
        assert cfg.get_connection_names() == []

    def test_loads_valid_json(self, tmp_path):
        data = {'Alpha': {**EMPTY_CONNECTION, FIELD_NAME: 'Alpha', FIELD_CLOUD: 'PAoC'}}
        conn_file = tmp_path / 'config' / 'connections.json'
        conn_file.parent.mkdir(parents=True, exist_ok=True)
        conn_file.write_text(json.dumps(data), encoding='utf-8')

        cfg = ConfigManager(str(tmp_path))
        assert 'Alpha' in cfg.get_connection_names()

    def test_corrupt_json_starts_fresh(self, tmp_path):
        conn_file = tmp_path / 'config' / 'connections.json'
        conn_file.parent.mkdir(parents=True, exist_ok=True)
        conn_file.write_text('{ not valid json', encoding='utf-8')

        cfg = ConfigManager(str(tmp_path))
        assert cfg.get_connection_names() == []

    def test_non_dict_root_starts_fresh(self, tmp_path):
        conn_file = tmp_path / 'config' / 'connections.json'
        conn_file.parent.mkdir(parents=True, exist_ok=True)
        conn_file.write_text('["list", "not", "dict"]', encoding='utf-8')

        cfg = ConfigManager(str(tmp_path))
        assert cfg.get_connection_names() == []

    def test_unknown_fields_merged_with_empty(self, tmp_path):
        """Extra keys in the file should not discard EMPTY_CONNECTION defaults."""
        data = {'X': {FIELD_NAME: 'X', FIELD_CLOUD: 'PAoC', 'future_field': 'ignored'}}
        conn_file = tmp_path / 'config' / 'connections.json'
        conn_file.parent.mkdir(parents=True, exist_ok=True)
        conn_file.write_text(json.dumps(data), encoding='utf-8')

        cfg = ConfigManager(str(tmp_path))
        conn = cfg.get_connection('X')
        # All EMPTY_CONNECTION keys must be present
        for key in EMPTY_CONNECTION:
            assert key in conn

    def test_skips_non_dict_entries(self, tmp_path):
        data = {'Good': {**EMPTY_CONNECTION, FIELD_NAME: 'Good'}, 'Bad': 'just a string'}
        conn_file = tmp_path / 'config' / 'connections.json'
        conn_file.parent.mkdir(parents=True, exist_ok=True)
        conn_file.write_text(json.dumps(data), encoding='utf-8')

        cfg = ConfigManager(str(tmp_path))
        assert 'Good' in cfg.get_connection_names()
        assert 'Bad' not in cfg.get_connection_names()


class TestSave:
    def test_save_creates_file(self, tmp_path, cfg):
        cfg.save_connection(_onprem())
        config_file = tmp_path / 'config' / 'connections.json'
        assert config_file.exists()

    def test_roundtrip(self, tmp_path):
        cfg1 = ConfigManager(str(tmp_path))
        cfg1.save_connection(_onprem(name='RoundTrip'))

        cfg2 = ConfigManager(str(tmp_path))
        assert 'RoundTrip' in cfg2.get_connection_names()


# ── get_connection ─────────────────────────────────────────────────────────────

class TestGetConnection:
    def test_returns_copy_of_saved(self, cfg):
        cfg.save_connection(_onprem())
        conn = cfg.get_connection('MyServer')
        assert conn[FIELD_NAME] == 'MyServer'
        assert conn[FIELD_CLOUD] == 'On-Prem'

    def test_returns_empty_for_unknown(self, cfg):
        conn = cfg.get_connection('NoSuchServer')
        assert conn == EMPTY_CONNECTION

    def test_returns_copy_not_reference(self, cfg):
        cfg.save_connection(_onprem())
        conn = cfg.get_connection('MyServer')
        conn[FIELD_ADDRESS] = 'tampered'
        assert cfg.get_connection('MyServer')[FIELD_ADDRESS] == 'tm1.example.com'


# ── get_connection_names ───────────────────────────────────────────────────────

class TestGetConnectionNames:
    def test_sorted(self, cfg):
        for name in ['Zebra', 'Apple', 'Mango']:
            cfg.save_connection(_onprem(**{FIELD_NAME: name}))
        assert cfg.get_connection_names() == ['Apple', 'Mango', 'Zebra']

    def test_empty_when_none(self, cfg):
        assert cfg.get_connection_names() == []


# ── save_connection / validation ──────────────────────────────────────────────

class TestSaveConnection:
    def test_valid_onprem_standard(self, cfg):
        ok, msg = cfg.save_connection(_onprem())
        assert ok is True
        assert msg == ''

    def test_valid_onprem_cam(self, cfg):
        ok, _ = cfg.save_connection(_onprem(security='CAM', namespace='MYCAM'))
        assert ok is True

    def test_valid_onprem_cam_sso(self, cfg):
        ok, _ = cfg.save_connection(_onprem(security='CAM SSO', namespace='NS', gateway='gw.example.com'))
        assert ok is True

    def test_valid_paoc(self, cfg):
        ok, _ = cfg.save_connection(_paoc())
        assert ok is True

    def test_valid_saas(self, cfg):
        ok, _ = cfg.save_connection(_saas())
        assert ok is True

    def test_strips_whitespace_on_save(self, cfg):
        cfg.save_connection(_onprem(**{FIELD_NAME: '  SpacedName  ', FIELD_ADDRESS: ' addr '}))
        assert 'SpacedName' in cfg.get_connection_names()
        assert cfg.get_connection('SpacedName')[FIELD_ADDRESS] == 'addr'

    def test_overwrites_existing(self, cfg):
        cfg.save_connection(_onprem())
        cfg.save_connection(_onprem(**{FIELD_ADDRESS: 'new.example.com'}))
        assert cfg.get_connection('MyServer')[FIELD_ADDRESS] == 'new.example.com'
        assert len(cfg.get_connection_names()) == 1


class TestValidation:
    # ── name ──────────────────────────────────────────────────────────────────

    def test_empty_name_rejected(self, cfg):
        ok, msg = cfg.save_connection(_onprem(**{FIELD_NAME: ''}))
        assert ok is False
        assert 'name' in msg.lower()

    def test_whitespace_name_rejected(self, cfg):
        ok, msg = cfg.save_connection(_onprem(**{FIELD_NAME: '   '}))
        assert ok is False

    # ── cloud type ────────────────────────────────────────────────────────────

    def test_invalid_cloud_rejected(self, cfg):
        ok, msg = cfg.save_connection(_onprem(**{FIELD_CLOUD: 'AWS'}))
        assert ok is False
        assert 'cloud' in msg.lower() or 'type' in msg.lower()

    def test_empty_cloud_rejected(self, cfg):
        ok, _ = cfg.save_connection(_onprem(**{FIELD_CLOUD: ''}))
        assert ok is False

    # ── address ───────────────────────────────────────────────────────────────

    def test_missing_address_rejected(self, cfg):
        ok, msg = cfg.save_connection(_onprem(**{FIELD_ADDRESS: ''}))
        assert ok is False
        assert 'address' in msg.lower()

    # ── port (On-Prem only) ───────────────────────────────────────────────────

    def test_missing_port_rejected(self, cfg):
        ok, msg = cfg.save_connection(_onprem(**{FIELD_PORT: ''}))
        assert ok is False
        assert 'port' in msg.lower()

    def test_non_numeric_port_rejected(self, cfg):
        ok, msg = cfg.save_connection(_onprem(**{FIELD_PORT: 'abc'}))
        assert ok is False
        assert 'port' in msg.lower()

    def test_port_zero_rejected(self, cfg):
        ok, _ = cfg.save_connection(_onprem(**{FIELD_PORT: '0'}))
        assert ok is False

    def test_port_65536_rejected(self, cfg):
        ok, _ = cfg.save_connection(_onprem(**{FIELD_PORT: '65536'}))
        assert ok is False

    def test_port_65535_accepted(self, cfg):
        ok, _ = cfg.save_connection(_onprem(**{FIELD_PORT: '65535'}))
        assert ok is True

    def test_port_1_accepted(self, cfg):
        ok, _ = cfg.save_connection(_onprem(**{FIELD_PORT: '1'}))
        assert ok is True

    # ── instance ──────────────────────────────────────────────────────────────

    def test_missing_instance_rejected_onprem(self, cfg):
        ok, msg = cfg.save_connection(_onprem(**{FIELD_INSTANCE: ''}))
        assert ok is False
        assert 'instance' in msg.lower()

    def test_missing_instance_rejected_paoc(self, cfg):
        ok, _ = cfg.save_connection(_paoc(**{FIELD_INSTANCE: ''}))
        assert ok is False

    # ── SSL (On-Prem only) ────────────────────────────────────────────────────

    def test_invalid_ssl_rejected(self, cfg):
        ok, msg = cfg.save_connection(_onprem(**{FIELD_SSL: 'yes'}))
        assert ok is False
        assert 'ssl' in msg.lower()

    def test_empty_ssl_rejected(self, cfg):
        ok, _ = cfg.save_connection(_onprem(**{FIELD_SSL: ''}))
        assert ok is False

    def test_ssl_true_accepted(self, cfg):
        ok, _ = cfg.save_connection(_onprem(**{FIELD_SSL: 'True'}))
        assert ok is True

    def test_ssl_false_accepted(self, cfg):
        ok, _ = cfg.save_connection(_onprem(**{FIELD_SSL: 'False'}))
        assert ok is True

    # ── security mode (On-Prem) ───────────────────────────────────────────────

    def test_invalid_security_mode_rejected(self, cfg):
        ok, msg = cfg.save_connection(_onprem(**{FIELD_SECURITY: 'Kerberos'}))
        assert ok is False
        assert 'security' in msg.lower()

    def test_cam_requires_namespace(self, cfg):
        ok, msg = cfg.save_connection(_onprem(security='CAM', namespace=''))
        assert ok is False
        assert 'namespace' in msg.lower() or 'cam' in msg.lower()

    def test_cam_sso_requires_namespace(self, cfg):
        ok, _ = cfg.save_connection(_onprem(security='CAM SSO', namespace='', gateway='gw'))
        assert ok is False

    def test_cam_sso_requires_gateway(self, cfg):
        ok, msg = cfg.save_connection(_onprem(security='CAM SSO', namespace='NS', gateway=''))
        assert ok is False
        assert 'gateway' in msg.lower() or 'sso' in msg.lower()

    # ── PA SaaS ───────────────────────────────────────────────────────────────

    def test_saas_requires_tenant_id(self, cfg):
        ok, msg = cfg.save_connection(_saas(**{FIELD_NAMESPACE: ''}))
        assert ok is False
        assert 'tenant' in msg.lower()


# ── delete_connection ─────────────────────────────────────────────────────────

class TestDeleteConnection:
    def test_deletes_existing(self, cfg):
        cfg.save_connection(_onprem())
        result = cfg.delete_connection('MyServer')
        assert result is True
        assert 'MyServer' not in cfg.get_connection_names()

    def test_returns_false_for_nonexistent(self, cfg):
        result = cfg.delete_connection('Ghost')
        assert result is False

    def test_persisted_after_delete(self, tmp_path):
        cfg1 = ConfigManager(str(tmp_path))
        cfg1.save_connection(_onprem())
        cfg1.delete_connection('MyServer')

        cfg2 = ConfigManager(str(tmp_path))
        assert 'MyServer' not in cfg2.get_connection_names()


# ── rename_connection ─────────────────────────────────────────────────────────

class TestRenameConnection:
    def test_renames_successfully(self, cfg):
        cfg.save_connection(_onprem())
        ok, msg = cfg.rename_connection('MyServer', 'NewName')
        assert ok is True
        assert 'NewName' in cfg.get_connection_names()
        assert 'MyServer' not in cfg.get_connection_names()

    def test_name_field_updated(self, cfg):
        cfg.save_connection(_onprem())
        cfg.rename_connection('MyServer', 'NewName')
        assert cfg.get_connection('NewName')[FIELD_NAME] == 'NewName'

    def test_source_not_found(self, cfg):
        ok, msg = cfg.rename_connection('Ghost', 'NewName')
        assert ok is False
        assert 'not found' in msg.lower()

    def test_target_already_exists(self, cfg):
        cfg.save_connection(_onprem(**{FIELD_NAME: 'A'}))
        cfg.save_connection(_onprem(**{FIELD_NAME: 'B'}))
        ok, msg = cfg.rename_connection('A', 'B')
        assert ok is False
        assert 'already exists' in msg.lower()

    def test_rename_to_same_name_allowed(self, cfg):
        """Renaming to itself should be a no-op, not an error."""
        cfg.save_connection(_onprem())
        ok, _ = cfg.rename_connection('MyServer', 'MyServer')
        assert ok is True

    def test_strips_whitespace_from_new_name(self, cfg):
        cfg.save_connection(_onprem())
        ok, _ = cfg.rename_connection('MyServer', '  Trimmed  ')
        assert ok is True
        assert 'Trimmed' in cfg.get_connection_names()


# ── static helpers ────────────────────────────────────────────────────────────

class TestStaticHelpers:
    def test_visible_fields_onprem(self):
        fields = ConfigManager.visible_fields('On-Prem')
        assert FIELD_ADDRESS in fields
        assert FIELD_PORT in fields
        assert FIELD_SSL in fields

    def test_visible_fields_saas(self):
        fields = ConfigManager.visible_fields('PA SaaS')
        assert FIELD_NAMESPACE in fields
        assert FIELD_PORT not in fields

    def test_visible_fields_unknown(self):
        assert ConfigManager.visible_fields('Unknown') == []

    def test_default_port_onprem(self):
        assert ConfigManager.default_port('On-Prem') == '8010'

    def test_default_port_paoc(self):
        assert ConfigManager.default_port('PAoC') == ''

    def test_default_port_saas(self):
        assert ConfigManager.default_port('PA SaaS') == ''

    def test_default_port_unknown(self):
        assert ConfigManager.default_port('Unknown') == ''
