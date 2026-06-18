---
name: wnacg-hermes-guided-recovery
description: Hermes-guided wnacg manga recovery workflow from manifest. Strict 5-step pipeline (manifest title, Hermes search keyword judgment, Python client search, Hermes + browser target judgment, Python download). Python direct-image is primary; site button/Server-2 ZIP is backup for high-page-count titles. Full post-process to exact manifest-title ZIP, rclone to recovered/, logging. Encodes lessons from side-by-side quality comparison.
category: recovery
version: "1.0"
---

# wnacg Hermes-Guided Recovery Skill

## Core Principle
Recover titles from the manifest using a **strict, repeatable 5-step pipeline** that combines human/AI judgment (Hermes) where it adds value with deterministic Python code for search and download.

**User-specified pipeline (must follow exactly):**
1. 獲取漫畫名稱
2. Hermes 判斷應該使用的搜尋標題
3. 使用python code進行搜尋獲得搜尋結果
4. Hermes 判斷那個是目標
5. 使用python code進行下載

**Primary download**: Python direct per-image download (WnacgClient + Downloader) with strict rate limits.
**Backup**: Site "下載漫畫" button / Server 2 direct ZIP (only for titles with many images where you want to test if site packaging avoids per-image security triggers).

Empirical finding (see comparison report): Quality is identical when both succeed. Python wins on reliability, control, and post-processing consistency.

