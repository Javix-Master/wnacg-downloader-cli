#!/usr/bin/env python3
"""
WNACG 漫畫恢復輔助工具 (missmission 專用)

從「漫畫本子誤刪清單.txt」幫助產生下載建議 ID 清單。

用法：
  cd /path/to/wnacg-downloader-python_绅士漫畫下載器
  env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run python recover_deleted_list.py --help

  # 僅產生建議清單（推薦，安全）
  env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run python recover_deleted_list.py \
      --search-top 2 --output /tmp/ids_to_recover.txt

  # 之後用 wnacg CLI 批量下載
  env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download \
      --list /tmp/ids_to_recover.txt --concurrency 3

  # 指定清單位置（在 tools 專案中使用時必用）
  env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run python recover_deleted_list.py \
      --manifest-list /home/tsengagent/Nextcloud/Project/develop_軟體開發/missmission/漫畫本子誤刪清單.txt \
      --search-top 2 --output /tmp/ids.txt

注意：
- 此腳本使用簡單關鍵字截斷，建議配合 Hermes 人工判斷更好關鍵字後再精準搜尋。
- 直接 --download-top 僅限少量測試使用，否則建議只產生清單後人工確認。
- 完整流程請參考專案 README 及 wnacg-hermes-guided-recovery skill。
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# 直接 import 內部模組（uv run 時會正確找到）
from wnacg_downloader.client import WnacgClient
from wnacg_downloader.downloader import Downloader
from wnacg_downloader.config import load_config


def load_deleted_titles(manifest_list: Optional[str] = None) -> list[str]:
    if manifest_list:
        list_file = Path(manifest_list).expanduser().resolve()
    else:
        # 嘗試多個常見位置（相容舊 missmission 結構與獨立使用）
        candidates = [
            Path(__file__).parent.parent / "漫畫本子誤刪清單.txt",
            Path.cwd().parent / "漫畫本子誤刪清單.txt",
            Path("/home/tsengagent/Nextcloud/Project/develop_軟體開發/missmission/漫畫本子誤刪清單.txt"),
            Path(__file__).parent / "漫畫本子誤刪清單.txt",
            Path.cwd() / "漫畫本子誤刪清單.txt",
        ]
        list_file = None
        for c in candidates:
            if c.exists():
                list_file = c
                break
        if not list_file:
            print("錯誤：找不到誤刪清單檔案。")
            print("請使用 --manifest-list 明確指定完整路徑，例如：")
            print("  --manifest-list /home/tsengagent/Nextcloud/Project/develop_軟體開發/missmission/漫畫本子誤刪清單.txt")
            sys.exit(1)

    if not list_file.exists():
        print(f"錯誤：找不到清單檔案 {list_file}")
        sys.exit(1)

    titles = []
    with open(list_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # 移除可能的 zip 副檔名與多餘空白
                title = line.replace(".zip", "").strip()
                titles.append(title)

    print(f"從 {list_file} 讀取到 {len(titles)} 個標題")
    return titles, list_file


def search_for_title(client: WnacgClient, title: str, top_n: int = 3):
    """對單一標題做搜尋，返回前 top_n 個結果"""
    try:
        # 用標題關鍵字搜尋（取前幾個字避免太長；實際使用建議搭配 Hermes 人工精煉關鍵字）
        keyword = title[:40].strip()
        result = client.search_by_keyword(keyword, page_num=1)
        return result.comics[:top_n]
    except Exception as e:
        print(f"  搜尋失敗：{title[:40]}... → {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="從誤刪清單幫助恢復 wnacg 本子（產生 ID 清單給 wnacg download --list 使用）"
    )
    parser.add_argument(
        "--manifest-list", "--list-file", dest="manifest_list", type=str, default=None,
        help="誤刪清單檔案完整路徑（建議明確指定，尤其在獨立 tools 專案目錄執行時）"
    )
    parser.add_argument("--search-top", type=int, default=2, help="每個標題搜尋顯示前 N 個結果（預設2）")
    parser.add_argument("--output", type=str, default="ids_to_download.txt", help="輸出建議 ID 清單檔名")
    parser.add_argument(
        "--download-top", type=int, default=0,
        help="直接下載每個標題的前 N 個結果（0=只產生清單，不下載。小心使用！）"
    )
    parser.add_argument("--concurrency", type=int, default=3, help="下載時的圖片併發數（大本建議 2-3）")
    parser.add_argument("--force", action="store_true", help="下載時強制覆蓋已存在檔案")
    args = parser.parse_args()

    titles, list_file = load_deleted_titles(args.manifest_list)

    client = WnacgClient()
    downloader = None
    if args.download_top > 0:
        cfg = load_config()
        cfg.img_concurrency = args.concurrency
        downloader = Downloader(client, cfg)

    collected_ids = []
    for i, title in enumerate(titles, 1):
        print(f"\n[{i}/{len(titles)}] 處理：{title[:60]}...")
        matches = search_for_title(client, title, top_n=args.search_top)

        if not matches:
            print("  無結果")
            continue

        for rank, comic in enumerate(matches, 1):
            print(f"  建議 {rank}: ID={comic.id} | {comic.title[:50]} | {comic.additional_info}")
            if rank == 1:
                collected_ids.append(comic.id)

        if args.download_top > 0 and matches:
            for comic in matches[:args.download_top]:
                print(f"  >>> 正在下載 ID={comic.id} ...")
                try:
                    downloader.download_comic(comic, force=args.force)  # type: ignore
                except Exception as e:
                    print(f"  下載失敗 ID={comic.id}: {e}")

    # 輸出 ID 清單（去重）
    unique_ids = sorted(set(collected_ids))
    if args.output:
        out_path = Path(args.output)
        out_path.write_text("\n".join(map(str, unique_ids)), encoding="utf-8")
        print(f"\n已輸出 {len(unique_ids)} 個建議 ID 到 {out_path}")
        print("之後可執行：")
        print(f"  env -u VIRTUAL_ENV -u SSL_CERT_FILE uv run wnacg download --list {out_path} --concurrency {args.concurrency}")

    print("\n完成。建議先手動檢查建議 ID（搭配 browser 驗證），再決定是否大量下載。")
    print("進階：使用 wnacg-hermes-guided-recovery skill 進行更精準的人工關鍵字判斷。")


if __name__ == "__main__":
    main()
