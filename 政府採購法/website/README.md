# 政府採購法練習測驗網站

依 [政府採購法練習網站_開發規格書v1.md](../政府採購法練習網站_開發規格書v1.md) 實作的第一、二階段練習網站：分類練習、隨機測驗、模擬考（倒數計時＋成績）、錯題本（localStorage）。

## 題庫資料來源

`src/data/questions.json` 由 `20260625全部題庫.pdf` 解析而來，該 PDF 來源為行政院公共工程委員會「政府電子採購網」公開題庫查詢系統
（<https://web.pcc.gov.tw/psms/plrtqdm/questionPublic/indexReadQuestion>），屬官方公開題庫，非商業付費題庫。

若要重新產生 `questions.json`（例如題庫更新後）：

1. 到上述網站下載最新版題庫 PDF，放到專案上層目錄。
2. 修改 `scripts/parse_pdf.py` 內的 `PDF_PATH` 指向該 PDF 檔案位置。
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
