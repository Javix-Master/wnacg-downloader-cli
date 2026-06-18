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
- 核心模組（cli/client/config/downloader/exporter）仍為簡體中文字串，與專案繁體定位不一致；如要統一需另開一次大範圍字串改動。
- `recover_deleted_list.py` 的 docstring 與 fallback 路徑仍含舊 missmission/Linux 路徑（屬選用輔助腳本，未在本次範圍內清理）。
- 未能在本機跑真實站點端對端測試（成人內容 + 網路 + venv 限制）；下載重試/429 行為僅經靜態與單元層級驗證。
</content>
