# Hermes Agent Skill 範例：從清單批量恢復漫畫

## 適用場景

- 從誤刪清單批量恢復缺失的漫畫
- 與 `recover_deleted_list.py` + Hermes 引導流程搭配
- 適合 missmission 工作流

## 前置條件

```bash
cd /home/tsengagent/Nextcloud/Project/tools_工具開發/wnacg-downloader-cli
```

## 完整流程

### Step 1：產生 ID 建議清單

使用內建的 `recover_deleted_list.py` 從誤刪清單生成建議 ID：

```bash
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run python recover_deleted_list.py \
  --manifest-list /home/tsengagent/Nextcloud/Project/develop_軟體開發/missmission/漫畫本子誤刪清單.txt \
  --search-top 2 \
  --output /tmp/ids_recover.txt
```

輸出範例：
```
# search: 作品標題A
#   1. 288694  作品A (同人誌, 32P)      ← 建議
#   2. 300123  不同作品 (同人誌, 24P)

288694
# search: 作品標題B
#   1. 299888  作品B (單行本, 180P)     ← 建議

299888
```

### Step 2：Hermes 驗證（強烈建議）

在 Hermes 中載入內建 skill：

```
skill_view('wnacg-hermes-guided-recovery')
```

讓 Hermes 用 browser 工具逐筆確認：
- 標題吻合度
- 頁數合理
- 封面確認

### Step 3：批量下載

```bash
# 使用驗證後的 ID 清單
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download \
  --list /tmp/ids_recover.txt \
  --concurrency 2 \
  --comic-interval 300 \
  --dir /tmp/wnacg-recover \
  --no-progress
```

參數說明：
| 參數 | 建議值 | 原因 |
|------|--------|------|
| `--concurrency` | 2~3 | 避免觸發 WNACG 防護 |
| `--comic-interval` | 300 | 每本間隔 5 分鐘 |
| `--no-progress` | 建議 | 減少 log 輸出 |

### Step 4：後處理

```bash
# 檢查下載結果
ls /tmp/wnacg-recover/

# 逐本匯出 CBZ
for dir in /tmp/wnacg-recover/*/; do
  env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg export "$dir" --format cbz --out /tmp/wnacg-exports/
done

# 搬到 Nextcloud（避免 quota 問題）
rclone copy /tmp/wnacg-exports/ nextcloud:Project/develop_軟體開發/missmission/recovered/

# 清理
rm -rf /tmp/wnacg-recover /tmp/wnacg-exports
```

## Agent 整合提示

### 在 Hermes Cron Job 中使用

```bash
# cron 設定範例：
# schedule: 0 2 * * *（每天凌晨 2 點）
# prompt: 檢查 missmission 誤刪清單，如有新條目則搜尋建議 ID
#         並將結果寫入 /tmp/ids_recover.txt，發送通知給使用者

env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run python recover_deleted_list.py \
  --manifest-list /path/to/清單.txt \
  --search-top 2 --output /tmp/ids_$(date +%Y%m%d).txt
```

### 與 Hermes Guided Recovery Skill 協同

本範例是 `wnacg-hermes-guided-recovery` skill 的快速上手版。
完整 5 步驟 pipeline + 批次準備模式 + 執行陷阱，請見：
- `skills/wnacg-hermes-guided-recovery/SKILL.md`
- `skills/wnacg-hermes-guided-recovery/references/batch-preparation-patterns.md`
- `skills/wnacg-hermes-guided-recovery/references/execution-pitfalls-and-fixes.md`

## 注意事項

- 大於 200 頁的本子用 concurrency=2
- 用 `/tmp` 下載避免 Nextcloud 即時同步大量小檔
- 每次完成後立即 rclone + 清理 /tmp
