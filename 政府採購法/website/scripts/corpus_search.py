"""
跨檔案關鍵字搜尋工具，涵蓋 法規/ 資料夾下所有 md 檔案（不含題庫本身）。

用途：law_lookup.py 只能查「政府採購法／施行細則」逐條內容，遇到沒有明確
source_legal_ref、或依據其實藏在其他子法規/稽核彙編案例裡的題目時，
用這支工具做全文關鍵字搜尋補上。

用法：
    from corpus_search import search_corpus
    hits = search_corpus(["評選優勝廠商", "不以一家為限"])
    for filename, snippet in hits:
        print(filename, snippet)
"""
import re
from pathlib import Path

LAW_DIR = Path(__file__).resolve().parent.parent.parent / "法規"

# 題庫本身不是「依據」來源，排除；避免拿題庫的敘述來佐證題庫自己的答案（循環論證）
EXCLUDE_FILENAMES = {"20260625全部題庫.md"}


def _iter_corpus_files():
    for path in LAW_DIR.glob("*.md"):
        if path.name in EXCLUDE_FILENAMES:
            continue
        yield path


def search_corpus(keywords, context_chars: int = 200, max_hits_per_file: int = 3):
    """
    對 法規/ 資料夾下所有 md 檔案做關鍵字搜尋（AND 邏輯：keywords 需全部出現在同一段落附近）。
    回傳 [(檔名, 命中段落), ...]，依命中檔案排序。
    """
    if isinstance(keywords, str):
        keywords = [keywords]

    results = []
    for path in _iter_corpus_files():
        text = path.read_text(encoding="utf-8")
        # 用第一個關鍵字定位候選位置，再檢查其餘關鍵字是否在鄰近範圍內
        first_kw = keywords[0]
        hits_in_file = 0
        for m in re.finditer(re.escape(first_kw), text):
            if hits_in_file >= max_hits_per_file:
                break
            start = max(0, m.start() - context_chars)
            end = min(len(text), m.end() + context_chars)
            window = text[start:end]
            if all(kw in window for kw in keywords[1:]):
                snippet = re.sub(r"\n{2,}", "\n", window.strip())
                results.append((path.name, snippet))
                hits_in_file += 1
    return results


if __name__ == "__main__":
    import sys

    kws = sys.argv[1:] or ["評選優勝廠商", "不以一家為限"]
    hits = search_corpus(kws)
    with open("_corpus_search_test.txt", "w", encoding="utf-8") as f:
        f.write(f"關鍵字：{kws}\n共 {len(hits)} 筆命中\n\n")
        for filename, snippet in hits:
            f.write(f"=== {filename} ===\n{snippet}\n\n")
    print(f"done, {len(hits)} hits, see _corpus_search_test.txt")
