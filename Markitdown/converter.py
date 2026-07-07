"""
M1：核心轉檔邏輯，可用命令列測試（尚未接 UI）。

依副檔名分派轉換方式：
- .pdf  -> pdfminer 直接萃取純文字，跳過 markitdown 內建的表格偵測（見規格書 4.1）
- 其他  -> markitdown.MarkItDown().convert()
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Literal, Union

from markitdown import MarkItDown
from pdfminer.high_level import extract_text as pdf_extract_text

ConflictStrategy = Literal["overwrite", "skip", "rename"]
ConflictResolver = Union[ConflictStrategy, Callable[[Path], ConflictStrategy]]

# 遞迴掃描資料夾時要忽略的目錄名稱
_SKIP_DIR_NAMES = {".git", "__pycache__", "venv", ".venv"}

# 對應規格書 4. 非功能需求所列的相容格式。
#
# markitdown 的純文字 fallback 轉換器會用 charset_normalizer 對任意 bytes 猜測編碼，
# 幾乎不會拋例外——實測對隨機二進位內容也會「成功」轉出 "None" 這種無意義文字，而不會
# 標示失敗。因此在呼叫 markitdown 之前先用白名單擋掉不支援的副檔名，
# 讓「不支援的格式 → 失敗」這條規格真正生效。
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".xlsx",
    ".xls",
    ".pptx",
    ".jpg",
    ".jpeg",
    ".png",
    ".wav",
    ".mp3",
    ".m4a",
    ".mp4",
    ".html",
    ".htm",
    ".csv",
    ".json",
    ".jsonl",
    ".xml",
    ".epub",
    ".txt",
    ".text",
    ".markdown",
    ".ipynb",
    ".msg",
}


@dataclass
class ConversionResult:
    source: Path
    output: Path | None
    status: Literal["success", "failed", "skipped"]
    message: str = ""


def collect_files(paths: Iterable[str | Path]) -> list[Path]:
    """展開輸入路徑：檔案原樣保留，資料夾遞迴尋找其中所有檔案。"""
    collected: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for child in sorted(p.rglob("*")):
                if child.is_file() and not _SKIP_DIR_NAMES & set(child.parts):
                    collected.append(child)
        elif p.is_file():
            collected.append(p)
        else:
            raise FileNotFoundError(f"找不到路徑：{p}")
    return collected


def default_output_path(source: Path) -> Path:
    return source.with_suffix(".md")


def generate_incremented_path(target: Path) -> Path:
    """A.md 已存在時，找出下一個可用的 A(1).md、A(2).md ..."""
    if not target.exists():
        return target
    stem, suffix, parent = target.stem, target.suffix, target.parent
    n = 1
    while True:
        candidate = parent / f"{stem}({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def resolve_conflict(target: Path, strategy: ConflictStrategy) -> Path | None:
    """依衝突策略回傳實際輸出路徑；回傳 None 代表略過此檔案。"""
    if not target.exists():
        return target
    if strategy == "overwrite":
        return target
    if strategy == "skip":
        return None
    if strategy == "rename":
        return generate_incremented_path(target)
    raise ValueError(f"未知的衝突策略：{strategy}")


def convert_pdf_to_text(source: Path) -> str:
    return pdf_extract_text(str(source))


def convert_with_markitdown(source: Path) -> str:
    result = MarkItDown().convert(str(source))
    return result.markdown


def convert_file(source: str | Path, on_conflict: ConflictResolver = "rename") -> ConversionResult:
    """轉換單一檔案並寫出 .md；單一檔案失敗不影響呼叫端佇列中其他檔案。"""
    source = Path(source)
    try:
        if not source.exists():
            return ConversionResult(source, None, "failed", "來源檔案不存在")

        ext = source.suffix.lower()

        if ext == ".md":
            return ConversionResult(source, None, "skipped", "來源已是 .md 檔案，不需轉換")

        if ext not in SUPPORTED_EXTENSIONS:
            label = ext if ext else "(無副檔名)"
            return ConversionResult(source, None, "failed", f"不支援的格式：{label}")

        if source.suffix.lower() == ".pdf":
            markdown = convert_pdf_to_text(source)
        else:
            markdown = convert_with_markitdown(source)

        target = default_output_path(source)
        if target.exists():
            # 只有真的有同名檔案時才詢問策略，避免每個檔案都跳一次對話框。
            strategy = on_conflict(target) if callable(on_conflict) else on_conflict
            output_path = resolve_conflict(target, strategy)
        else:
            output_path = target

        if output_path is None:
            return ConversionResult(source, None, "skipped", "使用者選擇略過（同名檔案已存在）")

        output_path.write_text(markdown, encoding="utf-8")
        return ConversionResult(source, output_path, "success")

    except PermissionError as e:
        return ConversionResult(source, None, "failed", f"無寫入權限：{e}")
    except Exception as e:  # 任何轉換例外都不可讓整個批次中斷
        return ConversionResult(source, None, "failed", f"{type(e).__name__}: {e}")


def convert_batch(
    paths: Iterable[str | Path], on_conflict: ConflictResolver = "rename"
) -> list[ConversionResult]:
    return [convert_file(f, on_conflict) for f in collect_files(paths)]


def _prompt_conflict(target: Path) -> ConflictStrategy:
    while True:
        choice = input(f"「{target.name}」已存在，要 [o]覆蓋 / [s]略過 / [r]另存新檔？ ").strip().lower()
        if choice in ("o", "overwrite"):
            return "overwrite"
        if choice in ("s", "skip"):
            return "skip"
        if choice in ("r", "rename"):
            return "rename"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MarkItDown 轉檔核心邏輯 CLI 測試工具（M1，尚未接 UI）"
    )
    parser.add_argument("paths", nargs="+", help="要轉換的檔案或資料夾路徑")
    parser.add_argument(
        "--on-conflict",
        choices=["ask", "overwrite", "skip", "rename"],
        default="ask",
        help="同名 .md 已存在時的處理方式，預設每次詢問",
    )
    args = parser.parse_args()

    strategy: ConflictResolver = (
        _prompt_conflict if args.on_conflict == "ask" else args.on_conflict
    )

    results = convert_batch(args.paths, strategy)

    labels = {"success": "[OK]", "failed": "[FAIL]", "skipped": "[SKIP]"}
    for r in results:
        detail = f" -> {r.output.name}" if r.output else (f" ({r.message})" if r.message else "")
        print(f"{labels[r.status]} {r.source.name}{detail}")

    ok = sum(1 for r in results if r.status == "success")
    print(f"\n完成：{ok}/{len(results)} 成功")


if __name__ == "__main__":
    main()
