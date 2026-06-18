"""命令行入口 - 使用 argparse"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .client import WnacgClient
from .config import Config, load_config, save_config
from .downloader import Downloader
from .exporter import export_comic


def eprint(*args, **kwargs):
    """印出错误讯息到 stderr。"""
    print(*args, file=sys.stderr, **kwargs)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wnacg",
        description="WNACG 绅士漫畫下載器 (Python + uv + argparse 版)",
        epilog="示例: wnacg search \"ブルーアーカイブ\" --page 1 ; wnacg download 288694"
    )

    subparsers = parser.add_subparsers(dest="command", required=True, help="子命令")

    # config
    p_config = subparsers.add_parser("config", help="查看/修改配置")
    p_config.add_argument("--show", action="store_true", help="显示当前配置")
    p_config.add_argument("--set-cookie", type=str, help="设置登录 cookie (从浏览器或 login 命令获取)")
    p_config.add_argument("--set-download-dir", type=str, help="设置下載目录")
    p_config.add_argument("--set-export-dir", type=str, help="设置导出目录")
    p_config.add_argument("--set-domain", type=str, help="设置 API 域名 (如 www.wn06.cfd)")
    p_config.add_argument("--set-img-concurrency", type=int, help="图片并发数 (默认8)")
    p_config.add_argument("--set-img-interval", type=int, help="图片下載间隔秒 (默认1)")
    p_config.add_argument("--set-comic-interval", type=int, help="漫畫间下載间隔秒 (默认0，建议设置为300即5分钟以避免封锁)")
    p_config.set_defaults(func=cmd_config)

    # login
    p_login = subparsers.add_parser("login", help="账号密码登录 (获取 cookie)")
    p_login.add_argument("--username", "-u", required=True, help="用户名")
    p_login.add_argument("--password", "-p", required=True, help="密码")
    p_login.set_defaults(func=cmd_login)

    # search
    p_search = subparsers.add_parser("search", help="按关键词搜索漫畫")
    p_search.add_argument("keyword", help="搜索关键词 (支持日文/中文)")
    p_search.add_argument("--page", "-p", type=int, default=1, help="页码 (默认1)")
    p_search.add_argument("--tag", action="store_true", help="按标签搜索 (keyword 作为 tag 名)")
    p_search.set_defaults(func=cmd_search)

    # info
    p_info = subparsers.add_parser("info", help="获取漫畫详细信息 + 图片列表预览")
    p_info.add_argument("comic_id", type=int, help="漫畫 ID (aid)")
    p_info.set_defaults(func=cmd_info)

    # download
    p_dl = subparsers.add_parser("download", help="下載指定漫畫")
    p_dl.add_argument("comic_id", type=int, nargs="?", help="漫畫 ID")
    p_dl.add_argument("--dir", "-d", type=str, help="覆盖下載目录")
    p_dl.add_argument("--force", "-f", action="store_true", help="强制重新下載 (忽略已存在)")
    p_dl.add_argument("--concurrency", "-c", type=int, help="覆盖图片并发数")
    p_dl.add_argument("--comic-interval", type=int, help="覆盖漫畫间下載间隔秒 (批量时建议300)")
    p_dl.add_argument("--retries", type=int, help="覆盖单张图片下載失败重试次数 (默认3)")
    p_dl.add_argument("--no-progress", action="store_true", help="关闭进度条 (适合 log / agent / cron)")
    p_dl.add_argument("--list", "-l", type=str, help="从文件批量下載 ID (每行一个 ID)")
    p_dl.set_defaults(func=cmd_download)

    # shelf (需要登录)
    p_shelf = subparsers.add_parser("shelf", help="列出书架内容 (需先 login)")
    p_shelf.add_argument("shelf_id", type=int, default=0, nargs="?", help="书架ID (默认0?)")
    p_shelf.add_argument("--page", type=int, default=1)
    p_shelf.set_defaults(func=cmd_shelf)

    # export
    p_exp = subparsers.add_parser("export", help="将已下載的漫畫目录导出为 cbz 或 pdf")
    p_exp.add_argument("comic_dir", help="已下載的漫畫目录路径 (包含图片和可选元数据.json)")
    p_exp.add_argument("--format", "-f", choices=["cbz", "pdf"], default="cbz", help="导出格式")
    p_exp.add_argument("--out", "-o", type=str, help="导出目录 (默认使用配置)")
    p_exp.set_defaults(func=cmd_export)

    return parser


def cmd_config(args: argparse.Namespace):
    cfg = load_config()
    if args.show or not any([args.set_cookie, args.set_download_dir, args.set_export_dir, args.set_domain, args.set_img_concurrency, args.set_img_interval, args.set_comic_interval]):
        print("当前配置:")
        print(f"  cookie: {'已设置' if cfg.cookie else '未设置'}")
        print(f"  download_dir: {cfg.download_dir}")
        print(f"  export_dir: {cfg.export_dir}")
        print(f"  api_domain: {cfg.api_domain}")
        print(f"  img_concurrency: {cfg.img_concurrency}")
        print(f"  img_interval: {cfg.img_download_interval_sec}s")
        print(f"  comic_interval: {cfg.comic_download_interval_sec}s (漫畫间间隔)")
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
    if args.set_img_concurrency:
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
        print("配置已更新")


def cmd_login(args: argparse.Namespace):
    client = WnacgClient()
    print(f"正在登录用户: {args.username} ...")
    try:
        cookie = client.login(args.username, args.password)
        print("登录成功！")
        print(f"Cookie (前50字符): {cookie[:50]}...")
        cfg = load_config()
        cfg.cookie = cookie
        client.set_cookie(cookie)
        save_config(cfg)
        print("Cookie 已保存到配置，可用于 shelf 等需要登录的功能。")
    except Exception as e:
        eprint(f"登录失败: {e}")
        sys.exit(1)


def cmd_search(args: argparse.Namespace):
    client = WnacgClient()
    print(f"搜索: {args.keyword} (page={args.page}) ...")
    try:
        if args.tag:
            result = client.search_by_tag(args.keyword, args.page)
        else:
            result = client.search_by_keyword(args.keyword, args.page)
    except Exception as e:
        eprint(f"搜索失败: {e}")
        sys.exit(1)

    print(f"结果: 第 {result.current_page}/{result.total_page} 页，共 {len(result.comics)} 项")
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
        eprint(f"获取漫畫信息失败 (ID={args.comic_id}): {e}")
        sys.exit(1)
    print(f"ID: {comic.id}")
    print(f"标题: {comic.title}")
    print(f"分类: {comic.category}")
    print(f"页数: {comic.image_count}")
    print(f"封面: {comic.cover}")
    print(f"标签: {[t.name for t in comic.tags]}")
    print(f"简介: {comic.intro[:200]}...")
    print(f"\n图片列表 (前5 + 最后):")
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
        # 批量从文件
        ids = []
        with open(args.list, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit():
                    ids.append(int(line))
        print(f"从 {args.list} 读取到 {len(ids)} 个 ID，开始批量下載...")
        failed_ids = []
        for cid in ids:
            try:
                downloader.download_by_id(cid, force=args.force, show_progress=show_progress)
            except Exception as e:
                eprint(f"ID {cid} 下載失败: {e}")
                failed_ids.append(cid)
        if failed_ids:
            eprint(f"批量下載完成，但有 {len(failed_ids)}/{len(ids)} 个失败: {failed_ids}")
            sys.exit(1)
        print(f"批量下載完成: 全部 {len(ids)} 个成功")
        return

    if args.comic_id is None:
        eprint("请提供 comic_id 或使用 --list")
        sys.exit(1)

    try:
        downloader.download_by_id(args.comic_id, force=args.force, show_progress=show_progress)
    except Exception as e:
        eprint(f"下載失败 (ID={args.comic_id}): {e}")
        sys.exit(1)


def cmd_shelf(args: argparse.Namespace):
    cfg = load_config()
    if not cfg.cookie:
        eprint("请先使用 `wnacg login` 或 `wnacg config --set-cookie` 设置 cookie")
        sys.exit(1)
    client = WnacgClient(cfg)
    client.set_cookie(cfg.cookie)
    print(f"获取书架 shelf_id={args.shelf_id} page={args.page} ...")
    comics = client.get_shelf(args.shelf_id, args.page)
    for c in comics:
        print(f"ID:{c.id} {c.title} | {c.additional_info}")


def cmd_export(args: argparse.Namespace):
    comic_dir = Path(args.comic_dir).expanduser().resolve()
    if not comic_dir.is_dir():
        eprint(f"错误: {comic_dir} 不是目录")
        sys.exit(1)
    out = Path(args.out).expanduser().resolve() if args.out else None
    try:
        export_comic(comic_dir, fmt=args.format, export_dir=out)
    except Exception as e:
        eprint(f"导出失败: {e}")
        sys.exit(1)


def main(argv: Optional[list] = None):
    parser = create_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
