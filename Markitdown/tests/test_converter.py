import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import converter


def test_generate_incremented_path_when_no_conflict(tmp_path):
    target = tmp_path / "A.md"
    assert converter.generate_incremented_path(target) == target


def test_generate_incremented_path_increments(tmp_path):
    (tmp_path / "A.md").write_text("x")
    assert converter.generate_incremented_path(tmp_path / "A.md") == tmp_path / "A(1).md"

    (tmp_path / "A(1).md").write_text("x")
    assert converter.generate_incremented_path(tmp_path / "A.md") == tmp_path / "A(2).md"


def test_resolve_conflict_overwrite_returns_same_path(tmp_path):
    target = tmp_path / "A.md"
    target.write_text("old")
    assert converter.resolve_conflict(target, "overwrite") == target


def test_resolve_conflict_skip_returns_none(tmp_path):
    target = tmp_path / "A.md"
    target.write_text("old")
    assert converter.resolve_conflict(target, "skip") is None


def test_resolve_conflict_rename_returns_incremented_path(tmp_path):
    target = tmp_path / "A.md"
    target.write_text("old")
    assert converter.resolve_conflict(target, "rename") == tmp_path / "A(1).md"


def test_resolve_conflict_no_existing_file_ignores_strategy(tmp_path):
    target = tmp_path / "A.md"
    assert converter.resolve_conflict(target, "skip") == target


def test_collect_files_expands_folder_recursively(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "sub" / "b.txt").write_text("b")

    files = converter.collect_files([str(tmp_path)])

    assert {f.name for f in files} == {"a.txt", "b.txt"}


def test_collect_files_keeps_individual_file(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("a")

    assert converter.collect_files([str(f)]) == [f]


def test_collect_files_raises_for_missing_path(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError):
        converter.collect_files([str(tmp_path / "not_there.txt")])


def test_convert_file_skips_md_source(tmp_path):
    f = tmp_path / "already.md"
    f.write_text("已經是 markdown")

    result = converter.convert_file(f)

    assert result.status == "skipped"
    assert result.output is None


def test_convert_file_does_not_ask_conflict_when_no_conflict(tmp_path, monkeypatch):
    monkeypatch.setattr(converter, "convert_with_markitdown", lambda p: "content")

    f = tmp_path / "report.docx"
    f.write_text("x")

    def resolver(target):
        raise AssertionError("target.md 不存在，不應該詢問衝突策略")

    result = converter.convert_file(f, resolver)

    assert result.status == "success"
    assert result.output == tmp_path / "report.md"


def test_convert_file_asks_conflict_only_when_target_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(converter, "convert_with_markitdown", lambda p: "content")

    f = tmp_path / "report.docx"
    f.write_text("x")
    (tmp_path / "report.md").write_text("existing")

    calls = []

    def resolver(target):
        calls.append(target)
        return "rename"

    result = converter.convert_file(f, resolver)

    assert calls == [tmp_path / "report.md"]
    assert result.status == "success"
    assert result.output == tmp_path / "report(1).md"


def test_convert_file_rejects_unsupported_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(
        converter, "convert_with_markitdown", lambda p: (_ for _ in ()).throw(AssertionError("不應呼叫 markitdown"))
    )

    f = tmp_path / "virus.exe"
    f.write_bytes(b"\x00\x01not a real exe\xff\xfe")

    result = converter.convert_file(f)

    assert result.status == "failed"
    assert "不支援的格式" in result.message


def test_convert_file_rejects_no_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(
        converter, "convert_with_markitdown", lambda p: (_ for _ in ()).throw(AssertionError("不應呼叫 markitdown"))
    )

    f = tmp_path / "no_extension_file"
    f.write_text("hello")

    result = converter.convert_file(f)

    assert result.status == "failed"
    assert "不支援的格式" in result.message


def test_convert_file_reports_missing_source(tmp_path):
    result = converter.convert_file(tmp_path / "missing.pdf")
    assert result.status == "failed"
    assert "不存在" in result.message


def test_convert_file_dispatches_pdf_to_pdfminer(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(converter, "convert_pdf_to_text", lambda p: calls.append(p) or "純文字內容")
    monkeypatch.setattr(
        converter, "convert_with_markitdown", lambda p: (_ for _ in ()).throw(AssertionError("不應呼叫 markitdown"))
    )

    f = tmp_path / "doc.pdf"
    f.write_text("fake pdf bytes")

    result = converter.convert_file(f)

    assert result.status == "success"
    assert calls == [f]
    assert result.output.read_text(encoding="utf-8") == "純文字內容"


def test_convert_file_dispatches_other_formats_to_markitdown(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(converter, "convert_with_markitdown", lambda p: calls.append(p) or "轉出的內容")
    monkeypatch.setattr(
        converter, "convert_pdf_to_text", lambda p: (_ for _ in ()).throw(AssertionError("不應呼叫 pdfminer"))
    )

    f = tmp_path / "report.docx"
    f.write_text("fake docx bytes")

    result = converter.convert_file(f)

    assert result.status == "success"
    assert calls == [f]


def test_convert_file_failure_does_not_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(
        converter, "convert_with_markitdown", lambda p: (_ for _ in ()).throw(RuntimeError("boom"))
    )

    f = tmp_path / "broken.docx"
    f.write_text("x")

    result = converter.convert_file(f)

    assert result.status == "failed"
    assert "boom" in result.message


def test_convert_batch_continues_after_one_failure(tmp_path, monkeypatch):
    def fake_markitdown(p: Path) -> str:
        if p.name == "bad.docx":
            raise RuntimeError("broken file")
        return "ok"

    monkeypatch.setattr(converter, "convert_with_markitdown", fake_markitdown)

    (tmp_path / "good.docx").write_text("x")
    (tmp_path / "bad.docx").write_text("x")

    results = converter.convert_batch([str(tmp_path)], on_conflict="rename")

    statuses = {r.source.name: r.status for r in results}
    assert statuses == {"good.docx": "success", "bad.docx": "failed"}
