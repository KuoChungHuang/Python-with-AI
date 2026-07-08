"""
M5：PySide6 主視窗 — 拖拉區（含資料夾）、檔案清單 UI，接上背景轉換
（QThread，見 conversion_worker.py）、進度回報、取消、正常關閉，
同名檔案衝突對話框（見規格書 8.），以及視窗美化、轉換動畫、完成畫面。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, QUrl, Qt
from PySide6.QtGui import (
    QBrush,
    QCloseEvent,
    QColor,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from conversion_worker import ConversionWorker
from converter import ConflictStrategy, ConversionResult, collect_files

COLUMN_NAMES = ["檔名", "狀態", "進度"]
STATUS_WAITING = "等待中"
STATUS_RUNNING = "轉換中"
STATUS_SUCCESS = "成功"
STATUS_FAILED = "失敗"
STATUS_SKIPPED = "已略過"

_SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

_ROW_COLORS = {
    STATUS_RUNNING: QColor("#eaf3fc"),
    STATUS_SUCCESS: QColor("#e8f8ef"),
    STATUS_FAILED: QColor("#fdecea"),
    STATUS_SKIPPED: QColor("#f2f2f2"),
}

APP_STYLESHEET = """
QWidget {
    font-family: "Microsoft JhengHei UI", "Segoe UI", sans-serif;
    font-size: 10.5pt;
    color: #2c3e50;
}
QMainWindow, QDialog {
    background-color: #f5f7fa;
}
QLabel#sectionLabel {
    font-weight: 600;
    color: #34495e;
    margin-top: 4px;
}
QPushButton {
    background-color: #ffffff;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 6px 16px;
}
QPushButton:hover {
    background-color: #eef4fc;
    border-color: #3a8ee6;
}
QPushButton:pressed {
    background-color: #dceaf9;
}
QPushButton:disabled {
    color: #aab2bd;
    background-color: #f0f0f0;
    border-color: #e0e0e0;
}
QPushButton#primaryButton {
    background-color: #3a8ee6;
    border-color: #3a8ee6;
    color: white;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background-color: #2f7bd0;
}
QPushButton#primaryButton:disabled {
    background-color: #b9d6f5;
    border-color: #b9d6f5;
    color: #eef4fc;
}
QTableWidget {
    background-color: white;
    border: 1px solid #e0e4e8;
    border-radius: 6px;
    gridline-color: #eef1f4;
}
QHeaderView::section {
    background-color: #eef1f4;
    color: #34495e;
    padding: 6px;
    border: none;
    font-weight: 600;
}
QTableWidget::item {
    padding: 4px;
}
QPlainTextEdit {
    background-color: white;
    border: 1px solid #e0e4e8;
    border-radius: 6px;
    font-family: Consolas, monospace;
    font-size: 9.5pt;
}
QProgressBar {
    border: 1px solid #d0d7de;
    border-radius: 6px;
    text-align: center;
    background-color: white;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #3a8ee6;
    border-radius: 5px;
}
QLabel#completionCheck {
    font-size: 42pt;
    color: #2ecc71;
}
QLabel#completionTitle {
    font-size: 14pt;
    font-weight: 700;
    color: #2c3e50;
}
QLabel#completionSummary {
    color: #5f6b7a;
}
"""


class DropArea(QLabel):
    """可接受檔案／資料夾拖放的區域。"""

    def __init__(self, on_files_dropped, parent=None) -> None:
        super().__init__(parent)
        self._on_files_dropped = on_files_dropped
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(120)
        self.setText("將檔案或資料夾拖曳到這裡")
        self._set_idle_style()

    def _set_idle_style(self) -> None:
        self.setStyleSheet(
            "QLabel {"
            "  border: 2px dashed #888;"
            "  border-radius: 8px;"
            "  color: #888;"
            "  font-size: 14px;"
            "}"
        )

    def _set_active_style(self) -> None:
        self.setStyleSheet(
            "QLabel {"
            "  border: 2px dashed #3a8ee6;"
            "  border-radius: 8px;"
            "  color: #3a8ee6;"
            "  font-size: 14px;"
            "  background-color: rgba(58, 142, 230, 0.08);"
            "}"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            self._set_active_style()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: ANN001 - Qt event signature
        self._set_idle_style()

    def dropEvent(self, event: QDropEvent) -> None:
        self._set_idle_style()
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        event.acceptProposedAction()
        if paths:
            self._on_files_dropped(paths)


class ConflictDialog(QDialog):
    """同名 .md 已存在時的詢問對話框：覆蓋／略過／另存新檔。

    依決策「每次都詢問，不設預設」，使用者必須點選其中一個按鈕才能關閉這個對話框，
    不提供 Esc / 右上角關閉鈕跳過選擇的途徑。

    「另存新檔」「略過」是不可逆風險低的選擇，選了就自動套用到這批其餘的衝突，
    不用每個檔案都按一次。「覆蓋」會覆蓋既有檔案內容、無法復原，預設仍然逐一詢問，
    只有勾選「套用到全部」才會讓覆蓋也套用到其餘衝突。
    """

    def __init__(self, target_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("檔案已存在")
        self.setModal(True)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )

        self.strategy: ConflictStrategy = "skip"
        self.apply_to_all = False

        label = QLabel(f"「{target_name}」已存在，請選擇處理方式：")
        label.setWordWrap(True)

        overwrite_btn = QPushButton("覆蓋")
        skip_btn = QPushButton("略過")
        rename_btn = QPushButton("另存新檔")
        overwrite_btn.clicked.connect(lambda: self._choose("overwrite"))
        skip_btn.clicked.connect(lambda: self._choose("skip"))
        rename_btn.clicked.connect(lambda: self._choose("rename"))

        self.apply_all_checkbox = QCheckBox("覆蓋也套用到全部")
        self.apply_all_checkbox.setToolTip(
            "「另存新檔」「略過」預設就會自動套用到其餘同名衝突。\n"
            "覆蓋是不可逆的動作，預設逐一詢問；勾選這裡才會讓覆蓋也套用到全部。"
        )

        button_row = QHBoxLayout()
        for btn in (overwrite_btn, skip_btn, rename_btn):
            button_row.addWidget(btn)

        layout = QVBoxLayout()
        layout.addWidget(label)
        layout.addLayout(button_row)
        layout.addWidget(self.apply_all_checkbox)
        self.setLayout(layout)

    def _choose(self, strategy: ConflictStrategy) -> None:
        self.strategy = strategy
        if strategy == "overwrite":
            # 覆蓋不可逆，只有使用者明確勾選才會套用到全部；預設每次都問。
            self.apply_to_all = self.apply_all_checkbox.isChecked()
        else:
            # 另存新檔／略過風險低，選了就直接套用到這批其餘的衝突。
            self.apply_to_all = True
        self.accept()

    def reject(self) -> None:
        # 不允許用 Esc 跳過選擇；WindowCloseButtonHint 已移除，這裡再擋一層防呆。
        pass


class CompletionDialog(QDialog):
    """轉換批次結束時的完成畫面：打勾 + 成功/失敗/略過統計，淡入後停留一下自動淡出關閉。

    非強制互動（非 modal），不會擋住使用者接下來的操作；只是給一個明確的完成回饋。
    """

    def __init__(self, success: int, failed: int, skipped: int, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("完成")
        self.setModal(False)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )
        self.setFixedWidth(300)

        check = QLabel("✓")
        check.setObjectName("completionCheck")
        check.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("轉換完成！")
        title.setObjectName("completionTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        parts = [f"成功 {success}"]
        if failed:
            parts.append(f"失敗 {failed}")
        if skipped:
            parts.append(f"略過 {skipped}")
        summary = QLabel("　".join(parts))
        summary.setObjectName("completionSummary")
        summary.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(check)
        layout.addWidget(title)
        layout.addWidget(summary)
        self.setLayout(layout)

        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        self._fade_in = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_in.setDuration(200)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._fade_out.setDuration(300)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self.close)

        QTimer.singleShot(2200, self._fade_out.start)

    def showEvent(self, event) -> None:  # noqa: ANN001 - Qt event signature
        super().showEvent(event)
        parent = self.parentWidget()
        if parent is not None:
            geo = self.frameGeometry()
            geo.moveCenter(parent.frameGeometry().center())
            self.move(geo.topLeft())
        self._fade_in.start()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MarkItDown 轉檔工具")
        self.resize(760, 560)

        self._queued_paths: set[str] = set()
        self._worker: ConversionWorker | None = None
        self._last_output_dir: Path | None = None
        self._batch_counts = {"success": 0, "failed": 0, "skipped": 0}

        self._active_row: int | None = None
        self._spinner_index = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(120)
        self._spinner_timer.timeout.connect(self._tick_spinner)

        self.drop_area = DropArea(self._handle_new_paths)

        self.select_button = QPushButton("選擇檔案")
        self.select_button.clicked.connect(self._on_select_files_clicked)

        self.file_table = QTableWidget(0, len(COLUMN_NAMES))
        self.file_table.setHorizontalHeaderLabels(COLUMN_NAMES)
        header = self.file_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.file_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setAlternatingRowColors(True)

        self.overall_progress = QProgressBar()
        self.overall_progress.setVisible(False)

        self.start_button = QPushButton("開始轉換")
        self.start_button.setObjectName("primaryButton")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._on_start_clicked)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)

        self.clear_button = QPushButton("清空清單")
        self.clear_button.clicked.connect(self._on_clear_clicked)

        self.open_output_button = QPushButton("開啟輸出資料夾")
        self.open_output_button.setEnabled(False)
        self.open_output_button.setToolTip("轉換成功至少一個檔案後才能開啟輸出資料夾")
        self.open_output_button.clicked.connect(self._on_open_output_clicked)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)

        button_row = QHBoxLayout()
        for btn in (
            self.start_button,
            self.cancel_button,
            self.clear_button,
            self.open_output_button,
        ):
            button_row.addWidget(btn)
        button_row.addStretch(1)

        file_list_label = QLabel("檔案清單：")
        file_list_label.setObjectName("sectionLabel")
        log_label = QLabel("日誌：")
        log_label.setObjectName("sectionLabel")

        layout = QVBoxLayout()
        layout.addWidget(self.drop_area)
        layout.addWidget(self.select_button)
        layout.addWidget(file_list_label)
        layout.addWidget(self.file_table, stretch=1)
        layout.addLayout(button_row)
        layout.addWidget(self.overall_progress)
        layout.addWidget(log_label)
        layout.addWidget(self.log_view)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._update_button_states()

    # -- 加入檔案 --

    def _on_select_files_clicked(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "選擇檔案")
        if files:
            self._handle_new_paths(files)

    def _on_clear_clicked(self) -> None:
        self.file_table.setRowCount(0)
        self._queued_paths.clear()
        self._log("已清空檔案清單")
        self._update_button_states()

    def _handle_new_paths(self, raw_paths: list[str]) -> None:
        try:
            files = collect_files(raw_paths)
        except FileNotFoundError as e:
            self._log(f"加入失敗：{e}")
            return

        added = 0
        for f in files:
            key = str(f.resolve())
            if key in self._queued_paths:
                continue
            self._queued_paths.add(key)
            self._add_row(f)
            added += 1

        if added:
            self._log(f"已加入 {added} 個檔案到佇列")
        else:
            self._log("沒有新增檔案（可能是空資料夾或重複拖入）")
        self._update_button_states()

    def _add_row(self, path: Path) -> None:
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)

        name_item = QTableWidgetItem(path.name)
        name_item.setData(Qt.ItemDataRole.UserRole, str(path))
        self.file_table.setItem(row, 0, name_item)
        self.file_table.setItem(row, 1, QTableWidgetItem(STATUS_WAITING))
        self.file_table.setItem(row, 2, QTableWidgetItem("-"))

    def _set_row_color(self, row: int, status: str) -> None:
        color = _ROW_COLORS.get(status)
        brush = QBrush(color) if color is not None else QBrush()
        for col in range(self.file_table.columnCount()):
            item = self.file_table.item(row, col)
            if item is not None:
                item.setBackground(brush)

    def _tick_spinner(self) -> None:
        if self._active_row is None:
            return
        self._spinner_index = (self._spinner_index + 1) % len(_SPINNER_FRAMES)
        item = self.file_table.item(self._active_row, 2)
        if item is not None:
            item.setText(_SPINNER_FRAMES[self._spinner_index])

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"{timestamp} {message}")

    # -- 轉換控制 --

    def _is_running(self) -> bool:
        return self._worker is not None

    def _update_button_states(self) -> None:
        running = self._is_running()
        has_rows = self.file_table.rowCount() > 0

        self.start_button.setEnabled(not running and has_rows)
        self.cancel_button.setEnabled(running)
        self.clear_button.setEnabled(not running)
        self.select_button.setEnabled(not running)
        self.drop_area.setEnabled(not running)
        self.open_output_button.setEnabled(self._last_output_dir is not None)

    def _on_start_clicked(self) -> None:
        queued: list[tuple[int, Path]] = []
        for row in range(self.file_table.rowCount()):
            if self.file_table.item(row, 1).text() == STATUS_WAITING:
                full_path = self.file_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                queued.append((row, Path(full_path)))

        if not queued:
            self._log("沒有待轉換的檔案（已完成的項目需先清空清單才能重新轉換）")
            return

        self._batch_counts = {"success": 0, "failed": 0, "skipped": 0}

        self._worker = ConversionWorker(queued)
        self._worker.file_started.connect(self._on_worker_file_started)
        self._worker.file_finished.connect(self._on_worker_file_finished)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.conflict_needed.connect(self._on_conflict_needed)
        self._worker.finished.connect(self._on_worker_done)

        self._log(f"開始轉換，共 {len(queued)} 個檔案")
        self.overall_progress.setRange(0, len(queued))
        self.overall_progress.setValue(0)
        self.overall_progress.setVisible(True)
        self._spinner_timer.start()
        self._update_button_states()
        self._worker.start()

    def _on_cancel_clicked(self) -> None:
        if self._worker is not None:
            self._worker.request_cancel()
            self.cancel_button.setEnabled(False)
            self._log("已送出取消要求，將於目前檔案處理完成後停止")

    def _on_worker_file_started(self, row: int, filename: str) -> None:
        self._active_row = row
        self._spinner_index = 0
        self.file_table.item(row, 1).setText(STATUS_RUNNING)
        self.file_table.item(row, 2).setText(_SPINNER_FRAMES[0])
        self._set_row_color(row, STATUS_RUNNING)

    def _on_worker_file_finished(self, row: int, result: ConversionResult) -> None:
        if self._active_row == row:
            self._active_row = None  # 停止這一列的 spinner 動畫，改顯示最終結果

        status_text = {
            "success": STATUS_SUCCESS,
            "failed": STATUS_FAILED,
            "skipped": STATUS_SKIPPED,
        }[result.status]
        progress_text = "100%" if result.status == "success" else "-"

        self.file_table.item(row, 1).setText(status_text)
        self.file_table.item(row, 2).setText(progress_text)
        self._set_row_color(row, status_text)
        self._batch_counts[result.status] += 1

        if result.status == "success":
            self._last_output_dir = result.output.parent
            self._log(f"{result.source.name} -> 轉換成功：{result.output.name}")
        elif result.status == "skipped":
            self._log(f"{result.source.name} -> 已略過：{result.message}")
        else:
            self._log(f"{result.source.name} -> 失敗：{result.message}")

    def _on_conflict_needed(self, target_path: str) -> None:
        # 這個 slot 在 GUI 執行緒執行；worker 執行緒此刻正卡在 threading.Event.wait()
        # 等待下面 set_conflict_response() 被呼叫，所以跳出的對話框不會擋住 worker 之外的東西。
        dialog = ConflictDialog(Path(target_path).name, self)
        dialog.exec()
        if self._worker is not None:
            self._worker.set_conflict_response(dialog.strategy, dialog.apply_to_all)

    def _on_worker_progress(self, done: int, total: int) -> None:
        self.statusBar().showMessage(f"進度：{done}/{total}")
        self.overall_progress.setValue(done)

    def _on_worker_done(self) -> None:
        self._worker = None
        self._active_row = None
        self._spinner_timer.stop()
        self.overall_progress.setVisible(False)
        self._log("轉換批次結束")
        self.statusBar().clearMessage()
        self._update_button_states()

        counts = self._batch_counts
        if counts["success"] or counts["failed"] or counts["skipped"]:
            dialog = CompletionDialog(counts["success"], counts["failed"], counts["skipped"], self)
            dialog.show()

    def _on_open_output_clicked(self) -> None:
        if self._last_output_dir is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output_dir)))

    # -- 正常關閉 --

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._worker is not None:
            self._log("視窗關閉中，等待目前檔案轉換完成後安全停止...")
            self._worker.request_cancel()
            self._worker.wait()
        event.accept()
