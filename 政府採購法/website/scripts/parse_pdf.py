"""
解析 20260625全部題庫.pdf，輸出 src/data/questions.json。

格式細節（詳見 D:\\Cowork Project\\政府採購法\\政府採購法練習網站_開發規格書v1.md 第 6.3 節）：
- PDF 由 Apache FOP 產生，每頁分頁處會插入 \\x0c（form feed），需先移除，
  否則剛好落在頁首第一題題號前的題目會抓不到。
- 每題格式為「編號 答案代號 題幹(含選項)」，題目之間以空白行分隔。
- 第 12-14 類（政府採購法之總則/履約管理及驗收/罰則及附則）額外有「依據法源」欄位，
  其文字會插在題幹中間（PDF 表格欄位斷行造成），需要辨識並抽離，
  不能當成題幹的一部分，否則題目文字會被「第22條」這類字串打斷。
"""
import json
import re
from collections import Counter
from pathlib import Path

from pdfminer.high_level import extract_text

SCRIPT_DIR = Path(__file__).resolve().parent
PDF_PATH = SCRIPT_DIR.parent.parent / "20260625全部題庫.pdf"
OUTPUT_PATH = SCRIPT_DIR.parent / "src" / "data" / "questions.json"
REPORT_PATH = SCRIPT_DIR / "_parse_report.txt"

# (顯示用類別全名, id 用短代號)
CATEGORIES = [
    ("工程及技術服務採購作業", "eng"),
    ("財物及勞務採購作業", "goods"),
    ("最有利標及評選優勝廠商", "mostfav"),
    ("電子採購實務", "epro"),
    ("錯誤採購態樣", "error"),
    ("投標須知及招標文件製作", "bidding"),
    ("採購契約", "contract"),
    ("底價及價格分析", "price"),
    ("政府採購法之爭議處理", "dispute"),
    ("道德規範及違法處置", "ethics"),
    ("政府採購全生命週期概論", "lifecycle"),
    ("政府採購法之總則、招標及決標", "act-general"),
    ("政府採購法之履約管理及驗收", "act-perform"),
    ("政府採購法之罰則及附則", "act-penalty"),
]

LEGAL_TOKEN = (
    r"第\s*[0-9零一二三四五六七八九十百千]+\s*條"
    r"(?:之[一二三四五六七八九十0-9]+)?"
    r"(?:第[一二三四五六七八九十0-9]+項)?"
    r"(?:第[一二三四五六七八九十0-9]+款)?"
)
LEGAL_RE = re.compile(rf"^(?:{LEGAL_TOKEN}|綜合)(?:[、,，]?\s*(?:{LEGAL_TOKEN}|綜合))*$")
LEGAL_TOKEN_RE = re.compile(LEGAL_TOKEN + "|綜合")

QSTART_RE = re.compile(r"\n(\d+)\s+([1-4OX])\s")


def clean_legal_ref(raw: str) -> str:
    """去除依據法源欄位常見的重複字串（PDF 抽取瑕疵），保留去重後的條號清單。"""
    if raw == "綜合":
        return raw
    tokens = LEGAL_TOKEN_RE.findall(raw)
    seen = []
    for t in tokens:
        if t not in seen:
            seen.append(t)
    return "、".join(seen) if seen else raw


def split_body_into_chunks(body: str):
    return [c.strip() for c in re.split(r"\n\s*\n", body) if c.strip()]


def extract_stem_and_ref(body: str):
    chunks = split_body_into_chunks(body)
    legal_ref_raw = None
    stem_parts = []
    for c in chunks:
        collapsed = re.sub(r"\s+", "", c)
        if LEGAL_RE.match(collapsed):
            legal_ref_raw = collapsed
        else:
            stem_parts.append(re.sub(r"\s*\n\s*", "", c))
    full_text = "".join(stem_parts)
    legal_ref = clean_legal_ref(legal_ref_raw) if legal_ref_raw else None
    return full_text, legal_ref


