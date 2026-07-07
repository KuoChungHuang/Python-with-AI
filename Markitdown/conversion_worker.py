"""
M4：背景執行緒，逐一呼叫 converter 轉換佇列中的檔案，回報進度，並可回應取消要求。

同名檔案衝突時（見規格書 8.），改為向 GUI 執行緒詢問使用者要覆蓋／略過／另存新檔：
worker 發出 conflict_needed signal 後用 threading.Event 阻塞自己等待答案，
GUI 執行緒收到 signal 後跳出對話框，使用者選擇完再呼叫 set_conflict_response()
把答案寫回、喚醒 worker。這段等待只會擋住背景執行緒，不會擋住 GUI。

取消是「優雅」的：目前正在轉換的檔案會完成，之後才停止，不會留下寫到一半的殘缺 .md。
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from converter import ConflictStrategy, ConversionResult, convert_file


class ConversionWorker(QThread):
    file_started = Signal(int, str)  # row, 檔名
    file_finished = Signal(int, object)  # row, ConversionResult
    progress = Signal(int, int)  # 已完成數, 總數
    conflict_needed = Signal(str)  # 目的地路徑，請 GUI 執行緒跳出對話框詢問

    def __init__(self, queued: list[tuple[int, Path]], parent=None) -> None:
        super().__init__(parent)
        self._queued = queued
        self._cancel_requested = False

        self._sticky_strategy: ConflictStrategy | None = None
        self._conflict_event = threading.Event()
        self._conflict_response: tuple[ConflictStrategy, bool] | None = None

    def request_cancel(self) -> None:
        self._cancel_requested = True
        # 若正卡在等待衝突對話框的答案，補一個假答案讓 worker 能盡快檢查取消旗標並結束，
        # 不然視窗關閉時 wait() 會永遠等不到已經不會再出現的 GUI 回應。
        if not self._conflict_event.is_set():
            self._conflict_response = ("skip", False)
            self._conflict_event.set()

    def set_conflict_response(self, strategy: ConflictStrategy, apply_to_all: bool) -> None:
        self._conflict_response = (strategy, apply_to_all)
        self._conflict_event.set()

    def _resolve_conflict(self, target: Path) -> ConflictStrategy:
        if self._sticky_strategy is not None:
            return self._sticky_strategy

        self._conflict_event.clear()
        self.conflict_needed.emit(str(target))
        self._conflict_event.wait()

        strategy, apply_to_all = self._conflict_response
        if apply_to_all:
            self._sticky_strategy = strategy
        return strategy

    def run(self) -> None:
        total = len(self._queued)
        for done, (row, path) in enumerate(self._queued, start=1):
            if self._cancel_requested:
                break
            self.file_started.emit(row, path.name)
            result: ConversionResult = convert_file(path, self._resolve_conflict)
            self.file_finished.emit(row, result)
            self.progress.emit(done, total)
