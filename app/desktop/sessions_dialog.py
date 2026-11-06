"""Native session history and two-step restore UI. File paths stay in Python/Qt."""
from datetime import datetime, timezone
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QFileDialog, QHBoxLayout, QLabel,
                              QLineEdit, QProgressBar, QPushButton, QTableWidget,
                              QTableWidgetItem, QVBoxLayout, QHeaderView)

ERRORS = {
    'CANCELLED': 'Operación cancelada. Se conserva la base anterior.',
    'DATABASE_BUSY': 'La base está ocupada. Reintenta cuando termine la otra operación.',
    'DATABASE_UNAVAILABLE': 'No se pudo leer o escribir SQLite. Revisa el archivo, los permisos y el espacio disponible.',
    'SESSION_CONFLICT_REOPEN': 'Otra ventana cambió los datos. Cierra este gestor y reabre FiscalOps antes de modificarlos.',
    'SESSION_ENGINE_MISMATCH': 'La sesión activa del respaldo usa otra versión del motor. No se puede abrir con esta versión.',
    'BACKUP_VERSION_UNSUPPORTED': 'El respaldo usa una versión de base no compatible.',
    'BACKUP_IDENTITY_INVALID': 'El archivo no es una base FiscalOps.',
    'BACKUP_SCHEMA_INVALID': 'La estructura del respaldo no coincide con el esquema FiscalOps admitido.',
    'BACKUP_INTEGRITY_FAILED': 'El respaldo no pasó la comprobación de integridad de SQLite.',
    'BACKUP_CONTENT_INVALID': 'El respaldo contiene datos o resultados fiscales incompatibles.',
    'DOCUMENT_INTEGRITY_FAILED': 'Los hashes de documentos o resultados no coinciden.',
    'SESSION_INTEGRITY_FAILED': 'El conteo de documentos de una sesión no coincide.',
    'BACKUP_PATH_IS_ACTIVE_DATABASE': 'Elige un archivo distinto de la base activa y de sus archivos auxiliares.',
    'BACKUP_PATH_INVALID': 'No se admiten enlaces simbólicos como archivo de respaldo.',
    'RESTORE_FILE_LIMIT': 'Selecciona un respaldo SQLite existente de hasta 2 GiB.',
    'RESTORE_PLAN_CHANGED': 'La copia revisada cambió. Selecciona y verifica el respaldo de nuevo.',
}


