"""
解析政府採購法規 md 檔案，建立「條號 → 條文全文」查找字典。

用法：
    from law_lookup import load_law, lookup_article
    law = load_law("政府採購法.md")
    lookup_article(law, "第22條")   # -> 條文全文字串，找不到回傳 None
"""
import re
from pathlib import Path

LAW_DIR = Path(__file__).resolve().parent.parent.parent / "法規"

ARTICLE_HEADER_RE = re.compile(r"^第\s*([0-9]+(?:-[0-9]+)?)\s*條\s*$")


def normalize_article_key(raw: str) -> str:
    """把「第 22 條」「第22條」「第11-1條」等各種寫法統一成「第22條」「第11-1條」格式。"""
    m = re.match(r"第\s*([0-9]+(?:-[0-9]+)?)\s*條", raw.strip())
    if not m:
        return raw.strip()
    return f"第{m.group(1)}條"


def load_law(filename: str) -> dict:
    """解析單一法規 md 檔案，回傳 {條號: 條文全文} 字典。"""
    path = LAW_DIR / filename
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    articles = {}
    current_key = None
    current_lines = []

    def flush():
        if current_key is not None:
            body = "\n".join(current_lines).strip()
            body = re.sub(r"\n{2,}", "\n", body)
            articles[current_key] = body

    for line in lines:
        m = ARTICLE_HEADER_RE.match(line.strip())
        if m:
            flush()
            current_key = normalize_article_key(line.strip())
            current_lines = []
        else:
            if current_key is not None:
                current_lines.append(line)
    flush()
    return articles


def lookup_article(law: dict, ref: str) -> str | None:
    key = normalize_article_key(ref)
    return law.get(key)


if __name__ == "__main__":
    gpa = load_law("政府採購法.md")
    print(f"政府採購法 共解析 {len(gpa)} 條")
    print("--- 第22條 ---")
    print(lookup_article(gpa, "第22條"))
    print()
    print("--- 第2條 ---")
    print(lookup_article(gpa, "第2條"))

    rules = load_law("政府採購法施行細則.md")
    print(f"\n政府採購法施行細則 共解析 {len(rules)} 條")
