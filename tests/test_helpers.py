"""
test_helpers.py
---------------
Unit tests for the pure helper functions in main_window.py.

Qt is not required — conftest.py stubs out all PyQt5 modules before import.
TM1py / TM1Service are also stubbed, so no live server is needed.
"""

import pytest
from unittest.mock import MagicMock

# conftest.py has already stubbed PyQt5; import helpers directly.
from main_window import (
    _thread_value,
    _strip_protocol,
    _build_tm1_params,
    _friendly_error,
    _get_rest_service,
)
from config_manager import (
    FIELD_CLOUD, FIELD_ADDRESS, FIELD_PORT, FIELD_INSTANCE,
    FIELD_SSL, FIELD_NAMESPACE, FIELD_GATEWAY, FIELD_SECURITY,
)


# ── _thread_value ─────────────────────────────────────────────────────────────

class TestThreadValue:
    def test_first_key_match_dict(self):
        t = {'ID': '42', 'Name': 'Main'}
        assert _thread_value(t, 'ID', 'id') == '42'

    def test_second_key_fallback_dict(self):
        t = {'id': '7'}
        assert _thread_value(t, 'ID', 'id') == '7'

    def test_no_match_returns_empty(self):
        t = {'other': 'x'}
        assert _thread_value(t, 'ID', 'id') == ''

    def test_object_attribute_lookup(self):
        obj = MagicMock()
        obj.id = 'obj-99'
        # Key 'ID' → lowercased attr 'id'
        assert _thread_value(obj, 'ID') == 'obj-99'

    def test_object_multi_key_fallback(self):
        obj = MagicMock(spec=[])          # no attributes
        obj.wait_sec = 3.5
        # 'WaitSec' → 'waitsec' (not present), 'Wait' → 'wait' (not present),
        # 'wait_sec' → 'wait_sec' (present)
        result = _thread_value(obj, 'WaitSec', 'Wait', 'wait_sec')
        assert result == 3.5

    def test_none_value_in_dict_not_returned(self):
        """A key whose value is None in a dict is treated as found (returns None, not '')."""
        t = {'ID': None}
        assert _thread_value(t, 'ID') is None

    def test_empty_string_value_returned(self):
        t = {'Name': ''}
        assert _thread_value(t, 'Name') == ''


# ── _strip_protocol ───────────────────────────────────────────────────────────

class TestStripProtocol:
    def test_strips_https(self):
        assert _strip_protocol('https://server.example.com') == 'server.example.com'

    def test_strips_http(self):
        assert _strip_protocol('http://server.example.com') == 'server.example.com'

    def test_no_prefix_unchanged(self):
        assert _strip_protocol('server.example.com') == 'server.example.com'

    def test_strips_trailing_slash(self):
        assert _strip_protocol('https://server.example.com/') == 'server.example.com'

    def test_strips_multiple_trailing_slashes(self):
        assert _strip_protocol('http://server.example.com///') == 'server.example.com'

    def test_case_insensitive_prefix(self):
        assert _strip_protocol('HTTPS://server.example.com') == 'server.example.com'

    def test_preserves_path_after_host(self):
        assert _strip_protocol('https://server.example.com/path') == 'server.example.com/path'

    def test_empty_string(self):
        assert _strip_protocol('') == ''

    def test_strips_https_not_http_when_both_would_match(self):
        """https:// prefix should be removed, not leave 's://'"""
        result = _strip_protocol('https://host')
        assert result == 'host'


# ── _build_tm1_params ─────────────────────────────────────────────────────────