class SessionsDialog(QDialog):
    def __init__(self, window, snapshot):
        super().__init__(window)
        self.window, self.bridge = window, window.fiscal
        self.setObjectName('sessionsDialog')
        self.setWindowTitle('FiscalOps · Sesiones y respaldos')
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(910, 610)
        self.request_id = None
        self.plan = None
        self.changed = False
        self.closing_requested = False
        self.offset = 0
        self.rows = []
        self.has_more = False
        self.picker = None  # Python-only native-dialog QA hook.
        layout = QVBoxLayout(self)
        title = QLabel('Historial de sesiones', self)
        title.setStyleSheet('font-size:18px;font-weight:bold;color:#4f2d7f')
        layout.addWidget(title)
        self.search = QLineEdit(self)
        self.search.setObjectName('sessionSearch')
        self.search.setPlaceholderText('Buscar por RFC, fecha UTC o identificador de sesión')
        layout.addWidget(self.search)
        self.table = QTableWidget(0, 5, self)
        self.table.setObjectName('sessionsTable')
        self.table.setHorizontalHeaderLabels(['Fecha (UTC)', 'RFC', 'CFDI', 'Estado', 'Identificador'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        controls = QHBoxLayout()
        self.previous = self.button('Anteriores', 'historyPrevious', self.previous_page)
        self.next = self.button('Siguientes', 'historyNext', self.next_page)
        self.open = self.button('Abrir sesión seleccionada', 'historyOpen', self.open_session)
        for widget in (self.previous, self.next, self.open):
            controls.addWidget(widget)
        controls.addStretch()
        layout.addLayout(controls)
        actions = QHBoxLayout()
        self.backup = self.button('Crear respaldo SQLite…', 'backupCreate', self.create_backup)
        self.restore = self.button('Seleccionar respaldo para restaurar…', 'restoreChoose', self.choose_restore)
        actions.addWidget(self.backup)
        actions.addWidget(self.restore)
        actions.addStretch()
        layout.addLayout(actions)
        self.review = QLabel(self)
        self.review.setObjectName('restoreReview')
        self.review.setWordWrap(True)
        self.review.setTextFormat(Qt.TextFormat.PlainText)
        self.review.hide()
        layout.addWidget(self.review)
        review_actions = QHBoxLayout()
        self.confirm = self.button('Confirmar restauración', 'restoreConfirm', self.confirm_restore)
        self.discard = self.button('Descartar selección', 'restoreDiscard', self.discard_restore)
        review_actions.addWidget(self.confirm)
        review_actions.addWidget(self.discard)
        review_actions.addStretch()
        self.confirm.hide()
        self.discard.hide()
        layout.addLayout(review_actions)
        self.progress = QProgressBar(self)
        self.progress.setObjectName('maintenanceProgress')
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = QLabel('Cargando historial…', self)
        self.status.setObjectName('maintenanceStatus')
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.status)
        bottom = QHBoxLayout()
        bottom.addStretch()
        self.cancel = self.button('Cancelar operación', 'maintenanceCancel', self.cancel_operation)
        self.done = self.button('Cerrar', 'maintenanceClose', self.reject)
        bottom.addWidget(self.cancel)
        bottom.addWidget(self.done)
        layout.addLayout(bottom)
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.timeout.connect(self.reset_search)
        self.search.textChanged.connect(lambda: self.debounce.start(250))
        self.table.itemSelectionChanged.connect(self.update_buttons)
        self.table.itemDoubleClicked.connect(lambda item: self.open_session())
        QTimer.singleShot(0, lambda: self.run('native.enter', {'snapshot': snapshot}, lambda value: self.history()))
        self.update_buttons()

    def button(self, label, identity, callback):
        button = QPushButton(label, self)
        button.setObjectName(identity)
        button.clicked.connect(callback)
        button.setAutoDefault(False)
        return button

    def update_buttons(self):
        enabled = self.request_id is None and not self.closing_requested
        browsing = enabled and self.plan is None and not self.changed
        for control in (self.search, self.table, self.backup, self.restore):
            control.setEnabled(browsing)
        self.previous.setEnabled(browsing and self.offset > 0)
        self.next.setEnabled(browsing and self.has_more)
        selected = self.table.currentRow()
        self.open.setEnabled(browsing and 0 <= selected < len(self.rows) and self.rows[selected]['compatible'])
        self.confirm.setEnabled(enabled and self.plan is not None)
        self.discard.setEnabled(enabled and self.plan is not None)
        self.cancel.setEnabled(self.request_id is not None and not self.closing_requested)

    def run(self, operation, payload, callback):
        if self.request_id is not None:
            return
        self.debounce.stop()
        self.progress.setRange(0, 0)
        self.progress.show()
        def finished(reply):
            self.request_id = None
            self.progress.hide()
            if reply['ok'] and operation in ('native.open', 'native.restore.commit'):
                self.changed = True
                if operation == 'native.restore.commit':
                    self.window.last_restore = reply['result']
            if self.closing_requested:
                self.finish_close()
                return
            if reply['ok']:
                callback(reply['result'])
            else:
                message = ERRORS.get(reply['code'], 'Operación rechazada: '+reply['code'])
                if reply.get('recovery_path'):
                    message += '\nBase anterior conservada. Copia preventiva: '+reply['recovery_path']
                self.status.setText(message)
            self.update_buttons()
        self.request_id = self.bridge.native_request(operation, payload, finished, self.on_progress)
        self.update_buttons()

    def on_progress(self, value):
        self.status.setText(value['label']+' · '+str(value['done'])+(' / '+str(value['total']) if value['total'] else ''))
        self.progress.setRange(0, value['total'])
        self.progress.setValue(value['done'])

    def history(self):
        def loaded(value):
            self.rows, self.has_more = value['sessions'], value['has_more']
            self.table.setRowCount(len(self.rows))
            for index, row in enumerate(self.rows):
                state = 'Activa' if row['active'] else 'Guardada'
                if not row['compatible']:
                    state = 'Motor incompatible'
                for col, text in enumerate((row['created_at'], row['rfc'] or 'Sin RFC', str(row['documents']), state, row['dataset_id'])):
                    self.table.setItem(index, col, QTableWidgetItem(text))
            self.status.setText('Sesiones '+str(self.offset+1)+'–'+str(self.offset+len(self.rows)) if self.rows else 'No hay sesiones guardadas.')
        self.run('native.history', {'offset': self.offset, 'query': self.search.text()}, loaded)

    def reset_search(self):
        if not self.request_id and not self.plan:
            self.offset = 0
            self.history()

    def previous_page(self):
        self.offset = max(0, self.offset-50)
        self.history()

    def next_page(self):
        self.offset += 50
        self.history()

    def open_session(self):
        index = self.table.currentRow()
        if self.request_id or self.plan or not 0 <= index < len(self.rows) or not self.rows[index]['compatible']:
            return
        def opened(value):
            self.changed = True
            self.finish_close()
        self.run('native.open', {'dataset_id': self.rows[index]['dataset_id']}, opened)

    def pick(self, kind):
        if self.picker:
            return self.picker(kind)
        if kind == 'backup':
            name = 'FiscalOps_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'.sqlite3'
            return QFileDialog.getSaveFileName(self, 'Guardar respaldo FiscalOps', name, 'SQLite FiscalOps (*.sqlite3)')[0]
        return QFileDialog.getOpenFileName(self, 'Seleccionar respaldo FiscalOps', '', 'SQLite FiscalOps (*.sqlite3 *.db);;Todos los archivos (*)')[0]

    def create_backup(self):
        path = self.pick('backup')
        if path:
            self.run('native.backup', {'path': path}, lambda value: self.status.setText(
                'Respaldo verificado: '+value['path']+'\n'+str(value['sessions'])+' sesiones · '+str(value['documents'])+' CFDI\nSHA256: '+value['sha256']))

    def choose_restore(self):
        path = self.pick('restore')
        if not path:
            return
        def reviewed(value):
            self.plan = value
            self.review.setText('Archivo: '+value['name']+'\n'+str(value['sessions'])+' sesiones · '+str(value['documents'])+' CFDI · '+str(value['originals'])+' originales\n'
                                'SHA256: '+value['sha256']+'\nSe sustituirá el historial local completo. Antes se guardará un respaldo preventivo verificado de la base actual.\n'
                                'La selección aún no modifica tus datos. Confirma sólo si deseas restaurar este contenido.')
            self.review.show()
            self.confirm.show()
            self.discard.show()
            self.status.setText('Respaldo verificado. Revisa el contenido antes de confirmar.')
            self.discard.setFocus()
        self.run('native.restore.prepare', {'path': path}, reviewed)

    def discard_restore(self):
        if self.plan:
            token = self.plan['token']
            def discarded(value):
                self.plan = None
                self.review.hide()
                self.confirm.hide()
                self.discard.hide()
                self.status.setText('Selección descartada. La base no cambió.')
            self.run('native.restore.discard', {'token': token}, discarded)

    def confirm_restore(self):
        if not self.plan:
            return
        def restored(value):
            self.changed = True
            self.window.last_restore = value
            self.plan = None
            self.confirm.hide()
            self.discard.hide()
            self.review.setText('Restauración completada.\nRespaldo preventivo de los datos anteriores:\n'+value['recovery_path'])
            self.review.show()
            self.status.setText('Datos verificados y restaurados. Cierra este gestor para abrir el reporte recuperado.')
            self.done.setText('Ver reporte restaurado')
            self.done.setFocus()
        self.run('native.restore.commit', {'token': self.plan['token']}, restored)

    def cancel_operation(self):
        if self.request_id:
            self.bridge.native_cancel(self.request_id)

    def reject(self):
        self.closing_requested = True
        self.debounce.stop()
        if self.request_id:
            self.cancel_operation()
            self.update_buttons()
        else:
            self.finish_close()

    def closeEvent(self, event):
        event.ignore()
        self.reject()

    def finish_close(self):
        if self.plan and not self.changed:
            token, self.plan = self.plan['token'], None
            self.run('native.restore.discard', {'token': token}, lambda value: self.finish_close())
            return
        self.bridge.maintenance_active = False
        self.window.view.setEnabled(True)
        self.window.data_button.setEnabled(True)
        if self.changed:
            self.window.view.reload()
        else:
            self.window.web_page.runJavaScript('window.FiscalOpsRuntime&&window.FiscalOpsRuntime.endMaintenance&&window.FiscalOpsRuntime.endMaintenance()')
        self.window.data_dialog = None
        super().done(0)
