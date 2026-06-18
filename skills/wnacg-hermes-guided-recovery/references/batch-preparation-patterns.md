# Batch Preparation & Verification Patterns — wnacg Hermes-Guided Recovery

This file captures reusable techniques for handling 5–10 title recovery batches efficiently (observed 2026-06 sessions).

## Slice Selection (Progress Tracking)
- Grep the manifest for a recently recovered title to find its line number:
  ```bash
  grep -n "DASHIMAKITAMAGO" 漫畫本子誤刪清單.txt
  grep -n "The Dungeon In Yarn" 漫畫本子誤刪清單.txt
  ```
- Then pull the next slice:
  ```bash
  sed -n '90,110p' 漫畫本子誤刪清單.txt
  ```
- Cross-check against recovered titles:
  ```bash
  ls recovered/*.zip | sed 's|.*/||;s/\.zip$//'
  ```

## Efficient Multi-Title Search
Run several keywords in a **single** python invocation (avoids repeated uv/python startup):
```python
from wnacg_downloader.client import WnacgClient
client = WnacgClient()

candidates = [
    ("Xぴえろ 常識改変 ピュアときどきビッチ Sakura", "[Xぴえろ] ..."),
    ("ZERRY藤尾 いろつき Sakura", "..."),
    # ... up to 10
]
for kw, orig in candidates:
    print(f"\n=== Searching: {kw} ===")
    res = client.search_by_keyword(kw, page_num=1)
    for i, comic in enumerate(res.comics[:3], 1):
        print(f"  {i}. ID={comic.id} | {comic.title[:70]}")
```

## Parallel Browser Verification
Issue several navigates together:
```bash
# In one turn
browser_navigate for ID 353284
browser_navigate for ID 353285
...
```
Follow with snapshots on the best candidates. State decision explicitly for each.

## ID-to-Manifest-Title Map (Essential)
Before launching download, create `/tmp/batch_map.txt`:
```
353284|[Xぴえろ] 常識改変！ピュアときどきビッチ [DL版] [Sakura机翻汉化]
353285|[ZERRY藤尾] いろつき [Sakura机翻汉化]
...
```
This map is the source of truth for the final ZIP filename during post-process.

## Pre-Launch Checklist
- `df -h /tmp` (and root)
- `cd .../wnacg-downloader-python && env -u ... uv run wnacg config --show`
- Write ids.txt and map.txt
- Use conc=2 when /tmp free < 2.7G

## Launch
```bash
env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download \
  --list /tmp/next10_ids.txt --dir /tmp/wnacg_next10 --concurrency 2
```
With tool: `terminal(..., background=true, notify_on_complete=true)`

## Title Matching Tolerance
Accept near-matches when the distinctive core title, circle, and 漢化組 match even if site prefixes differ (e.g. "NCP (big.g)" vs manifest "[big.g]").

See main SKILL.md for integration into the 5-step pipeline.
```

Now patch the SKILL.md to reference the new file (using a correct call with old_string). 

Use a string from the section I added earlier.