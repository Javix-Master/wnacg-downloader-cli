# DEVLOG

## 2026-06-19

### 修改內容（Changes）
- `src/wnacg_downloader/config.py`：新增 `img_max_retries`（預設 3）；移除空的 `__post_init__`。
- `src/wnacg_downloader/client.py`：`download_image` 改為重試＋退避（429 等待 5s×次數，逾時/5xx 等待 1.5s×次數，非 429 的 4xx 直接拋出）；移除死碼 `doc_html`。
- `src/wnacg_downloader/downloader.py`：下載帶入 `img_max_retries`；新增 `show_progress`（tqdm `disable`）；整本零張成功時改為 `raise RuntimeError`（供 exit code 反映）；失敗訊息改輸出至 stderr。
- `src/wnacg_downloader/cli.py`：`download` 新增 `--no-progress`/`--comic-interval`/`--retries`；單本與批量失敗皆以非 0 exit code 結束；錯誤統一經 `eprint` 導向 stderr；移除未用的 `filename_filter` import。
- `recover_deleted_list.py`：修正 `load_deleted_titles` 回傳型別標註為 `tuple[list[str], Path]`。
- `README.md`：重寫為通用搜尋／下載工具定位；修正與程式不符之處（search 實際輸出格式、新參數、exit code 行為）；移除 Linux 絕對路徑與全域 `env -u` 前綴（保留一則受管 venv 說明）。
- `skills/`：將 `wnacg-hermes-guided-recovery` 改名重寫為通用的 `wnacg-search-download`（4 步驟流程 + reliability/batch references，移除 missmission/rclone/recovered/manifest 專屬內容）；更新 `skills/README.md`、`examples/search-and-download.md`、`examples/batch-from-list.md` 為通用版。

### 問題與解法（Problems & Solutions）
- 本機 `uv run` 因專案路徑含中文 + cp950 終端，editable 安裝的 `.pth` 解碼失敗無法啟動。改用系統/venv python 直接驗證；並將 `.pth` 以 Big5 重寫使本機 venv 可啟動（`.venv` 已 gitignore，`uv sync` 會再生）。正式環境在 Linux 不受影響。
- 驗證方式：`py_compile` 全模組通過；以 venv python 直接 import 並 parse 各子命令，確認新參數、簽名、help 正常。

### 待辦事項（TODO）
- 未能在本機跑真實站點端對端測試（成人內容 + 網路 + venv 限制）；下載重試/429 行為僅經靜態與單元層級驗證。

---

### 修改內容（Changes）— 啟動編碼問題正式修法
- `.python-version`：`3.11` → `3.13`。Python 3.11 的 `site.addpackage` 以 `encoding="locale"`（cp950）讀 `.pth` 且無視 UTF-8 模式，遇到含中文的 editable `.pth` 會在直譯器啟動時 `UnicodeDecodeError` 崩潰；3.13 起改以 UTF-8 讀 `.pth`，根本解決。`requires-python` 維持 `>=3.11`（只釘本機開發直譯器）。
- `src/wnacg_downloader/cli.py`：新增 `_force_utf8_output()`，在 `main()` 開頭把 `sys.stdout`/`stderr` `reconfigure(encoding="utf-8")`，修正 Windows cp950 主控台無法輸出日文/中文（如 help 中的 `ブルーアーカイブ` 的長音 `ー`）造成的 `UnicodeEncodeError`。Linux 已是 UTF-8，為 no-op。

### 問題與解法（Problems & Solutions）— 補充
- 取代上一輪「把 `.pth` 以 Big5 重寫」的暫時繞法：該繞法每次 `uv run` 自動 re-sync 會以 UTF-8 覆寫 `.pth` 而再次失效。改釘 3.13 後 editable `.pth` 可正常運作，不再需要手改。
- 兩處修正皆跨平台安全：3.13 於 Linux/Windows 皆可，`reconfigure("utf-8")` 在 Linux 為 no-op，不會反而弄壞 Linux。

