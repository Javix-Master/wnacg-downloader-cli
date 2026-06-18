# 範例：搜尋並下載漫畫

## 適用場景

- 快速搜尋並下載 WNACG 漫畫
- 定期檢查特定關鍵字／標籤的新刊（cron）
- 作為其他流程的子步驟

## 前置條件

```bash
cd /path/to/wnacg-downloader-cli
uv run wnacg --help
```

## 簡單搜尋 + 下載

當使用者說「幫我下載最新的艦これ同人誌」時：

```bash
# Step 1: 搜尋
uv run wnacg search "艦これ" --page 1

# Step 2: 從輸出挑目標 ID（例如第一筆 288694）

# Step 3: 確認資訊
uv run wnacg info 288694

# Step 4: 下載
uv run wnacg download 288694 --dir /tmp/wnacg-dl --concurrency 3

# Step 5: 匯出 CBZ
uv run wnacg export "/tmp/wnacg-dl/作品標題" --format cbz
```

## 搜尋 + 瀏覽器驗證（高準確度）

需要精準判斷時，先取結果再用瀏覽器確認：

```bash
uv run wnacg search "關鍵字" --page 1
# 在瀏覽器開 https://<domain>/photos-index-aid-<ID>.html 確認封面/標籤/頁數
uv run wnacg download <ID>
```

## 定期 Cron Job 範例

```bash
# prompt 範例：搜尋標籤 "艦これ" 最新一頁，若有新刊則下載並匯出到 /tmp/wnacg-weekly/
uv run wnacg search "艦これ" --page 1 --tag
# 解析輸出，篩選新刊...
```

## Agent 輸出解析

`wnacg search` 每筆輸出三行：

```
ID:  288694 | 作品標題……
     additional info（分類 / 頁數 等）
     cover: https://…
```

用 grep 取 ID：

```bash
# 第一筆 ID
uv run wnacg search "關鍵字" | grep -oP '^ID:\s*\K\d+' | head -1

# 所有 ID
uv run wnacg search "關鍵字" | grep -oP '^ID:\s*\K\d+'
```

## 注意事項

- 大量／大本下載設 `--concurrency 2~3`，批量加 `--comic-interval 300`。
- Agent / cron 模式加 `--no-progress`。
- 以 exit code 判斷成敗（0 = 成功），錯誤訊息在 stderr。
- 受管 venv 環境若 uv 受干擾，指令前加 `env -u VIRTUAL_ENV -u SSL_CERT_FILE`。
</content>