## Prerequisites
- **CLI 工具主目錄**（正式位置）: /home/tsengagent/Nextcloud/Project/tools_工具開發/wnacg-downloader-python_绅士漫畫下載器
- **missmission 工作資料**（清單 + recovered/）: /home/tsengagent/Nextcloud/Project/develop_軟體開發/missmission/
- 執行時 **cd** 到工具主目錄，或使用 `env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run --project /path/to/tools-dir ...`
- Always run Python with: `env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run python ...` (or the wnacg CLI wrapper).
- Manifest: 使用 `--manifest-list` 指向 `/home/tsengagent/Nextcloud/Project/develop_軟體開發/missmission/漫畫本子誤刪清單.txt`
- Config defaults: comic_interval=300s, img_concurrency=4-5, img_interval=2s.
- Available tools: browser_navigate/snapshot/console (for verification), terminal (Python client calls + post-process), rclone (nextcloud remote).
- Key artifacts:
  - recovered/site_button_vs_python_comparison.md (Python primary recommendation)
  - recovered/recovered.log (append only)
  - recovered/*.zip (full manifest titles only)

## Detailed 5-Step Pipeline

### 1. 獲取漫畫名稱
Read the next title (or batch) from the manifest or an approved ID list (/tmp/*.txt).

Example:
`(C102) [朧&天蓬元帥堂 (天蓬元帥)] THE chiDOLM@STER シンデレラリトルガールズ ~新メンバー初体験SPECIAL~ ... [黒緋鞠汉化]`

### 2. Hermes 判斷搜尋標題 (Highest Impact Step)
Do **not** use crude `title[:30]`.

Craft a high-recall keyword by extracting only the most distinctive elements:
- Circle / author group
- Core work title (short but unique)
- 漢化組 if present

**Good**:
`chiDOLM@STER シンデレラリトルガールズ 朧&天蓬元帥堂 黒緋鞠汉化`

**Bad** (too long/noisy):
Full raw title with all symbols and long subtitles.

If first search returns poor results, refine once (add or drop the 漢化組 or a character name) and retry.

### 3. 使用 Python code 進行搜尋
```python
from wnacg_downloader.client import WnacgClient
client = WnacgClient()
keyword = "HERMES_CHOSEN_KEYWORD_HERE"
result = client.search_by_keyword(keyword, page_num=1)
for i, comic in enumerate(result.comics[:3], 1):
    print(f"{i}. ID={comic.id} | {comic.title} | {comic.additional_info}")
```
Return the top results (with IDs and titles) for Hermes judgment in step 4.

### 4. Hermes 判斷那個是目標 (Always Use Browser Verification)
For the top 1-2 candidates:
- `browser_navigate https://www.wn06.cfd/photos-index-aid-{ID}.html`
- `browser_snapshot` (full if needed for tags)
- Check:
  - Title matches the manifest (exact or extremely close)
  - Tags include the expected circle, 漢化組, characters
  - Page count is consistent
- State your decision explicitly: "ID=XXXX is the target because [title match + tag overlap + page count]. The other result is a different variant."

If uncertain, browse both and pick the stronger match. Never auto-trust rank-1 without verification.

### 5. 使用 Python code 進行下載 (Primary Path)
```python
from wnacg_downloader.client import WnacgClient
from wnacg_downloader.downloader import Downloader
from wnacg_downloader.config import load_config

client = WnacgClient()
cfg = load_config()
cfg.img_concurrency = 4
cfg.comic_interval = 300

downloader = Downloader(client, cfg)
# Prefer a real Comic object from the search result when available
comic = ...   # e.g. from step 3 or minimal dataclass with .id and .title
path = downloader.download_comic(comic, force=False)
print(f"Downloaded to: {path}")
```
Run in foreground for small titles or background (with notify_on_complete) for larger ones.

**Click / Site-Button Backup Path (Use Judiciously)**
Only consider for titles with very high image counts where you suspect per-image requests may trigger security.

Steps:
1. browser_navigate to the main aid page.
2. Locate and note the "下載漫畫" element (commonly ref e23/e25/e22).
3. Navigate/click to reach the /download-index-aid-ID.html page.
4. Use browser_console or snapshot to extract the Server 2 direct link (dl1.wn01.download/... .zip?n=...).
5. Download the ZIP with terminal curl or Python urllib (quote the URL carefully).
6. Treat the resulting ZIP exactly like a Python download for post-processing.

Known limitations (from comparison):
- Frequent 403 on direct links (time-sensitive).
- No rate-limit control.
- Raw internal filenames (not normalized).
- Quality is the same as Python when successful.

## Post-Processing (Non-Negotiable)
After any download (Python or site, full or partial):
- Produce **only** a ZIP whose filename is the **exact original manifest title** (never loose JPGs or subfolders).
- Write the ZIP directly into the project `recovered/` directory (or other main-FS location) — **never** rely on /tmp for final ZIPs. /tmp disk quota is a recurring constraint on large titles.
- `rclone copy "exact-title.zip" nextcloud:Project/develop_軟體開發/missmission/recovered/ --progress --transfers=1`
- Append one structured line to `recovered/recovered.log/recovered.log`:
  `2026-06-17Txx:xx:xx | exact manifest title | aid=XXXXXX | exact-title.zip | XXM | success/partial (N/M pages) | source=hermes-skill (Python primary | click/Server2 backup) | notes=...`
- Immediately clean incomplete ".下载中-*" folders and any failed temp dirs after post-processing to free space for the next title.

## Configuration & Safety (Runtime Tuned)
- Default: comic_interval=300s, img_concurrency=4, img_interval=2s.
- For large titles (>200-300 pages), first-time risky titles, or retries: lower to img_concurrency=3 (or 2) immediately.
- Always prefix Python/CLI runs with `env -u VIRTUAL_ENV -u SSL_CERT_FILE`.
- Use background + notify_on_complete for batches. The very next turn after completion **must** inspect the download dir, post-process good titles to recovered/, rclone, log, and clean.
- Small batches (5 titles max) when page counts are high or space is tight.

## Decision Tree for Hermes (Updated with 2026 Execution Lessons)
- Multiple search results? → Always browser verify top 2 (title + tags + page count).
- No results or poor matches? → Refine keyword (circle + core title + 漢化組) and retry once.
- High page count title (>250-300P)? → Start with Python at concurrency=3. Have click/Server 2 as explicit backup test, but expect frequent 403s on direct links even after successful "下載漫畫" click.
- 403 on site direct link or heavy IP blocks? → Fall back to Python (or pause and retry later with lower concurrency). Do not trust direct links as reliable.
- Partial success (e.g. 65/327)? → Log exact counts and failure reasons. Re-queue only the ID with lowered concurrency or treat as candidate for click backup. Do not treat partial as complete.
- Disk quota hit on /tmp? → Immediately post-process whatever succeeded to project/recovered/, rclone, clean all temp folders aggressively, then re-queue only the good IDs.
- Quality check: sizes match + image count within ~1-2 → treat as equivalent. Record the exact method used in the log.

## Runtime Execution Lessons (June 2026 Batches)
- /tmp quota is the #1 operational blocker on batches containing 200P+ titles. Always route final ZIPs to main filesystem (project recovered/).
- Even with 300s interval and low concurrency, large titles can produce many per-image failures ("IP 被封"). Lower concurrency further on retries.
- Server 2 direct links (the "備用線路" exposed after clicking 下載漫畫) frequently 403 even when the button flow succeeds in the browser. Document as unreliable backup.
- After background completion, the immediate follow-up turn owns post-process + clean. Delaying this leads to quota death on the next title.
- Prefer 5-title batches for the first pass on a new slice of the manifest. Re-queue problem titles individually.

## Batch Preparation & Verification Efficiency Patterns (2026-06)
For 8–10 title slices (common when user requests "補下載10個"):

- **Progress location**: `grep -n "last_recovered_keyword" 漫畫本子誤刪清單.txt` (e.g. after "The Dungeon In Yarn" at line 86 or DASHIMAKITAMAGO at 32). Then `sed -n '90,110p'` (or similar) to pull the next clean slice. Cross-reference against `ls recovered/*.zip | sed 's|.*/||;s/\.zip$//'` and the log.

