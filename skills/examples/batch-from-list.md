# 範例：從 ID 清單批量下載

## 適用場景

- 一次下載多本（已知或已驗證的 ID 清單）
- 從一批標題搜尋、確認後批量取回

## 前置條件

```bash
cd /path/to/wnacg-downloader-cli
```

## 完整流程

### Step 1：準備 ID 清單

直接手寫 `ids.txt`（每行一個 ID，`#` 開頭與非數字行會被忽略）：

```
288694
299888
311300
```

或從一批標題搜尋產生候選（單一 python 呼叫，效率較好）：

```python
from wnacg_downloader.client import WnacgClient
client = WnacgClient()
for kw in ["關鍵字A", "關鍵字B"]:
    res = client.search_by_keyword(kw, page_num=1)
    for c in res.comics[:3]:
        print(f"{c.id} | {c.title[:60]}")
```

> 選用：專案根目錄的 `recover_deleted_list.py` 可從一份「標題清單檔」自動搜尋並輸出建議 ID 清單，再餵給 `--list`。

### Step 2：驗證（建議）

對相近候選用 `wnacg info <ID>` 或瀏覽器確認標題／標籤／頁數，再把確定的 ID 留在清單裡。

### Step 3：批量下載

```bash
uv run wnacg download \
  --list ids.txt \
  --concurrency 2 \
  --comic-interval 300 \
  --dir /tmp/wnacg-batch \
  --no-progress
```

| 參數 | 建議值 | 原因 |
|------|--------|------|
| `--concurrency` | 2~3 | 避免觸發站點防護 |
| `--comic-interval` | 300 | 每本間隔 5 分鐘 |
| `--no-progress` | 建議 | 減少 log 輸出 |

任一本失敗時，結束後會列出失敗 ID 並以非 0 exit code 結束。

### Step 4：後處理

```bash
# 檢查下載結果
ls /tmp/wnacg-batch/

# 逐本匯出 CBZ
for dir in /tmp/wnacg-batch/*/; do
  uv run wnacg export "$dir" --format cbz --out /tmp/wnacg-exports/
done
```

## 注意事項

- 大於 200 頁的本子用 `--concurrency 2`。
- 失敗的本子可加 `--force` 對該 ID 重跑補齊。
- 受管 venv 環境若 uv 受干擾，指令前加 `env -u VIRTUAL_ENV -u SSL_CERT_FILE`。
</content>