class TestBuildTm1Params:
    def _onprem(self, **overrides):
        base = {
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

    # On-Prem Standard
    def test_onprem_standard_address_and_port(self):
        params = _build_tm1_params(self._onprem(), 'user', 'pass')
        assert params['address'] == 'tm1.example.com'
        assert params['port'] == 8010

    def test_onprem_standard_ssl_true(self):
        params = _build_tm1_params(self._onprem(**{FIELD_SSL: 'True'}), 'u', 'p')
        assert params['ssl'] is True

    def test_onprem_standard_ssl_false(self):
        params = _build_tm1_params(self._onprem(**{FIELD_SSL: 'False'}), 'u', 'p')
        assert params['ssl'] is False

    def test_onprem_standard_no_namespace(self):
        params = _build_tm1_params(self._onprem(), 'u', 'p')
        assert 'namespace' not in params
        assert 'gateway' not in params

    def test_onprem_standard_strips_protocol_from_address(self):
        params = _build_tm1_params(self._onprem(**{FIELD_ADDRESS: 'https://tm1.example.com'}), 'u', 'p')
        assert params['address'] == 'tm1.example.com'

    def test_onprem_standard_session_context(self):
        params = _build_tm1_params(self._onprem(), 'u', 'p')
        assert params.get('session_context') == 'ACG Thread View'

    def test_onprem_standard_no_instance_key(self):
        """instance must NOT be passed for On-Prem (TM1py v2 treats it as OpenShift trigger)."""
        params = _build_tm1_params(self._onprem(), 'u', 'p')
        assert 'instance' not in params

    # On-Prem CAM
    def test_onprem_cam_includes_namespace(self):
        conn = self._onprem(**{FIELD_SECURITY: 'CAM', FIELD_NAMESPACE: 'MYCAM'})
        params = _build_tm1_params(conn, 'u', 'p')
        assert params['namespace'] == 'MYCAM'
        assert 'gateway' not in params

    # On-Prem CAM SSO
    def test_onprem_cam_sso_includes_namespace_and_gateway(self):
        conn = self._onprem(**{FIELD_SECURITY: 'CAM SSO', FIELD_NAMESPACE: 'NS', FIELD_GATEWAY: 'gw.example.com'})
        params = _build_tm1_params(conn, 'u', 'p')
        assert params['namespace'] == 'NS'
        assert params['gateway'] == 'gw.example.com'

    # PAoC
    def test_paoc_base_url_format(self):
        conn = {
            FIELD_CLOUD:    'PAoC',
            FIELD_ADDRESS:  'pa.cloud.ibm.com',
            FIELD_INSTANCE: 'myinstance',
        }
        params = _build_tm1_params(conn, 'user', 'pass')
        assert 'https://pa.cloud.ibm.com/tm1/api/myinstance/' in params['base_url']

    def test_paoc_namespace_is_ldap(self):
        conn = {FIELD_CLOUD: 'PAoC', FIELD_ADDRESS: 'pa.cloud.ibm.com', FIELD_INSTANCE: 'inst'}
        params = _build_tm1_params(conn, 'u', 'p')
        assert params['namespace'] == 'LDAP'

    def test_paoc_ssl_true(self):
        conn = {FIELD_CLOUD: 'PAoC', FIELD_ADDRESS: 'pa.cloud.ibm.com', FIELD_INSTANCE: 'inst'}
        params = _build_tm1_params(conn, 'u', 'p')
        assert params['ssl'] is True

    def test_paoc_strips_protocol(self):
        conn = {FIELD_CLOUD: 'PAoC', FIELD_ADDRESS: 'https://pa.cloud.ibm.com/', FIELD_INSTANCE: 'inst'}
        params = _build_tm1_params(conn, 'u', 'p')
        assert 'https://https://' not in params['base_url']
        assert params['base_url'].startswith('https://pa.cloud.ibm.com')

    # PA SaaS
    def test_saas_base_url_format(self):
        conn = {
            FIELD_CLOUD:     'PA SaaS',
            FIELD_ADDRESS:   'pa.saas.ibm.com',
            FIELD_INSTANCE:  'mydb',
            FIELD_NAMESPACE: 'mytenant',
        }
        params = _build_tm1_params(conn, 'apikey', 'mykey')
        assert 'mytenant' in params['base_url']
        assert 'mydb' in params['base_url']

    def test_saas_user_forced_to_apikey(self):
        conn = {
            FIELD_CLOUD:     'PA SaaS',
            FIELD_ADDRESS:   'pa.saas.ibm.com',
            FIELD_INSTANCE:  'mydb',
            FIELD_NAMESPACE: 'mytenant',
        }
        params = _build_tm1_params(conn, 'realuser', 'mykey')
        assert params['user'] == 'apikey'

    def test_saas_ssl_true(self):
        conn = {FIELD_CLOUD: 'PA SaaS', FIELD_ADDRESS: 'pa.saas.ibm.com',
                FIELD_INSTANCE: 'db', FIELD_NAMESPACE: 'tenant'}
        params = _build_tm1_params(conn, 'u', 'p')
        assert params['ssl'] is True

    def test_saas_async_mode(self):
        conn = {FIELD_CLOUD: 'PA SaaS', FIELD_ADDRESS: 'pa.saas.ibm.com',
                FIELD_INSTANCE: 'db', FIELD_NAMESPACE: 'tenant'}
        params = _build_tm1_params(conn, 'u', 'p')
        assert params.get('async_requests_mode') is True


# ── _friendly_error ───────────────────────────────────────────────────────────

class TestFriendlyError:
    def _conn(self, ssl='False'):
        return {FIELD_SSL: ssl}

    def test_generic_error_returned_as_is(self):
        exc = Exception('Some random error')
        result = _friendly_error(exc, self._conn())
        assert result == 'Some random error'

    def test_bad_status_line_ssl_disabled_suggests_enable(self):
        exc = Exception('BadStatusLine detected')
        result = _friendly_error(exc, self._conn(ssl='False'))
        assert 'Enable' in result
        assert 'SSL' in result

    def test_bad_status_line_ssl_enabled_suggests_disable(self):
        exc = Exception('BadStatusLine detected')
        result = _friendly_error(exc, self._conn(ssl='True'))
        assert 'Disable' in result
        assert 'SSL' in result

    def test_connection_aborted_with_tls_alert_byte_hex(self):
        exc = Exception('Connection aborted \\x15 something')
        result = _friendly_error(exc, self._conn(ssl='False'))
        assert 'SSL' in result
        assert 'Enable' in result

    def test_connection_aborted_with_tls_alert_real_byte(self):
        exc = Exception('Connection aborted \x15 something')
        result = _friendly_error(exc, self._conn(ssl='True'))
        assert 'SSL' in result
        assert 'Disable' in result

    def test_ssl_mismatch_mentions_plain_http_when_ssl_on(self):
        exc = Exception('BadStatusLine')
        result = _friendly_error(exc, self._conn(ssl='True'))
        assert 'plain HTTP' in result

    def test_ssl_mismatch_mentions_tls_when_ssl_off(self):
        exc = Exception('BadStatusLine')
        result = _friendly_error(exc, self._conn(ssl='False'))
        assert 'TLS' in result or 'HTTPS' in result


# ── _get_rest_service ─────────────────────────────────────────────────────────

class TestGetRestService:
    def test_finds_tm1_rest_attr(self):
        tm1 = MagicMock(spec=['_tm1_rest'])
        rest = MagicMock()
        tm1._tm1_rest = rest
        assert _get_rest_service(tm1) is rest

    def test_falls_back_to_rest_attr(self):
        tm1 = MagicMock(spec=['rest'])
        rest = MagicMock()
        tm1.rest = rest
        assert _get_rest_service(tm1) is rest

    def test_prefers_tm1_rest_over_rest(self):
        tm1 = MagicMock(spec=['_tm1_rest', 'rest'])
        primary = MagicMock()
        fallback = MagicMock()
        tm1._tm1_rest = primary
        tm1.rest = fallback
        assert _get_rest_service(tm1) is primary

    def test_raises_when_no_attr_found(self):
        tm1 = MagicMock(spec=[])   # no attributes at all
        with pytest.raises(AttributeError, match='RestService'):
            _get_rest_service(tm1)