def split_single_choice(full_text: str):
    idx1 = full_text.find("(1)")
    idx2 = full_text.find("(2)", idx1 + 1) if idx1 != -1 else -1
    idx3 = full_text.find("(3)", idx2 + 1) if idx2 != -1 else -1
    idx4 = full_text.find("(4)", idx3 + 1) if idx3 != -1 else -1
    if -1 in (idx1, idx2, idx3, idx4):
        return None
    stem = full_text[:idx1].strip()
    a = full_text[idx1 + 3 : idx2].strip()
    b = full_text[idx2 + 3 : idx3].strip()
    c = full_text[idx3 + 3 : idx4].strip()
    d = full_text[idx4 + 3 :].strip()
    return stem, [a, b, c, d]


def strip_trailing_period(s: str) -> str:
    return s[:-1] if s.endswith("。") else s


def main():
    raw_text = extract_text(str(PDF_PATH))
    text = raw_text.replace("\x0c", "")

    cat_positions = []
    for cat, slug in CATEGORIES:
        idx = text.find("\n" + cat + "\n")
        if idx == -1:
            raise RuntimeError(f"找不到類別標題：{cat}")
        cat_positions.append((idx, cat, slug))
    cat_positions.sort(key=lambda t: t[0])

    questions = []
    anomalies = []
    per_cat_counts = Counter()

    for i, (pos, cat, slug) in enumerate(cat_positions):
        end = cat_positions[i + 1][0] if i + 1 < len(cat_positions) else len(text)
        section = text[pos:end]

        sel_idx = section.find("選擇題")
        tf_idx = section.find("是非題")
        if sel_idx == -1:
            blocks = [("tf", section[tf_idx:])]
        elif tf_idx == -1:
            blocks = [("single", section[sel_idx:])]
        elif sel_idx < tf_idx:
            blocks = [("single", section[sel_idx:tf_idx]), ("tf", section[tf_idx:])]
        else:
            blocks = [("tf", section[tf_idx:sel_idx]), ("single", section[sel_idx:])]

        for btype, block in blocks:
            matches = list(QSTART_RE.finditer(block))
            for j, m in enumerate(matches):
                num, ans = m.group(1), m.group(2)
                start = m.end()
                stop = matches[j + 1].start() if j + 1 < len(matches) else len(block)
                body = block[start:stop]
                full_text, legal_ref = extract_stem_and_ref(body)

                qid = f"{slug}-{btype}-{int(num):03d}"

                if btype == "single":
                    result = split_single_choice(full_text)
                    if result is None:
                        anomalies.append((qid, cat, "single-choice 選項切分失敗", full_text[:80]))
                        continue
                    stem, opts = result
                    q = {
                        "id": qid,
                        "category": cat,
                        "type": "single",
                        "stem": stem,
                        "options": {
                            "A": strip_trailing_period(opts[0]),
                            "B": strip_trailing_period(opts[1]),
                            "C": strip_trailing_period(opts[2]),
                            "D": strip_trailing_period(opts[3]),
                        },
                        "answer": chr(ord("A") + int(ans) - 1),
                    }
                else:
                    if "(1)" in full_text or "(2)" in full_text:
                        anomalies.append((qid, cat, "是非題卻含有選項標記", full_text[:80]))
                        continue
                    if ans not in ("O", "X"):
                        anomalies.append((qid, cat, f"是非題答案代號異常:{ans}", full_text[:80]))
                        continue
                    q = {
                        "id": qid,
                        "category": cat,
                        "type": "tf",
                        "stem": strip_trailing_period(full_text.strip()),
                        "answer": ans == "O",
                    }

                if legal_ref:
                    q["source_legal_ref"] = legal_ref

                questions.append(q)
                per_cat_counts[cat] += 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(f"總題數：{len(questions)}\n")
        f.write(f"異常題數：{len(anomalies)}\n\n")
        f.write("各類別題數：\n")
        for cat, _ in CATEGORIES:
            f.write(f"  {cat}: {per_cat_counts[cat]}\n")
        if anomalies:
            f.write("\n異常清單：\n")
            for qid, cat, reason, snippet in anomalies:
                f.write(f"  [{qid}] {cat} - {reason}\n    片段: {snippet}\n")

    print(f"done: {len(questions)} questions, {len(anomalies)} anomalies")
    print(f"output: {OUTPUT_PATH}")
    print(f"report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