### 修改內容（Changes）— 第一輪檢視 flag 的 4 個小問題修正
- `src/wnacg_downloader/cli.py`：① `cmd_login` 移除多餘的 `client.set_cookie()`（client 用完即棄）。④ `cmd_config` 的偵測改為 `any(v is not None ...)`，並對 `--set-img-concurrency < 1` 報錯退出（exit 1）；連帶修正 `--set-img-interval 0` / `--set-comic-interval 0` 過去因 truthiness 被當成「未提供」而靜默忽略的問題，現在可正確設為 0。
- `src/wnacg_downloader/config.py`：② `load_config` 改為以 `fields(Config)` 過濾，只取已知欄位、對未知欄位印警告後忽略，缺少欄位由 dataclass 預設補上；避免設定檔含舊/未知鍵時 `Config(**data)` 丟 TypeError → 靜默回退整份預設值。
- `src/wnacg_downloader/downloader.py`：③ 新增執行緒安全的 `_RateLimiter`，於 `_download_one_image` 真正發起請求前 `acquire()`，移除原本放在主執行緒 `as_completed` 迴圈、對並行下載無效的 sleep。`img_download_interval_sec` 現在能真正逐圖限速（已存在而跳過者不佔時槽；interval=0 不阻塞）。

### 問題與解法（Problems & Solutions）— 補充
- 驗證：全模組 `compileall` 通過；`_RateLimiter` 以 4 worker、interval=0.2s 實測相鄰發起間隔穩定 0.2s，interval=0 不阻塞；`config --set-img-concurrency 0` 正確 exit 1、`--set-img-interval 0` 正確生效；注入未知欄位 + 缺欄位的設定檔可正常載入並印警告。
- 測試插曲：PowerShell `-c` 會吃掉內嵌引號、`Set-Content -Encoding utf8` 會加 BOM 使 `json.loads` 失敗 → 改用 Write 寫無 BOM 的暫存 .py 測試。獨立測試腳本未套用 `_force_utf8_output()`，其 stdout 在 cp950 主控台顯示為亂碼（內容正確），非程式問題。

### 修改內容（Changes）— 限速改為「並行＋限速兼具」
- `src/wnacg_downloader/downloader.py`：`download_comic` 將 `_RateLimiter` 的全域發起間隔由 `interval` 改為 `interval / img_concurrency`。語意改為「每個並行槽每隔 interval 秒發一張」，整體速率 = `並行數 / interval` 張/秒（例：interval=1＋並行3 → 約 3 張/秒）；interval=0 仍為不限速。`_RateLimiter` 維持通用「最小發起間隔」職責，換算移至呼叫端。
- `src/wnacg_downloader/cli.py`：`--set-img-interval` help 改述為「每個並行槽的圖片間隔秒；整體速率=並行數/間隔，設0關閉限速」。
- 驗證：以 interval=1、concurrency=3 跑 9 次 acquire，實測約 3.4 張/秒（張數越多越趨近 3/秒），符合公式。

### 修改內容（Changes）— 同步文件
- `README.md`：① 改寫 Windows 含中文路徑的 `.pth` 說明，反映已用 `.python-version` 釘 3.13 解決（並指出 `PYTHONUTF8=1` 對 3.11/3.12 無效）。② config 範例補上 `--set-img-interval`，新增「圖片下載速率＝並行數/間隔」說明（例：並行3＋間隔1≈3張/秒，間隔0不限速）。③ 注意事項補逐圖速率公式。
- `skills/wnacg-search-download/references/reliability-and-rate-limits.md`：「並行與間隔」新增 `img-interval` 逐圖速率槓桿說明。
- `skills/wnacg-search-download/SKILL.md`：並行與間隔條目補一句圖片層級速率與 `--set-img-interval` 指引。

### 後續追加（簡轉繁 + 移除恢復腳本）
- 簡轉繁：`cli.py`、`client.py`、`config.py`、`downloader.py`、`exporter.py`、`utils.py`、`__init__.py` 全部簡體字串改為繁體；`pyproject.toml` description 一併修正。
  - 連動更名：暫存目錄 `.下载中-` → `.下載中-`、元數據檔 `元数据.json` → `元數據.json`（writer/reader 同步），`.gitignore` 暫存樣式同步為 `.下載中-*`。
  - 站點比對字串 `分類：`/`頁數：` 維持不動（本就為繁體，須與網站 HTML 一致）。
- 移除 `recover_deleted_list.py`（恢復專用腳本），並清掉 README / SKILL / batch-from-list 範例中對它的引用。
- 驗證：全模組 `py_compile` 通過、venv python import 成功、parser 解析新參數正常、暫存目錄名輸出為 `.下載中-X`；全庫 grep 無簡體殘留。
