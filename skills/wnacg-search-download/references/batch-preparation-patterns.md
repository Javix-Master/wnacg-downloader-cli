# Batch Preparation & Verification Patterns

可重用的批量搜尋與下載準備技巧（適用一次處理多本）。

## 高效多關鍵字搜尋
把多個關鍵字放進**單一** python 呼叫，避免重複啟動成本：
```python
from wnacg_downloader.client import WnacgClient
client = WnacgClient()

candidates = [
    ("社團 核心作品名 漢化組", "原始全名（備註用）"),
    # ... 可放多筆
]
for kw, note in candidates:
    print(f"\n=== Searching: {kw} ===")
    res = client.search_by_keyword(kw, page_num=1)
    for i, comic in enumerate(res.comics[:3], 1):
        print(f"  {i}. ID={comic.id} | {comic.title[:70]}")
```

## 目標驗證
對相近的 top 1–2 候選，逐筆用 `wnacg info <ID>` 或瀏覽器開
`https://<domain>/photos-index-aid-<ID>.html` 比對標題、標籤、頁數。
明確寫出每筆的判斷理由再決定。

## ID 清單準備
把驗證過的 ID 寫進 `ids.txt`（每行一個；`#` 開頭與非數字行會被忽略）。
若要保留「ID → 期望標題」對照，可另存一份 map 方便事後核對下載結果：
```
353284|[Xぴえろ] 常識改変！ピュアときどきビッチ [DL版]
353285|[ZERRY藤尾] いろつき
```

## 啟動前檢查
- `uv run wnacg config --show` 確認域名、下載目錄、並行數。
- 確認目標磁碟空間足夠（大本可達數百 MB）。
- 空間吃緊或大本多時，把並行降到 `--concurrency 2`。

## 啟動
```bash
uv run wnacg download \
  --list ids.txt --dir /tmp/wnacg_batch --concurrency 2 --comic-interval 300 --no-progress
```
長時間批量可放背景執行；完成後檢查 exit code 與 stderr 的失敗清單。

## 標題吻合容忍度
當核心作品名、社團、漢化組吻合時，可接受站點前綴差異（例如站上顯示 `NCP (big.g)`，需求為 `[big.g]`）。記錄你的判斷。