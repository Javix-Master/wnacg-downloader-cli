# WNACG Downloader CLI

**純命令列的 WNACG 漫畫搜尋／下載工具** — 以 `uv` + `argparse` 打造，輸出可程式化解析，適合 terminal / SSH / cron / agent 工作流。

## 功能

- 🔎 **搜尋**：關鍵字搜尋、標籤搜尋，分頁瀏覽
- 📖 **詳情**：查看單本的標題、分類、頁數、標籤、圖片清單
- ⬇️ **下載**：多執行緒下載整本，單張失敗自動重試＋退避，429 自動降速
- 📚 **批量**：從 ID 清單一次下載多本，每本間可設間隔避免被封
- 📤 **匯出**：CBZ（含 ComicInfo.xml，相容 Kavita 等閱讀器）或 PDF
- 🤖 **Agent 友善**：`--no-progress` 關閉進度條、錯誤輸出至 stderr、失敗以非 0 exit code 反映

## 基於 / Based On

| 原始專案 | 說明 |
|----------|------|
| [lanyeeee/wnacg-downloader](https://github.com/lanyeeee/wnacg-downloader) | WNACG 下載器（Tauri GUI + Rust），API 分析與下載流程參考 |

本專案為其 **CLI 重生版**，專注純命令列、批量可靠與 agent 整合。

---

## 安裝

前提：已安裝 [uv](https://docs.astral.sh/uv/)。

```bash
cd /path/to/wnacg-downloader-cli

# 同步依賴並建立虛擬環境
uv sync

# 驗證
uv run wnacg --help
```

> **受管 venv 環境（如某些 agent 容器）**：若 shell 預設帶有 `VIRTUAL_ENV` / `SSL_CERT_FILE` 而干擾 uv，可在指令前加 `env -u VIRTUAL_ENV -u SSL_CERT_FILE`，例如
> `env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg --help`

---

## 使用方法

### 1. 搜尋

```bash
# 關鍵字搜尋
uv run wnacg search "艦これ" --page 1

# 標籤搜尋（keyword 作為 tag 名）
uv run wnacg search "ブルーアーカイブ" --tag
```

輸出格式（每筆三行，可用 grep / awk / Python 解析）：

```
ID:  288694 | 作品標題……
     同人誌 | 32P | …additional info…
     cover: https://…
```

> 取所有 ID：`uv run wnacg search "關鍵字" | grep -oP '^ID:\s*\K\d+'`

### 2. 查看詳情

```bash
uv run wnacg info 288694
```

輸出：ID、標題、分類、頁數、封面、標籤、圖片 URL 清單（前 5 + 最後 1）。

### 3. 下載單本

```bash
# 基本
uv run wnacg download 288694

# 指定目錄 + 並行數 + 重試次數
uv run wnacg download 288694 --dir /tmp/wnacg --concurrency 3 --retries 5

# 強制重新下載 + 關閉進度條（agent / cron 模式）
uv run wnacg download 288694 --force --no-progress
```

下載流程：先存到 `<目錄>/.下载中-<標題>/`，全部完成後才改名為 `<目錄>/<標題>/`，避免中斷殘留半成品。**若整本零張成功，exit code 為非 0。**

### 4. 批量下載（從 ID 清單）

```bash
# ids.txt 每行一個漫畫 ID（# 開頭與非數字行會被忽略）
uv run wnacg download \
  --list ids.txt \
  --concurrency 2 \
  --comic-interval 300 \
  --dir /tmp/wnacg-batch
```

任一本失敗時，批量結束後會列出失敗 ID 並以非 0 exit code 結束。

### 5. 匯出 CBZ / PDF

```bash
uv run wnacg export "/tmp/wnacg/作品標題" --format cbz
uv run wnacg export "/tmp/wnacg/作品標題" --format pdf --out /tmp/exports
```

CBZ 會自動讀取下載目錄內的 `元数据.json` 產生 `ComicInfo.xml`。

### 6. 配置管理

設定存於 `~/.config/wnacg-downloader/config.json`。

```bash
# 查看
uv run wnacg config --show

# 設定（可組合）
uv run wnacg config --set-domain www.wn06.cfd
uv run wnacg config --set-download-dir ~/wnacg-downloads
uv run wnacg config --set-img-concurrency 4
uv run wnacg config --set-comic-interval 300   # 批量時建議 300s（5 分鐘）
```

`download` 的 `--concurrency` / `--comic-interval` / `--retries` 為單次覆蓋，不寫入設定檔。

### 7. 登入（選用，僅 shelf 需要）

```bash
uv run wnacg login -u <帳號> -p <密碼>   # 成功後 cookie 存入設定
uv run wnacg shelf 0 --page 1            # 列出書架
```

---

## 參數速查

| 子命令 | 主要參數 |
|--------|----------|
| `search <keyword>` | `--page/-p`、`--tag` |
| `info <comic_id>` | — |
| `download [comic_id]` | `--dir/-d`、`--force/-f`、`--concurrency/-c`、`--comic-interval`、`--retries`、`--no-progress`、`--list/-l` |
| `export <comic_dir>` | `--format/-f {cbz,pdf}`、`--out/-o` |
| `config` | `--show`、`--set-cookie`、`--set-download-dir`、`--set-export-dir`、`--set-domain`、`--set-img-concurrency`、`--set-img-interval`、`--set-comic-interval` |
| `login` | `--username/-u`、`--password/-p` |
| `shelf [shelf_id]` | `--page` |

---

## Agent / 自動化整合

| 特性 | 說明 |
|------|------|
| `--no-progress` | 關閉 tqdm 進度條，適合 log / cron / agent |
| Exit code | 0 = 成功；下載失敗（單本零成功、或批量有失敗項）= 非 0 |
| stderr | 錯誤與失敗摘要輸出至 stderr，正常結果至 stdout |
| `--force` | 覆蓋已下載，確保冪等 |
| 自動重試 | 單張圖片逾時／5xx／429 自動退避重試（`--retries` 調整） |

附帶 Skill（見 `skills/`）提供「搜尋 → 判斷目標 → 下載 → 匯出」的引導式流程，可載入 agent 使用。

---

## 目錄結構

```
wnacg-downloader-cli/
├── pyproject.toml
├── README.md
├── recover_deleted_list.py     # 選用：從標題清單批量產生建議 ID（搭配 --list 下載）
├── src/wnacg_downloader/
│   ├── cli.py                  # CLI 入口（argparse）
│   ├── client.py               # WNACG API / HTML 抓取
│   ├── config.py               # 配置讀寫
│   ├── downloader.py           # 多執行緒下載引擎（重試／退避）
│   ├── exporter.py             # CBZ / PDF 匯出 + ComicInfo.xml
│   └── utils.py                # 共用工具
└── skills/                     # Agent Skill（搜尋下載引導流程）
    ├── README.md
    ├── wnacg-search-download/
    └── examples/
```

---

## 注意事項

- **下載目錄**：建議先用暫存目錄（如 `/tmp/wnacg-*`），完成後再 export / 搬移。
- **並行與間隔**：大量或大本（>200 頁）建議 `--concurrency 2~3` + `--comic-interval 300`，降低被封風險。
- **站點域名**：站點會更換域名，必要時用 `config --set-domain` 更新。
- **Windows + 含中文路徑**：editable 安裝的 `.pth` 在 cp950 終端可能解碼失敗；建議將專案放在純 ASCII 路徑，或設 `PYTHONUTF8=1`。
- **僅供個人學習研究使用。**

---

## 相關資源

- 原始專案：[lanyeeee/wnacg-downloader](https://github.com/lanyeeee/wnacg-downloader)
- 本專案：[Javix-Master/wnacg-downloader-cli](https://github.com/Javix-Master/wnacg-downloader-cli)
- Skill：`skills/wnacg-search-download/SKILL.md`
</content>
</invoke>
