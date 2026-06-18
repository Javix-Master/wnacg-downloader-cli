# Execution Pitfalls & Fixes — wnacg Hermes-Guided Recovery (2026-06 Batches)

## Recurring Operational Constraints
- **/tmp disk quota**: 4.1G tmpfs fills quickly with 180M+ titles. Partial downloads + failed attempts compound the problem.
  - Fix: Never create final ZIPs in /tmp. Write them directly into `project/recovered/`. After every background, the next turn must post-process + rclone + `rm -rf` all temp folders before starting the next title.
- **Large titles (250P+)**: Even with 300s comic interval, per-image requests frequently hit "IP 被封". One documented case: 65/327 success, 262 failures.
  - Fix: Start such titles at img_concurrency=3 (or 2). Log exact success/failure counts. Re-queue individually if needed.
- **Server 2 direct links (click backup)**: The "備用線路 (Server 2)" href exposed after "下載漫畫" click often returns 403 Forbidden shortly after the click succeeds in the browser session.
  - Fix: Treat as high-risk/unreliable. Use only as a one-off test on a problematic high-page title. Always have Python retry path ready. Do not depend on the direct URL remaining valid.

## Batch Management Lessons
- Batches of 5 are safer than 10 when page counts vary or titles are new to the manifest slice.
- After background completion (notify_on_complete), the immediate follow-up **must**:
  1. ls the download dir and count images per title.
  2. Post-process only the good ones (exact manifest title ZIP) directly to recovered/.
  3. rclone with --transfers=1 if large.
  4. Append detailed log line including method and outcome.
  5. rm -rf the entire temp batch dir + any ".下载中-*" folders.
- When quota is hit mid-batch, the later titles in the list may only have ".下载中-" stubs. Clean aggressively and re-queue only the IDs that actually produced substantial content.

## Logging Standard (Enforced)
Every entry must include:
- Exact manifest title
- aid=XXXX
- Final ZIP filename
- Size
- success / partial (N/M pages) / failed
- source=hermes-skill (Python primary | click/Server2 backup)
- notes= (e.g. "concurrency=3, 262 IP blocks on images 64-327", "Server 2 403 after click")

## When Both Methods Struggle
- Python partial + click 403 on the same high-page title: lower concurrency further, wait longer between attempts, or process as a single-title background with aggressive monitoring. Log the outcome honestly; do not force completion if the site is actively blocking.

## References from Actual Runs
- Batch with IDs 353454/324397/357145/348066/352188: two full successes, one partial (DOLL 327P), two quota-killed.
- DOLL (357145) click attempt produced 403 on the direct link.
- Re-tries with concurrency=3 on the two good IDs succeeded in freeing the workflow.

## 2026-06-17 Session Learnings (Disk-Guided + Tool Discipline)
- **Explicit disk check before every launch is mandatory** (user directive: "檢視現在剩餘硬碟是多少？根據剩餘量適當下載"). Always run `df -h /tmp` (and sometimes root) and report free space in the turn before launching a batch. Adjust batch size/concurrency live.
- **Live concurrency tuning by free space**:
  - /tmp free < ~2.5G after cleaning → default to conc=2 for the batch (even if previous default was 3-4).
  - Aggressive pre-clean: `rm -rf /tmp/wnacg_10batch /tmp/wnacg_nextbatch /tmp/wnacg_recover /tmp/wnacg_hermes_judged ...` (all old batch dirs) before starting new work.
- **Terminal background launches MUST use the tool parameter**: `terminal(..., background=true)`. Using shell `&` inside the command string triggers the error "Foreground command uses '&' backgrounding. Use terminal(background=true)..." and the job does not run as background.
- **Post-process path hygiene (recurring cd trap)**: When the shell is cd'ed into /tmp/wnacg_xxx, relative `mv ... recovered/` or `zip ... recovered/` resolves to the wrong directory and fails with "target 'recovered/': No such file or directory" or "directory not found". 
  - Fix: Perform mv/zip/rclone from the project root, or use absolute paths (`/home/tsengagent/Nextcloud/.../recovered/`). After any `cd /tmp/...`, explicitly `cd /home/tsengagent/Nextcloud/Project/...` before post-process steps.
- **Partial success is normal and must be preserved**: For large titles, 253/332 with 79 fails is still valuable. ZIP what succeeded, log the exact partial count + suspected reason, keep the ZIP. Do not rm the folder until after successful post-process.
- **rclone timeout on large ZIPs is expected**: 100M+ files frequently cause "timeout" or "Errors: 1 (retrying may help)". Use `--transfers=1 --timeout=5m`. Local `recovered/` is the source of truth; rclone is best-effort. Retry rclone in a separate low-risk terminal call if the first one fails.
- **Immediate post-completion protocol (non-negotiable)**: The turn that receives the "Background process ... completed" notification owns:
  1. Inspect (ls + per-folder image count + du).
  2. Post-process good titles to recovered/ with exact titles.
  3. rclone (with safe flags).
  4. Append to log with full details.
  5. rm -rf temp dirs.
  Delaying this step causes quota death on the next title.

Update this file with every new batch that hits a novel failure mode or reinforces a pattern (disk check, background param, path hygiene, partial logging, rclone handling).