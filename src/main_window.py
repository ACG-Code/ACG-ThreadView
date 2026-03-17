from src.base_code import resource_path, APPLICATION_PATH
from src.config_manager import (
    ConfigManager,
    FIELD_NAME, FIELD_CLOUD, FIELD_SECURITY, FIELD_ADDRESS, FIELD_PORT,
    FIELD_INSTANCE, FIELD_SSL, FIELD_NAMESPACE, FIELD_GATEWAY,
    NAMESPACE_LABEL, DEFAULT_PORTS, SECURITY_OPTIONS,
)
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QPushButton, QTableWidget, QTableWidgetItem,
    QStatusBar, QDialog, QComboBox, QLineEdit, QMessageBox, QLabel, QSpinBox,
    QFormLayout, QVBoxLayout, QDialogButtonBox, QMenu, QAction, QTextBrowser,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5 import uic
import sys
import os

APP_NAME    = 'ACG-ThreadView'
APP_VERSION = '1.0.0'
APP_BUILD   = '1.0.0'

# Ordered list shown in the IBM Cloud combobox
CLOUD_OPTIONS = ['On-Prem', 'PAoC', 'PA SaaS']


# Table column indices matching the tbl_threads header order
_COL_ID, _COL_NAME, _COL_STATE, _COL_TYPE, _COL_FUNCTION = 0, 1, 2, 3, 4
_COL_WAIT, _COL_ELAPSED, _COL_LOCK = 5, 6, 7
_COL_CONTEXT, _COL_INFO, _COL_OBJ_NAME, _COL_OBJ_TYPE = 8, 9, 10, 11


