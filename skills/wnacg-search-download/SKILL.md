---
name: wnacg-search-download
description: General-purpose workflow for searching and downloading WNACG manga via the wnacg-downloader-cli tool. Use when a user wants to find a title by keyword/tag, verify the right result, download it reliably (with rate-limit discipline), and optionally export to CBZ/PDF. Covers single titles and batch ID lists. Encodes keyword-crafting, target-verification, and reliability lessons.
category: download
version: "2.0"
---

# WNACG Search & Download Skill

通用的「搜尋 → 判斷目標 → 下載 → 匯出」流程，建立在 `wnacg-downloader-cli` 的 `wnacg` CLI 之上。
適用於單本下載、依關鍵字找新刊、或從 ID 清單批量下載。

## Core Principle
把**需要判斷力的步驟**（挑關鍵字、確認哪個結果才是目標）交給 agent／人，把**確定性步驟**（搜尋、下載、匯出）交給 CLI。不要對著一堆候選結果盲下載。

## 4-Step Workflow

### 1. 取得目標名稱／需求
從使用者得到要找的作品（完整標題、作者／社團、作品名、或標籤）。

### 2. 設計搜尋關鍵字（影響最大的一步）
不要直接整串塞進去，也不要粗暴 `title[:30]`。抽取最具辨識度的元素：
- 社團 / 作者
- 核心作品名（短而獨特）
- 漢化組（若有）

**好**：`chiDOLM@STER シンデレラリトルガールズ 朧&天蓬元帥堂`
**壞**：含所有符號與冗長副標的原始全名

若首次結果不佳，調整一次（加或拿掉漢化組／角色名）再重試。

### 3. 搜尋並挑出目標
```bash
uv run wnacg search "你設計的關鍵字" --page 1
# 標籤搜尋：
uv run wnacg search "標籤名" --tag
```
從輸出（每筆三行：`ID: ... | 標題` / `additional_info` / `cover`）挑候選。
**多個相近結果時務必驗證**，不要盲信第一筆：
```bash
uv run wnacg info <候選ID>          # 比對標題、頁數、標籤
# 或在瀏覽器開 https://<domain>/photos-index-aid-<ID>.html 確認封面/標籤
```
明確說出判斷理由：「ID=XXXX 是目標，因標題吻合 + 標籤含預期社團/角色 + 頁數一致。」

### 4. 下載（必要時匯出）
```bash
# 單本
uv run wnacg download <ID> --dir /tmp/wnacg --concurrency 3

# 批量：把確認過的 ID 寫進 ids.txt（每行一個）
uv run wnacg download --list ids.txt --dir /tmp/wnacg --concurrency 2 --comic-interval 300

# 匯出
uv run wnacg export "/tmp/wnacg/<作品標題>" --format cbz --out /tmp/exports
```
下載成功與否會反映在 exit code（非 0 = 失敗）；錯誤輸出在 stderr。

## Reliability & Rate-Limit Discipline
- **並行與間隔**：一般 `--concurrency 3`；大本（>200–300 頁）或重試時降到 `2`。批量務必加 `--comic-interval 300`（每本間隔 5 分鐘）。
- **429 / IP 被限速**：`download_image` 已內建退避重試（`--retries` 調整，預設 3）。若仍大量失敗，先暫停，稍後以更低並行重試。
- **部分成功**：下載完成訊息會回報 `成功 N/total`；失敗張數列在 stderr。零成功才視為整本失敗（exit 非 0）。部分成功可加 `--force` 重跑補齊。
- **暫存目錄**：下載過程在 `.下载中-<標題>/`，完成才改名；中斷後可安全重跑。

## Agent / Cron Integration
- 加 `--no-progress` 關閉進度條，輸出更乾淨。
- 以 exit code 判斷成敗；stdout 取結果、stderr 取錯誤。
- 取第一筆 ID：`uv run wnacg search "kw" --no-progress | grep -oP '^ID:\s*\K\d+' | head -1`
- 受管 venv 環境若 uv 受 `VIRTUAL_ENV`/`SSL_CERT_FILE` 干擾，指令前加 `env -u VIRTUAL_ENV -u SSL_CERT_FILE`。

## Decision Tree
- 多個搜尋結果？→ `info` 或瀏覽器驗證 top 1–2（標題＋標籤＋頁數），再決定。
- 無結果／不準？→ 重設關鍵字（社團＋核心標題＋漢化組）重試一次。
- 大本（>250P）？→ 從 `--concurrency 2~3` 起步。
- 大量 429 / 下載失敗？→ 降並行、加間隔，稍後重試。
- 批量？→ 先把驗證過的 ID 寫進清單，再 `--list` 下載，最後檢查 exit code 與 stderr 失敗清單。

## References
- 可靠性與限速操作細節：`references/reliability-and-rate-limits.md`
- 批量準備模式：`references/batch-preparation-patterns.md`
- CLI 完整參數：專案 `README.md`
- 從標題清單批量產生建議 ID（選用）：專案根目錄 `recover_deleted_list.py`

## Usage Example (One Title)
1. 使用者：「幫我下載 chiDOLM@STER シンデレラリトルガールズ」
2. 關鍵字：`chiDOLM@STER シンデレラリトルガールズ 朧&天蓬元帥堂`
3. `uv run wnacg search "<關鍵字>"` → top 結果 ID=311300
4. `uv run wnacg info 311300` 確認標題／頁數／標籤吻合
5. `uv run wnacg download 311300 --dir /tmp/wnacg --concurrency 3`
6. （選用）`uv run wnacg export "/tmp/wnacg/<標題>" --format cbz`
</content>
