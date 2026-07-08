# 政府採購法練習測驗網站

依 [政府採購法練習網站_開發規格書v1.md](../政府採購法練習網站_開發規格書v1.md) 實作的第一、二階段練習網站：分類練習、隨機測驗、模擬考（倒數計時＋成績）、錯題本（localStorage）。

## 題庫資料（未包含在本 repo）

`src/data/questions.json` 未納入版本控制，因為它是由題庫 PDF 解析而來，內容授權來源未確認（見規格書第 11 節風險清單），不公開發布題目全文。

若要在本機產生 `questions.json`：

1. 準備一份題庫 PDF（格式需符合 `scripts/parse_pdf.py` 開頭註解所述的表格結構）。
2. 修改 `scripts/parse_pdf.py` 內的 `PDF_PATH` 指向你的 PDF 檔案位置。
3. 安裝 Python 相依套件：`pip install pdfminer.six`
4. 執行：
   ```
   cd scripts
   python parse_pdf.py
   ```
   會在 `src/data/questions.json` 產出結構化題庫，並在 `scripts/_parse_report.txt` 輸出各類別題數與解析異常清單。

## 開發

```
npm install
npm run dev
```

需要先產生 `questions.json`，否則首頁分類清單會是空的。