- **Batch search (efficient)**: Put 8–10 (keyword, original_title) pairs in one `python -c`:
  ```python
  candidates = [ ("keyword1", "full manifest title1"), ... ]
  for kw, orig in candidates:
      res = client.search_by_keyword(kw, page_num=1)
      ... print top results
  ```
  This avoids repeated process startup cost.

- **Parallel verification**: Issue multiple `browser_navigate` (and later snapshots) in a single turn for the strongest candidates from search. Verify title exactness + tags + page count on each.

- **ID → exact title map (mandatory for reliable post-process)**: Before any download launch, write `/tmp/batch_map.txt`:
  ```
  353284|[Xぴえろ] 常識改変！ピュアときどきビッチ [DL版] [Sakura机翻汉化]
  353285|[ZERRY藤尾] いろつき [Sakura机翻汉化]
  ...
  ```
  Use this during post-process to produce the canonical ZIP name regardless of how the downloader folder was named.

- **Pre-launch config & disk check**: Run `wnacg config --show` and `df -h /tmp` immediately before the batch. Force conc=2 when free space < ~2.7G.

- **Launch command** (using CLI wrapper):
  ```bash
  env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download \
    --list /tmp/ids.txt --dir /tmp/wnacg_next10 --concurrency 2
  ```
  With `terminal(..., background=true, notify_on_complete=true)`.

- **Title variation tolerance**: During browser judgment, accept close matches when the core work title + 漢化組 + tags align (e.g. site shows "NCP (big.g)" but manifest is "[big.g]"). Document the decision.

Add these map and slice-selection steps to every multi-title run. See references/batch-preparation-and-verification-patterns.md for concrete command examples from the 2026-06-18 run.

**Disk & Tool Discipline (2026-06-17 session patterns)**:
- Always run `df -h /tmp` (and root) and report free space *before* launching any download batch. Tune batch size and concurrency live (e.g. conc=2 when free <2.5G).
- Terminal backgrounds: **must** use `terminal(..., background=true)`. Shell `&` inside the command string is rejected.
- Post-process from project root or with absolute paths. Relative "recovered/" fails when cwd is inside a /tmp/wnacg_* dir.
- Partial downloads: ZIP + log what succeeded (e.g. "partial (253/332, 79 fails, likely rate limit)"); do not discard.
- rclone large ZIPs: expect timeouts; use `--transfers=1 --timeout=5m`; local recovered/ is the source of truth.
- Immediate post-completion: on "completed" notification, the next actions are inspect → post-process → rclone → log → clean temps (non-negotiable).

## References & Artifacts
- Comparison report: `recovered/site_button_vs_python_comparison.md`
- This skill's own execution log from 2026-06 batches (see references/ for detailed pitfall examples)
- Manifest: `../漫畫本子誤刪清單.txt`
- Project: wnacg-downloader-python (client.py / downloader.py) 位於 tools_工具開發/wnacg-downloader-python_绅士漫畫下載器/
- Recovered: `recovered/` (ZIPs + recovered.log/recovered.log)

## Usage Example (One Title)
1. Title from manifest.
2. Hermes keyword: \"chiDOLM@STER シンデレラリトルガールズ 朧&天蓬元帥堂 黒緋鞠汉化\"
3. Python search → ID 311300 top.
4. browser_navigate + snapshot → exact title match + tags.
5. Python download (concurrency=3 if large).
6. Post-process **directly to recovered/** with exact title → rclone → append log with full source/method note.

## How to Use This Skill
Before starting any recovery batch:
- Load with skill_view(name='wnacg-hermes-guided-recovery')
- Follow the 5 steps literally.
- Record every Hermes keyword decision and browser verification.
- After every background completion: inspect → post-process to recovered/ immediately → clean temps.

This skill encodes the lessons from multiple 2026-06 recovery sessions, including the explicit user directive that Python is primary and click is high-page backup only.

## References & Artifacts
- Comparison report: `recovered/site_button_vs_python_comparison.md` (Python preferred, sizes identical, naming normalized in Python flow).
- Manifest: `../漫畫本子誤刪清單.txt`
- Project client/downloader: `src/wnacg_downloader/`
- Recovered log & ZIPs: `recovered/`
- Old (crude) script for reference only: `recover_deleted_list.py` (truncate + top-1 — do not use as primary).

## Usage Example (One Title)
1. Title from manifest.
2. Hermes keyword: "chiDOLM@STER シンデレラリトルガールズ 朧&天蓬元帥堂 黒緋鞠汉化"
3. Python search → ID 311300 top.
4. browser_navigate + snapshot → exact title match + tags.
5. Python download.
6. Post-process to full-title ZIP → rclone → log.

## How to Use This Skill
Before starting any recovery batch:
- Load with skill_view(name='wnacg-hermes-guided-recovery')
- Follow the 5 steps literally.
- Record every Hermes keyword decision and browser verification.

This skill encodes the lessons from multiple 2026-06 recovery sessions that achieved high accuracy on previously difficult ("無結果") titles.

---
End of skill. Update when new data or heuristics are available.