def _thread_value(thread, *keys):
    """Extract a value from a thread dict or object, trying multiple key names."""
    for k in keys:
        if isinstance(thread, dict):
            if k in thread:
                return thread[k]
        else:
            attr = k.lower().replace(' ', '_')
            if hasattr(thread, attr):
                return getattr(thread, attr)
    return ''


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        uic.loadUi(resource_path('ui/main_window.ui'), self)
        self.setWindowIcon(QIcon(resource_path(r'images/ACG.ico')))
        self.setWindowTitle(f'{APP_NAME} - {APP_VERSION}')

        self.action     = self.findChild(QPushButton, 'btn_action')
        self.exit       = self.findChild(QPushButton, 'btn_exit')
        self.table       = self.findChild(QTableWidget, 'tbl_threads')
        self.status      = self.findChild(QStatusBar, 'statusbar')
        self.cmb_conn    = self.findChild(QComboBox, 'cmb_connection')
        self.spn_refresh = self.findChild(QSpinBox, 'spn_refresh')

        # Thread table column widths
        for col, width in enumerate([100, 200, 100, 100, 300, 100, 100, 100, 200, 100, 100, 100]):
            self.table.setColumnWidth(col, width)

        # Hide the vertical header (row index numbers)
        self.table.verticalHeader().setVisible(False)

        # Right-click context menu for killing threads
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_thread_context_menu)

        self.status.setSizeGripEnabled(False)

        self._tm1   = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._fetch_threads)
        self.spn_refresh.valueChanged.connect(self._on_refresh_changed)

        self.action.setText('Start')
        self.status.showMessage('Ready')

        self.action.clicked.connect(self._toggle_monitoring)
        self.exit.clicked.connect(self.close)

        # Menu → Setup → Setup Connection
        self.actionSetup_Connection.triggered.connect(self.open_setup)

        # Menu → Help → About
        self.actionAbout.triggered.connect(self.open_about)

        self._load_connection_list()
        self.show()

    def open_setup(self):
        dlg = SetupWindow(APPLICATION_PATH, parent=self)
        dlg.exec_()
        self._load_connection_list()

    def open_about(self):
        dlg = AboutDialog(parent=self)
        dlg.exec_()

    def _load_connection_list(self):
        current = self.cmb_conn.currentText()
        self.cmb_conn.blockSignals(True)
        self.cmb_conn.clear()
        cfg = ConfigManager(APPLICATION_PATH)
        self.cmb_conn.addItems(cfg.get_connection_names())
        idx = self.cmb_conn.findText(current)
        self.cmb_conn.setCurrentIndex(max(idx, 0))
        self.cmb_conn.blockSignals(False)

    # ── monitoring ────────────────────────────────────────────────────────────

    def _toggle_monitoring(self):
        if self.action.text() == 'Start':
            self._start_monitoring()
        else:
            self._stop_monitoring()

    def _start_monitoring(self):
        conn_name = self.cmb_conn.currentText().strip()
        if not conn_name:
            QMessageBox.warning(self, 'No Connection', 'Please select a connection first.')
            return

        cfg  = ConfigManager(APPLICATION_PATH)
        conn = cfg.get_connection(conn_name)

        cloud = conn.get(FIELD_CLOUD, '')
        dlg = LoginDialog(conn_name, api_key_only=(cloud == 'PA SaaS'), parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return

        user, password = dlg.credentials()

        try:
            from TM1py import TM1Service
            params = _build_tm1_params(conn, user, password)
            self._tm1 = TM1Service(**params)
        except Exception as exc:
            self._tm1 = None
            QMessageBox.critical(self, 'Connection Error', _friendly_error(exc, conn))
            return

        self.action.setText('Stop')
        self.status.showMessage(f'Connected to {conn_name}')
        self._fetch_threads()
        self._timer.start(self.spn_refresh.value() * 1000)

    def _stop_monitoring(self):
        self._timer.stop()
        if self._tm1 is not None:
            try:
                self._tm1.logout()
            except Exception:
                pass
            self._tm1 = None
        self.action.setText('Start')
        self.status.showMessage('Disconnected')
        self.table.setRowCount(0)

    def _fetch_threads(self):
        if self._tm1 is None:
            return
        try:
            threads = _get_threads(self._tm1)
            self._populate_table(threads)
            self.status.showMessage(f'Refreshed — {len(threads)} thread(s)')
        except Exception as exc:
            self._stop_monitoring()
            QMessageBox.critical(self, 'Fetch Error', str(exc))

    def _populate_table(self, threads):
        self.table.setRowCount(0)
        for t in threads:
            row = self.table.rowCount()
            self.table.insertRow(row)
            values = [
                _thread_value(t, 'ID',         'id'),
                _thread_value(t, 'Name',        'name'),
                _thread_value(t, 'State',       'state'),
                _thread_value(t, 'Type',        'type'),
                _thread_value(t, 'Function',    'function'),
                _thread_value(t, 'WaitSec',     'Wait',     'wait_sec'),
                _thread_value(t, 'ElapsedSec',  'Elapsed',  'elapsed_sec'),
                _thread_value(t, 'Lock',        'lock'),
                _thread_value(t, 'Context',     'context'),
                _thread_value(t, 'Info',        'info'),
                _thread_value(t, 'ObjectName',  'Object',   'object_name'),
                _thread_value(t, 'ObjectType',  'object_type'),
            ]
            for col, val in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(val) if val is not None else ''))

    def _on_refresh_changed(self, seconds: int):
        """Restart the timer with the new interval if monitoring is active."""
        if self._timer.isActive():
            self._timer.start(seconds * 1000)

    def _show_thread_context_menu(self, pos):
        """Right-click context menu on the threads table."""
        if self._tm1 is None:
            return
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        thread_id_item = self.table.item(row, _COL_ID)
        if thread_id_item is None:
            return
        thread_id = thread_id_item.text()

        menu = QMenu(self)
        kill_action = QAction(f'Cancel thread {thread_id}', self)
        kill_action.triggered.connect(lambda: self._cancel_thread(thread_id))
        menu.addAction(kill_action)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _cancel_thread(self, thread_id: str):
        """Cancel/kill a TM1 thread by ID."""
        reply = QMessageBox.question(
            self, 'Cancel Thread',
            f'Cancel thread ID {thread_id}?',
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            _cancel_thread_rest(self._tm1, int(thread_id))
            self.status.showMessage(f'Thread {thread_id} cancelled.')
            self._fetch_threads()
        except Exception as exc:
            QMessageBox.warning(self, 'Cancel Failed', str(exc))

    def closeEvent(self, event):
        self._stop_monitoring()
        super().closeEvent(event)


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_threads(tm1) -> list:
    """Fetch active threads directly via REST, bypassing TM1py's deprecated wrapper."""
    # Filter out idle threads and our own polling request (works on v11 and v12)
    url = "/Threads?$filter=State ne 'Idle' and Function ne 'GET /Threads' and Function ne 'GET /api/v1/Threads'"
    try:
        return tm1._rest.GET(url).json()['value']
    except Exception:
        # Fall back to unfiltered if OData filter isn't supported
        return tm1._rest.GET('/Threads').json()['value']


def _cancel_thread_rest(tm1, thread_id: int) -> None:
    """Cancel a thread directly via REST, bypassing TM1py's deprecated wrapper."""
    url = f"/Threads('{thread_id}')/tm1.CancelOperation"
    tm1._rest.POST(url)


def _strip_protocol(address: str) -> str:
    """Remove any http:// or https:// prefix and trailing slashes from an address."""
    for prefix in ('https://', 'http://'):
        if address.lower().startswith(prefix):
            address = address[len(prefix):]
            break
    return address.rstrip('/')


def _build_tm1_params(conn: dict, user: str, password: str) -> dict:
    cloud   = conn.get(FIELD_CLOUD, '')
    address = _strip_protocol(conn.get(FIELD_ADDRESS, ''))
    params  = {'user': user, 'password': password}

    params['session_context'] = 'ACG Thread View'

    if cloud == 'On-Prem':
        # v11 on-prem: address + port — do NOT pass 'instance',
        # as TM1py v2 treats it as an OpenShift/v12 auth trigger.
        security = conn.get(FIELD_SECURITY, 'Standard')
        params['address'] = address
        params['port']    = int(conn.get(FIELD_PORT) or '8010')
        params['ssl']     = conn.get(FIELD_SSL, 'False') == 'True'
        if security == 'CAM':
            params['namespace'] = conn.get(FIELD_NAMESPACE, '')
        elif security == 'CAM SSO':
            params['namespace'] = conn.get(FIELD_NAMESPACE, '')
            params['gateway']   = conn.get(FIELD_GATEWAY, '')

    elif cloud == 'PAoC':
        # PAoC always uses CAM auth with LDAP namespace
        instance = conn.get(FIELD_INSTANCE, '')
        params['base_url']           = f'https://{address}/tm1/api/{instance}/'
        params['namespace']          = 'LDAP'
        params['ssl']                = True
        params['verify']             = True
        params['async_requests_mode'] = True

    elif cloud == 'PA SaaS':
        # PA SaaS uses TenantId + DatabaseName in URL; user is always 'apikey'
        tenant   = conn.get(FIELD_NAMESPACE, '')
        database = conn.get(FIELD_INSTANCE, '')
        params['base_url']            = f'https://{address}/api/{tenant}/v0/tm1/{database}/'
        params['user']                = 'apikey'
        params['ssl']                 = True
        params['verify']              = True
        params['async_requests_mode'] = True

    return params


def _friendly_error(exc: Exception, conn: dict) -> str:
    """Return a user-readable connection error message."""
    msg = str(exc)
    # TLS alert bytes in the response mean the server expects the opposite SSL mode
    if 'BadStatusLine' in msg or ('Connection aborted' in msg and ('\\x15' in msg or '\x15' in msg)):
        current_ssl = conn.get(FIELD_SSL, 'False') == 'True'
        suggestion  = 'Disable' if current_ssl else 'Enable'
        return (
            f'Connection aborted — SSL mismatch detected.\n\n'
            f'The server responded with a {"plain HTTP" if current_ssl else "TLS/HTTPS"} '
            f'handshake, but the connection is configured with '
            f'SSL {"enabled" if current_ssl else "disabled"}.\n\n'
            f'Fix: {suggestion} SSL for this connection in Setup → Setup Connection.'
        )
    return msg


# ── Login dialog ──────────────────────────────────────────────────────────────

class LoginDialog(QDialog):
    def __init__(self, conn_name: str, api_key_only: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'Connect to {conn_name}')
        self.setModal(True)
        self._api_key_only = api_key_only

        self._user = QLineEdit()
        self._pass = QLineEdit()
        self._pass.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        if api_key_only:
            self.setFixedSize(280, 85)
            form.addRow('API Key:', self._pass)
            self._pass.setFocus()
        else:
            self.setFixedSize(280, 110)
            form.addRow('Username:', self._user)
            form.addRow('Password:', self._pass)
            self._user.setFocus()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def credentials(self) -> tuple[str, str]:
        return self._user.text(), self._pass.text()


# ── Setup / Connection-editor dialog ──────────────────────────────────────────

class SetupWindow(QDialog):
    def __init__(self, app_path: str, parent=None):
        super(SetupWindow, self).__init__(parent)
        uic.loadUi(resource_path('ui/setup_window.ui'), self)
        self.setWindowIcon(QIcon(resource_path(r'images/ACG.ico')))
        self.setWindowTitle(f'Setup - {APP_NAME} - {APP_VERSION}')

        self.config   = ConfigManager(app_path)
        self._loading = False   # block recursive signal handling

        # ── find widgets ──────────────────────────────────────────────────────
        # Input fields
        self.connections = self.findChild(QComboBox,  'cmb_config')
        self.cloud_type  = self.findChild(QComboBox,  'cmb_cloud')
        self.security    = self.findChild(QComboBox,  'cmb_security')
        self.address     = self.findChild(QLineEdit,  'le_address')
        self.port        = self.findChild(QLineEdit,  'le_port')
        self.instance    = self.findChild(QLineEdit,  'le_instance')
        self.ssl         = self.findChild(QComboBox,  'cmb_ssl')
        self.namespace   = self.findChild(QLineEdit,  'le_namespace')
        self.gateway     = self.findChild(QLineEdit,  'le_gateway')

        # Labels
        self.lbl_security  = self.findChild(QLabel, 'lbl_security')
        self.lbl_port      = self.findChild(QLabel, 'label_4')   # "HTTP Port #"
        self.lbl_instance  = self.findChild(QLabel, 'label_5')   # "Instance Name"
        self.lbl_ssl       = self.findChild(QLabel, 'label_6')   # "Use SSL"
        self.lbl_namespace = self.findChild(QLabel, 'label_7')   # "CAM Namespace ID" / "Tenant ID"
        self.lbl_gateway   = self.findChild(QLabel, 'label_8')   # "SSO Gateway"

        # Buttons
        self.btn_save   = self.findChild(QPushButton, 'btn_save')
        self.btn_delete = self.findChild(QPushButton, 'btn_delete')
        self.btn_close  = self.findChild(QPushButton, 'btn_close')

        # ── initialise comboboxes ─────────────────────────────────────────────
        self.connections.setEditable(True)
        self.connections.lineEdit().setPlaceholderText('Select or type a name…')
        self._refresh_connections(select='')

        self.ssl.addItems(['', 'True', 'False'])
        self.cloud_type.addItems([''] + CLOUD_OPTIONS)
        self.security.addItems(SECURITY_OPTIONS)

        # ── connect signals ───────────────────────────────────────────────────
        self.cloud_type.currentIndexChanged.connect(self._on_cloud_changed)
        self.security.currentIndexChanged.connect(self._on_security_changed)
        self.connections.currentIndexChanged.connect(self._on_connection_changed)
        self.btn_save.clicked.connect(self.save_config)
        self.btn_delete.clicked.connect(self.delete_config)
        self.btn_close.clicked.connect(self.reject)

        # Initial field visibility
        self._apply_visibility()

    # ── private helpers ───────────────────────────────────────────────────────

    def _refresh_connections(self, select: str = ''):
        """Repopulate the connections combobox, optionally pre-selecting *select*."""
        self.connections.blockSignals(True)
        self.connections.clear()
        self.connections.addItem('')
        self.connections.addItems(self.config.get_connection_names())
        idx = self.connections.findText(select)
        self.connections.setCurrentIndex(max(idx, 0))
        self.connections.blockSignals(False)

    def _set_row_visible(self, widget, label, visible: bool):
        """Show or hide a field widget and its accompanying label together."""
        widget.setVisible(visible)
        if label is not None:
            label.setVisible(visible)

    def _apply_visibility(self):
        """Show/hide fields based on cloud type and (for On-Prem) security mode."""
        cloud    = self.cloud_type.currentText()
        security = self.security.currentText()
        on_prem  = cloud == 'On-Prem'

        # Security selector: On-Prem only
        self._set_row_visible(self.security, self.lbl_security, on_prem)

        # Port and SSL: On-Prem only
        self._set_row_visible(self.port, self.lbl_port, on_prem)
        self._set_row_visible(self.ssl,  self.lbl_ssl,  on_prem)

        # Instance: all cloud types except blank
        self._set_row_visible(self.instance, self.lbl_instance, cloud in ('On-Prem', 'PAoC', 'PA SaaS'))

        # Namespace: On-Prem CAM/CAM SSO, or PA SaaS (as Tenant ID); PAoC hardcodes LDAP
        show_ns = (on_prem and security in ('CAM', 'CAM SSO')) or cloud == 'PA SaaS'
        self._set_row_visible(self.namespace, self.lbl_namespace, show_ns)
        if show_ns and self.lbl_namespace:
            self.lbl_namespace.setText(NAMESPACE_LABEL.get(cloud, 'CAM Namespace ID'))

        # Gateway: On-Prem CAM SSO only
        self._set_row_visible(self.gateway, self.lbl_gateway, on_prem and security == 'CAM SSO')

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_cloud_changed(self):
        if self._loading:
            return
        cloud = self.cloud_type.currentText()
        default = DEFAULT_PORTS.get(cloud, '')
        if default and not self.port.text().strip():
            self.port.setText(default)
        self._apply_visibility()

    def _on_security_changed(self):
        if not self._loading:
            self._apply_visibility()

    def _on_connection_changed(self):
        name = self.connections.currentText().strip()
        if not name or name not in self.config.get_connection_names():
            return

        self._loading = True
        data = self.config.get_connection(name)

        # Set cloud type (this normally triggers _on_cloud_changed, suppressed by _loading)
        cloud = data.get(FIELD_CLOUD, '')
        idx   = self.cloud_type.findText(cloud)
        self.cloud_type.setCurrentIndex(idx if idx >= 0 else 0)

        # Populate all fields
        sec_idx = self.security.findText(data.get(FIELD_SECURITY, 'Standard'))
        self.security.setCurrentIndex(sec_idx if sec_idx >= 0 else 0)
        self.address.setText(data.get(FIELD_ADDRESS, ''))
        self.port.setText(data.get(FIELD_PORT, ''))
        self.instance.setText(data.get(FIELD_INSTANCE, ''))
        ssl_idx = self.ssl.findText(data.get(FIELD_SSL, ''))
        self.ssl.setCurrentIndex(ssl_idx if ssl_idx >= 0 else 0)
        self.namespace.setText(data.get(FIELD_NAMESPACE, ''))
        self.gateway.setText(data.get(FIELD_GATEWAY, ''))

        self._loading = False
        self._apply_visibility()

    # ── actions ───────────────────────────────────────────────────────────────

    def save_config(self):
        name = self.connections.currentText().strip()
        if not name:
            QMessageBox.warning(self, 'Validation', 'Please enter a connection name.')
            return

        data = {
            FIELD_NAME:      name,
            FIELD_CLOUD:     self.cloud_type.currentText(),
            FIELD_SECURITY:  self.security.currentText(),
            FIELD_ADDRESS:   self.address.text(),
            FIELD_PORT:      self.port.text(),
            FIELD_INSTANCE:  self.instance.text(),
            FIELD_SSL:       self.ssl.currentText(),
            FIELD_NAMESPACE: self.namespace.text(),
            FIELD_GATEWAY:   self.gateway.text(),
        }

        ok, msg = self.config.save_connection(data)
        if ok:
            self._refresh_connections(select=name)
            QMessageBox.information(self, 'Saved', f'Connection "{name}" saved successfully.')
        else:
            QMessageBox.warning(self, 'Validation Error', msg)

    def delete_config(self):
        name = self.connections.currentText().strip()
        if not name or name not in self.config.get_connection_names():
            QMessageBox.information(self, 'Delete', 'Please select a saved connection to delete.')
            return

        reply = QMessageBox.question(
            self, 'Confirm Delete',
            f'Delete connection "{name}"?',
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.config.delete_connection(name)
            self._refresh_connections(select='')


# ── About dialog ──────────────────────────────────────────────────────────────

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f'About {APP_NAME}')
        self.setModal(True)
        self.setFixedSize(480, 380)

        text = QTextBrowser()
        text.setOpenExternalLinks(True)
        text.setReadOnly(True)
        text.setHtml(f"""
<h2 style="color:#17365D;">{APP_NAME}</h2>
<p><b>Version:</b> {APP_VERSION}</p>
<p>
  Monitors active threads on IBM Planning Analytics / TM1 servers in real time.
  Threads are refreshed on a configurable interval and can be cancelled directly
  from the table via right-click.
</p>

<h3 style="color:#17365D;">Connection Types</h3>
<table cellpadding="4" width="100%">
  <tr>
    <td><b>On-Prem</b></td>
    <td>
      TM1 v11 server running on-premises or on a private network.<br/>
      Connects via <i>address</i> + <i>HTTP port</i> (REST API port from
      <code>Tm1s.cfg → HTTPPortNumber</code>).<br/>
      Supports <b>Standard</b>, <b>CAM</b>, and <b>CAM SSO</b> security modes.
    </td>
  </tr>
  <tr>
    <td><b>PAoC</b></td>
    <td>
      IBM Planning Analytics on Cloud (hosted by IBM,
      <code>*.planning-analytics.cloud.ibm.com</code>).<br/>
      Uses CAM / LDAP authentication. Enter your IBM Cloud username and password.
    </td>
  </tr>
  <tr>
    <td><b>PA SaaS</b></td>
    <td>
      IBM Planning Analytics as a Service
      (<code>*.planninganalytics.saas.ibm.com</code>).<br/>
      Authenticates with an <b>IBM Cloud API key</b> (user is fixed to
      <code>apikey</code>). The <i>Tenant ID</i> and <i>Instance Name</i>
      can be found in your IBM Cloud resource details.
    </td>
  </tr>
</table>

<h3 style="color:#17365D;">Setup</h3>
<p>
  Use <b>Setup → Setup Connection</b> to add, edit, or delete connections.
  Connections are stored locally in <code>config/connections.json</code>.
</p>

<p style="color:grey;font-size:small;">
  &copy; Application Consulting Group &nbsp;|&nbsp; {APP_VERSION}
</p>
""")

        close_btn = QPushButton('Close')
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(text)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
        self.setLayout(layout)


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if not os.path.exists('config'):
        os.makedirs('config')
    app = QApplication(sys.argv)
    UIWindow = MainWindow()
    app.exec_()
