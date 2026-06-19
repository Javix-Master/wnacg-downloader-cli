"""命令列入口 - 使用 argparse"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .client import WnacgClient
from .config import Config, load_config, save_config
from .downloader import Downloader
from .exporter import export_comic


def eprint(*args, **kwargs):
    """印出錯誤訊息到 stderr。"""
    print(*args, file=sys.stderr, **kwargs)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wnacg",
        description="WNACG 紳士漫畫下載器 (Python + uv + argparse 版)",
        epilog="範例: wnacg search \"ブルーアーカイブ\" --page 1 ; wnacg download 288694"
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="子命令")

    # config
    p_config = subparsers.add_parser("config", help="查看/修改設定")
    p_config.add_argument("--show", action="store_true", help="顯示目前設定")
    p_config.add_argument("--set-cookie", type=str, help="設定登入 cookie (從瀏覽器或 login 命令取得)")
    p_config.add_argument("--set-download-dir", type=str, help="設定下載目錄")
    p_config.add_argument("--set-export-dir", type=str, help="設定匯出目錄")
    p_config.add_argument("--set-domain", type=str, help="設定 API 域名 (如 www.wn06.cfd)")
    p_config.add_argument("--set-img-concurrency", type=int, help="圖片並行數 (預設8)")
    p_config.add_argument("--set-img-interval", type=int, help="每個並行槽的圖片間隔秒 (預設1)；整體速率=並行數/間隔，設0關閉限速")
    p_config.add_argument("--set-comic-interval", type=int, help="漫畫間下載間隔秒 (預設0，建議設為300即5分鐘以避免封鎖)")
    p_config.set_defaults(func=cmd_config)

    # login
    p_login = subparsers.add_parser("login", help="帳號密碼登入 (取得 cookie)")
    p_login.add_argument("--username", "-u", required=True, help="使用者名稱")
    p_login.add_argument("--password", "-p", required=True, help="密碼")
    p_login.set_defaults(func=cmd_login)

    # search
    p_search = subparsers.add_parser("search", help="按關鍵字搜尋漫畫")
    p_search.add_argument("keyword", help="搜尋關鍵字 (支援日文/中文)")
    p_search.add_argument("--page", "-p", type=int, default=1, help="頁碼 (預設1)")
    p_search.add_argument("--tag", action="store_true", help="按標籤搜尋 (keyword 作為 tag 名)")
    p_search.set_defaults(func=cmd_search)

    # info
    p_info = subparsers.add_parser("info", help="取得漫畫詳細資訊 + 圖片清單預覽")
    p_info.add_argument("comic_id", type=int, help="漫畫 ID (aid)")
    p_info.set_defaults(func=cmd_info)

    # download
    p_dl = subparsers.add_parser("download", help="下載指定漫畫")
    p_dl.add_argument("comic_id", type=int, nargs="?", help="漫畫 ID")
    p_dl.add_argument("--dir", "-d", type=str, help="覆寫下載目錄")
    p_dl.add_argument("--force", "-f", action="store_true", help="強制重新下載 (忽略已存在)")
    p_dl.add_argument("--concurrency", "-c", type=int, help="覆寫圖片並行數")
    p_dl.add_argument("--comic-interval", type=int, help="覆寫漫畫間下載間隔秒 (批量時建議300)")
    p_dl.add_argument("--retries", type=int, help="覆寫單張圖片下載失敗重試次數 (預設3)")
    p_dl.add_argument("--no-progress", action="store_true", help="關閉進度條 (適合 log / agent / cron)")
    p_dl.add_argument("--list", "-l", type=str, help="從檔案批量下載 ID (每行一個 ID)")
    p_dl.set_defaults(func=cmd_download)

    # shelf (需要登入)
    p_shelf = subparsers.add_parser("shelf", help="列出書架內容 (需先 login)")
    p_shelf.add_argument("shelf_id", type=int, default=0, nargs="?", help="書架ID (預設0?)")
    p_shelf.add_argument("--page", type=int, default=1)
    p_shelf.set_defaults(func=cmd_shelf)

    # export
    p_exp = subparsers.add_parser("export", help="將已下載的漫畫目錄匯出為 cbz 或 pdf")
    p_exp.add_argument("comic_dir", help="已下載的漫畫目錄路徑 (包含圖片和可選元數據.json)")
    p_exp.add_argument("--format", "-f", choices=["cbz", "pdf"], default="cbz", help="匯出格式")
    p_exp.add_argument("--out", "-o", type=str, help="匯出目錄 (預設使用設定)")
    p_exp.set_defaults(func=cmd_export)

    return parser


def cmd_config(args: argparse.Namespace):
    cfg = load_config()
    setters = [args.set_cookie, args.set_download_dir, args.set_export_dir, args.set_domain,
               args.set_img_concurrency, args.set_img_interval, args.set_comic_interval]
    if args.show or not any(v is not None for v in setters):
        print("目前設定:")
        print(f"  cookie: {'已設定' if cfg.cookie else '未設定'}")
        print(f"  download_dir: {cfg.download_dir}")
        print(f"  export_dir: {cfg.export_dir}")
        print(f"  api_domain: {cfg.api_domain}")
        print(f"  img_concurrency: {cfg.img_concurrency}")
        print(f"  img_interval: {cfg.img_download_interval_sec}s")
        print(f"  comic_interval: {cfg.comic_download_interval_sec}s (漫畫間間隔)")
        return

    changed = False
    if args.set_cookie:
        cfg.cookie = args.set_cookie
        changed = True
    if args.set_download_dir:
        cfg.download_dir = args.set_download_dir
        changed = True
    if args.set_export_dir:
        cfg.export_dir = args.set_export_dir
        changed = True
    if args.set_domain:
        cfg.api_domain = args.set_domain
        changed = True
    if args.set_img_concurrency is not None:
        if args.set_img_concurrency < 1:
            eprint("錯誤: img_concurrency 必須 >= 1")
            sys.exit(1)
        cfg.img_concurrency = args.set_img_concurrency
        changed = True
    if args.set_img_interval is not None:
        cfg.img_download_interval_sec = args.set_img_interval
        changed = True
    if args.set_comic_interval is not None:
        cfg.comic_download_interval_sec = args.set_comic_interval
        changed = True

    if changed:
        save_config(cfg)
        print("設定已更新")


def cmd_login(args: argparse.Namespace):
    client = WnacgClient()
    print(f"正在登入使用者: {args.username} ...")
    try:
        cookie = client.login(args.username, args.password)
        print("登入成功！")
        print(f"Cookie (前50字元): {cookie[:50]}...")
        cfg = load_config()
        cfg.cookie = cookie
        save_config(cfg)
        print("Cookie 已儲存到設定，可用於 shelf 等需要登入的功能。")
    except Exception as e:
        eprint(f"登入失敗: {e}")
        sys.exit(1)


def cmd_search(args: argparse.Namespace):
    client = WnacgClient()
    print(f"搜尋: {args.keyword} (page={args.page}) ...")
    try:
        if args.tag:
            result = client.search_by_tag(args.keyword, args.page)
        else:
            result = client.search_by_keyword(args.keyword, args.page)
    except Exception as e:
        eprint(f"搜尋失敗: {e}")
        sys.exit(1)

    print(f"結果: 第 {result.current_page}/{result.total_page} 頁，共 {len(result.comics)} 項")
    print("-" * 80)
    for c in result.comics:
        print(f"ID: {c.id:7d} | {c.title[:50]}")
        print(f"     {c.additional_info}")
        print(f"     cover: {c.cover[:60]}...")
        print()


def cmd_info(args: argparse.Namespace):
    client = WnacgClient()
    try:
        comic = client.get_comic(args.comic_id)
    except Exception as e:
        eprint(f"取得漫畫資訊失敗 (ID={args.comic_id}): {e}")
        sys.exit(1)
    print(f"ID: {comic.id}")
    print(f"標題: {comic.title}")
    print(f"分類: {comic.category}")
    print(f"頁數: {comic.image_count}")
    print(f"封面: {comic.cover}")
    print(f"標籤: {[t.name for t in comic.tags]}")
    print(f"簡介: {comic.intro[:200]}...")
    print(f"\n圖片清單 (前5 + 最後):")
    for i, img in enumerate(comic.img_list[:5]):
        print(f"  [{img.caption}] {img.url[:70]}")
    if len(comic.img_list) > 5:
        print("  ...")
        last = comic.img_list[-1]
        print(f"  [{last.caption}] {last.url[:70]}")


def cmd_download(args: argparse.Namespace):
    cfg = load_config()
    if args.dir:
        cfg.download_dir = args.dir
    if args.concurrency:
        cfg.img_concurrency = args.concurrency
    if args.comic_interval is not None:
        cfg.comic_download_interval_sec = args.comic_interval
    if args.retries is not None:
        cfg.img_max_retries = args.retries

    show_progress = not args.no_progress
    client = WnacgClient(cfg)
    downloader = Downloader(client, cfg)

    if args.list:
        # 從檔案批量
        ids = []
        with open(args.list, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    ids.append(int(line))
        print(f"從 {args.list} 讀取到 {len(ids)} 個 ID，開始批量下載...")
        failed_ids = []
        for cid in ids:
            try:
                downloader.download_by_id(cid, force=args.force, show_progress=show_progress)
            except Exception as e:
                eprint(f"ID {cid} 下載失敗: {e}")
                failed_ids.append(cid)
        if failed_ids:
            eprint(f"批量下載完成，但有 {len(failed_ids)}/{len(ids)} 個失敗: {failed_ids}")
            sys.exit(1)
        print(f"批量下載完成: 全部 {len(ids)} 個成功")
        return

    if args.comic_id is None:
        eprint("請提供 comic_id 或使用 --list")
        sys.exit(1)

    try:
        downloader.download_by_id(args.comic_id, force=args.force, show_progress=show_progress)
    except Exception as e:
        eprint(f"下載失敗 (ID={args.comic_id}): {e}")
        sys.exit(1)


def cmd_shelf(args: argparse.Namespace):
    cfg = load_config()
    if not cfg.cookie:
        eprint("請先使用 `wnacg login` 或 `wnacg config --set-cookie` 設定 cookie")
        sys.exit(1)
    client = WnacgClient(cfg)
    client.set_cookie(cfg.cookie)
    print(f"取得書架 shelf_id={args.shelf_id} page={args.page} ...")
    comics = client.get_shelf(args.shelf_id, args.page)
    for c in comics:
        print(f"ID:{c.id} {c.title} | {c.additional_info}")


def cmd_export(args: argparse.Namespace):
    comic_dir = Path(args.comic_dir).expanduser().resolve()
    if not comic_dir.is_dir():
        eprint(f"錯誤: {comic_dir} 不是目錄")
        sys.exit(1)
    out = Path(args.out).expanduser().resolve() if args.out else None
    try:
        export_comic(comic_dir, fmt=args.format, export_dir=out)
    except Exception as e:
        eprint(f"匯出失敗: {e}")
        sys.exit(1)


def _force_utf8_output() -> None:
    """確保 stdout/stderr 以 UTF-8 輸出。

    Windows 主控台預設使用地區編碼 (如繁中環境的 cp950)，無法輸出
    日文/中文漫畫標題與訊息，會丟 UnicodeEncodeError。這裡統一切到
    UTF-8；Linux/macOS 本來就是 UTF-8，reconfigure 為 no-op，不影響行為。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue  # 例如輸出被包成不支援 reconfigure 的物件
        try:
            reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass


def main(argv: Optional[list] = None):
    _force_utf8_output()
    parser = create_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
