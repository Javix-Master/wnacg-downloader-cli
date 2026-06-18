# WNACG Downloader CLI

**專為 CLI 工作流設計的 WNACG 下載工具，深度整合 Hermes Agent & OpenClaw**

## 基於 / Based On

| 原始專案 | 說明 |
|----------|------|
| [lanyeeee/wnacg-downloader](https://github.com/lanyeeee/wnacg-downloader) | WNACG 下載器（Tauri GUI + Rust），API 分析與下載流程參考 |

本專案為其 **CLI 重生版**，由 Hermes Agent 協助實作，專注以下目標：

- 🖥️ **純 CLI**：無 GUI，完美適配 terminal / SSH / cron / agent 工作流
- 🤖 **Agent 友善**：所有輸出可程式化解析，exit code 語意明確
- 📦 **uv 管理**：零系統污染，一行 `uv sync` 即用
- 🔁 **批量可靠**：支援 ID 清單批量下載 + comic 間隔 + 並行控制
- 📤 **多重匯出**：CBZ（含 ComicInfo.xml）+ PDF
- 🧩 **內建 Skill**：隨專案附 Hermes 引導恢復流程，開箱即用

---

## Hermes Agent / OpenClaw 快速整合

本工具從設計之初就以 agent 使用場景為核心考量。

### 一行指令整合

```bash
# 在 Hermes skill / cron job / OpenClaw 中直接呼叫
cd /path/to/wnacg-downloader-cli
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg search "關鍵字" --page 1
```

### Agent 友善特性

| 特性 | 說明 |
|------|------|
| **結構化輸出** | search / info 輸出易於 grep / jq 解析 |
| **明確 exit code** | 0 = 成功，非 0 = 失敗（含錯誤訊息到 stderr） |
| **無互動提示** | 所有操作可無人值守執行 |
| **進度條可控** | `--no-progress` 關閉 tqdm（適合 log 輸出） |
| **--force** | 覆蓋已下載，確保冪等 |

### 專案內建 Skills

本專案隨附完整 Hermes Skills，可直接載入使用：

```
skills/
├── README.md                           # Skills 總覽
├── wnacg-hermes-guided-recovery/       # 5 步驟精準恢復 pipeline
│   ├── SKILL.md
│   └── references/
└── examples/                           # 🆕 快速上手範例
    ├── search-and-download.md          # 搜尋 + 下載範例
    └── batch-from-list.md              # 從清單批量下載範例
```

---

## 安裝與啟動

前提：已安裝 [uv](https://docs.astral.sh/uv/)

```bash
# 進入專案目錄
cd /home/tsengagent/Nextcloud/Project/tools_工具開發/wnacg-downloader-cli

# 首次同步依賴
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv sync

# 驗證 CLI
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg --help
```

**重要**：所有指令必須加上 `env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run ...`

---

## 完整使用方法

### 1. 搜尋漫畫

```bash
# 關鍵字搜尋
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg search "艦これ" --page 1

# 標籤搜尋
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg search "ブルーアーカイブ" --tag

# Agent 模式（關閉進度條，輸出精簡）
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg search "艦これ" --no-progress
```

輸出格式（agent 可解析）：
```
ID      標題                               分類        頁數
288694  ある作品名                          同人誌      32P
```

### 2. 查看詳細資訊

```bash
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg info 288694
```

輸出含：ID、標題、分類、頁數、標籤、圖片 URL 清單。

### 3. 下載單本

```bash
# 指定目錄 + 並行數
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download 288694 --dir /tmp/wnacg --concurrency 3

# 強制覆蓋 + 無進度條（agent 模式）
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download 288694 --force --no-progress
```

### 4. 批量下載（從 ID 清單）

```bash
# ids.txt 每行一個漫畫 ID
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download \
  --list /tmp/ids.txt --concurrency 2 --dir /tmp/wnacg-batch
```

### 5. 匯出 CBZ / PDF

```bash
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg export "/tmp/wnacg/作品標題" --format cbz
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg export "/tmp/wnacg/作品標題" --format pdf
```

### 6. 配置管理

```bash
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg config --show
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg config --set-comic-interval 300
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg config --set-img-concurrency 4
```

---

## Hermes Skill 範例

### 快速搜尋並下載

```bash
# 在 Hermes 中，只需告訴 agent：
# 「幫我用 wnacg 搜尋『艦これ』第一頁，找出最新的同人誌並下載」
# Agent 會：
# 1. wnacg search "艦これ" --page 1
# 2. 解析輸出，找到目標 ID
# 3. wnacg download <ID> --dir /tmp/wnacg --concurrency 3
# 4. wnacg export <DIR> --format cbz
```

完整範例見 `skills/examples/search-and-download.md`

### 從清單批量恢復（missmission）

```bash
# 使用內建 recover_deleted_list.py 產生 ID 清單
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run python recover_deleted_list.py \
  --manifest-list /path/to/誤刪清單.txt \
  --search-top 2 --output /tmp/ids.txt

# Agent 驗證 + 批量下載
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download \
  --list /tmp/ids.txt --concurrency 2 --dir /tmp/wnacg-recover
```

完整流程見 `skills/examples/batch-from-list.md` 及內建 `wnacg-hermes-guided-recovery` skill。

---

## 目錄結構

```
wnacg-downloader-cli/
├── pyproject.toml
├── README.md
├── recover_deleted_list.py     # 缺失恢復輔助腳本
├── src/
│   └── wnacg_downloader/
│       ├── cli.py              # CLI 入口（argparse）
│       ├── client.py           # WNACG API / HTML 抓取
│       ├── config.py           # 配置讀寫（~/.config/wnacg-downloader/）
│       ├── downloader.py       # 多執行緒下載引擎
│       ├── exporter.py         # CBZ / PDF 匯出 + ComicInfo.xml
│       └── utils.py            # 共用工具
├── skills/                     # Hermes Agent Skills
│   ├── README.md
│   ├── wnacg-hermes-guided-recovery/
│   │   ├── SKILL.md            # 5 步驟精準恢復 pipeline
│   │   └── references/
│   └── examples/
│       ├── search-and-download.md   # 搜尋+下載範例
│       └── batch-from-list.md       # 批量恢復範例
└── .python-version
```

---

## 注意事項

- **下載目錄**：建議先用 `/tmp/wnacg-xxx`，完成後再搬移或 export
- **並行與間隔**：大量下載請設 concurrency=2~3 + comic_interval=300s
- **Agent 模式**：加 `--no-progress` 關閉 tqdm，適合 log / cron
- **僅供個人學習研究使用**

---

## 相關資源

- **原始專案**：[lanyeeee/wnacg-downloader](https://github.com/lanyeeee/wnacg-downloader)
- **GitHub**：[Javix-Master/wnacg-downloader-cli](https://github.com/Javix-Master/wnacg-downloader-cli)
- **Hermes Skill**：`skills/wnacg-hermes-guided-recovery/SKILL.md`
- **快速範例**：`skills/examples/`

**本工具為完整可運作的 CLI 版本，專為 agent 工作流優化。**
