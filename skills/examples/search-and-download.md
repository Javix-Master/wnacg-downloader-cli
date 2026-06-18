# Hermes Agent Skill 範例：搜尋並下載漫畫

## 適用場景

- 在 Hermes / OpenClaw 對話中快速搜尋並下載 WNACG 漫畫
- 適合 Cron Job 定期檢查新刊
- 可作為其他 Skill 的子步驟

## 前置條件

```bash
# 確保工具已安裝
cd /home/tsengagent/Nextcloud/Project/tools_工具開發/wnacg-downloader-cli
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg --help
```

## Skill 範本

### 簡單搜尋 + 下載

當使用者說「幫我下載 WNACG 最新的艦これ同人誌」時：

```bash
# Step 1: 搜尋
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg search "艦これ" --page 1

# Step 2: 從輸出選擇目標 ID（例如第一筆：288694）

# Step 3: 查看資訊確認
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg info 288694

# Step 4: 下載
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download 288694 \
  --dir /tmp/wnacg-dl --concurrency 3

# Step 5: 匯出 CBZ
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg export \
  "/tmp/wnacg-dl/作品標題" --format cbz
```

### 搜尋 + 瀏覽器驗證（高準確度）

當需要精準判斷搜尋結果時，結合 Hermes browser 工具：

```bash
# 1. 先取得搜尋結果 ID 清單
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg search "關鍵字" --page 1

# 2. 用 browser 打開候選頁面確認
# browser_navigate "https://www.wn06.cfd/photos-index-aid-<ID>.html"

# 3. 確認後下載
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download <ID>
```

### 定期 Cron Job 範例

每週檢查特定標籤是否有新刊：

```bash
# cron job prompt:
# 使用 wnacg CLI 搜尋標籤 "艦これ" 最新一頁
# 如果有今天日期的新刊，下載並匯出到 /tmp/wnacg-weekly/

env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg search "艦これ" --page 1 --no-progress
# 解析輸出，篩選新刊...
```

## Agent 輸出解析指南

`wnacg search` 輸出行格式：
```
ID      標題                    分類      頁數
288694  作品標題                同人誌     32P
```

用 `awk` / `grep` / Python 解析：
```bash
# 取得第一筆 ID
wnacg search "關鍵字" --no-progress | grep -oP '^\d+' | head -1

# 取得所有 ID
wnacg search "關鍵字" --no-progress | grep -oP '^\d+'
```

## 注意事項

- 大量下載時請設 `--comic-interval 300` 避免被封
- Agent 模式建議加 `--no-progress` 關閉進度條
- 下載完成檢查 exit code（0 = 成功）
