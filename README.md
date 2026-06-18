# WNACG 绅士漫畫下載器 (Python CLI 版)

**原專案**：https://github.com/lanyeeee/wnacg-downloader (Tauri GUI + Rust)

本專案為 **CLI 版本**，由 Hermes 協助製作：

- 使用 **uv** 進行 Python 環境與依賴管理
- 純 **argparse** 命令列界面（無 GUI）
- 核心搜尋 / 資訊 / 下載 / 匯出邏輯完整實作
- 支援多執行緒圖片並行下載、進度條、元資料儲存、CBZ / PDF 匯出
- 專為「缺失漫畫恢復」（missmission）優化，同時可作為一般下載工具

---

## 專案位置（Nextcloud 規範）

```
Nextcloud/Project/tools_工具開發/wnacg-downloader-python_绅士漫畫下載器/
```

此為**正式工具存放位置**。missmission 相關工作區（清單、recovered/）仍位於 `develop_軟體開發/missmission/`。

---

## 安裝與啟動

前提：已安裝 [uv](https://docs.astral.sh/uv/)

```bash
# 進入專案目錄
cd /home/tsengagent/Nextcloud/Project/tools_工具開發/wnacg-downloader-python_绅士漫畫下載器

# 首次同步依賴（建立 .venv）
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv sync

# 驗證 CLI（**務必使用此前綴**）
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg --help
```

**重要**：所有執行指令都必須加上 `env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run ...` 以避免與系統或其它 venv 衝突。

---

## 完整使用方法

### 1. 搜尋漫畫

```bash
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg search "ブルーアーカイブ" --page 1
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg search "艦これ" --tag   # 標籤搜尋
```

### 2. 查看漫畫詳細資訊（含圖片清單預覽）

```bash
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg info 288694
```

輸出包含：ID、標題、分類、頁數、標籤、簡介、前幾張與最後一張圖片 URL。

### 3. 下載單本

```bash
# 基本下載（使用預設下載目錄）
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download 288694

# 指定下載目錄 + 強制重新下載
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download 288694 --dir /tmp/wnacg-test --force

# 調整並行數（大本建議 2~4）
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download 288694 --concurrency 3
```

### 4. 批量下載（最常用於缺失恢復）

準備 `ids.txt`（每行一個數字 ID）：

```bash
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download --list /tmp/ids_to_recover.txt --concurrency 3 --dir /tmp/wnacg-recover
```

### 5. 登入（書架功能）

```bash
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg login -u 你的帳號 -p 你的密碼
```

登入成功後 cookie 自動存到 `~/.config/wnacg-downloader/config.json`

### 6. 查看書架

```bash
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg shelf 0 --page 1
```

### 7. 匯出為 CBZ / PDF（閱讀器相容）

```bash
# CBZ（推薦，內含 ComicInfo.xml）
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg export "/tmp/wnacg-recover/某漫畫標題" --format cbz

# PDF（無損）
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg export "/tmp/wnacg-recover/某漫畫標題" --format pdf --out /tmp/exports/
```

### 8. 配置管理

```bash
# 查看目前設定
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg config --show

# 常用設定
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg config --set-download-dir /tmp/wnacg-downloads
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg config --set-img-concurrency 4
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg config --set-comic-interval 300   # 每本間隔 5 分鐘，避免被封
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg config --set-domain www.wn06.cfd
```

---

## 缺失漫畫恢復專用流程（missmission）

1. 從 `develop_軟體開發/missmission/漫畫本子誤刪清單.txt` 讀取標題
2. 使用輔助腳本產生建議 ID（**建議先只產生清單**）：

```bash
cd /home/tsengagent/Nextcloud/Project/tools_工具開發/wnacg-downloader-python_绅士漫畫下載器

env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run python recover_deleted_list.py \
  --manifest-list /home/tsengagent/Nextcloud/Project/develop_軟體開發/missmission/漫畫本子誤刪清單.txt \
  --search-top 2 \
  --output /tmp/ids_recover.txt
```

3. **強烈建議**：用 Hermes + browser 手動驗證搜尋結果（參考 `wnacg-hermes-guided-recovery` skill 的 5 步驟）
4. 批量下載（建議用 /tmp 避免配額問題）：

```bash
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download \
  --list /tmp/ids_recover.txt --concurrency 2 --dir /tmp/wnacg-recover
```

5. 下載完成後後處理：
   - 檢查圖片數量
   - export 成標準命名 ZIP/CBZ
   - `rclone copy ... nextcloud:Project/develop_軟體開發/missmission/recovered/`
   - 記錄到 recovered.log

**重要提醒**：
- 大於 200 頁的本子請先用 concurrency=2 或 3
- 優先使用 Python 直接下載而非站內 ZIP 按鈕
- 每次背景下載完成後，立即進行 post-process + clean /tmp

---

## 目錄結構

```
wnacg-downloader-python_绅士漫畫下載器/
├── pyproject.toml
├── README.md
├── recover_deleted_list.py     # missmission 恢復輔助（可獨立使用）
├── src/
│   └── wnacg_downloader/
│       ├── __init__.py
│       ├── cli.py              # CLI 入口
│       ├── client.py           # API / 抓取
│       ├── config.py
│       ├── downloader.py       # 下載引擎 + 並行 + 進度
│       ├── exporter.py         # CBZ / PDF 匯出 + ComicInfo.xml
│       └── utils.py
└── .python-version
```

---

## 注意事項與最佳實踐

- **下載目錄建議**：先用 `/tmp/wnacg-xxx` ，完成後再搬移或 export，避免 Nextcloud 即時同步大量小檔造成問題。
- **並行與間隔**：預設 img_concurrency=8，comic_interval=0。大量下載務必調低 + 間隔 300s。
- **Cloudflare / 封鎖**：降低 concurrency、增加 img_interval、或稍後重試。
- **檔名**：下載時會正規化為 `0001.jpg` 等有序檔名 + `metadata.json`。
- **匯出相容**：CBZ 內含 ComicInfo.xml，可直接給 Kavita、Komga 等閱讀器使用。
- **僅供個人學習研究使用**。

---

## 開發與貢獻

```bash
cd 專案目錄
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg --help
# 修改後直接測試
```

---

## 相關資源

- missmission 清單與 recovered：`develop_軟體開發/missmission/`
- Hermes 引導恢復流程：載入 skill `wnacg-hermes-guided-recovery`
- 原始 Rust GUI 參考：同目錄下的 `wnacg-downloader/`（僅供研究）

**本工具為完整可運作的 CLI 版本**，已上傳至 Nextcloud Project 適當位置（tools_工具開發）。
