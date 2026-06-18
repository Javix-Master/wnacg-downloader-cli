"""下载管理器 - 支持多线程图片下载、断点续传(简单存在跳过)、元数据"""

import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from .client import Comic, WnacgClient
from .config import Config, load_config, save_config
from .utils import ensure_dir, filename_filter, is_image_file


def get_temp_dir(download_dir: Path, title: str) -> Path:
    return download_dir / f".下载中-{title}"


def get_final_dir(download_dir: Path, title: str) -> Path:
    return download_dir / title


class Downloader:
    def __init__(self, client: Optional[WnacgClient] = None, config: Optional[Config] = None):
        self.config = config or load_config()
        self.client = client or WnacgClient(self.config)
        ensure_dir(self.config.download_path)
        ensure_dir(self.config.export_path)

    def download_comic(self, comic: Comic, force: bool = False, show_progress: bool = True) -> Path:
        """下载整本漫画，返回最终目录路径。

        若全部图片下载失败 (零成功)，抛出 RuntimeError，便于上层以 exit code 反映失败。
        """
        title = comic.title
        download_dir = self.config.download_path
        final_dir = get_final_dir(download_dir, title)
        temp_dir = get_temp_dir(download_dir, title)

        if final_dir.exists() and not force:
            print(f"[{title}] 已存在，跳过下载 (使用 --force 强制重新下载)")
            return final_dir

        # 清理旧的临时目录
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        ensure_dir(temp_dir)

        # 获取图片列表 (如果 comic 里没有则重新获取)
        if not comic.img_list:
            print(f"[{title}] 正在获取图片列表...")
            comic.img_list = self.client.get_img_list(comic.id)

        # 过滤有效图片
        valid_imgs = [img for img in comic.img_list if not img.url.endswith("shoucang.jpg")]
        total = len(valid_imgs)
        if total == 0:
            print(f"[{title}] 没有有效图片")
            return final_dir

        print(f"[{title}] 开始下载 {total} 张图片 (并发={self.config.img_concurrency})")

        # 保存元数据
        self._save_metadata(temp_dir, comic)

        # 准备任务
        tasks = []
        for idx, img in enumerate(valid_imgs):
            # 决定文件名
            if self.config.use_original_filename:
                # 从 url 取原名
                orig = Path(img.url).stem
                base = orig or f"{idx+1:04d}"
            else:
                base = f"{idx+1:04d}"

            tasks.append((idx, img.url, base, temp_dir))

        # 并发下载
        success_count = 0
        failed = []

        with ThreadPoolExecutor(max_workers=self.config.img_concurrency) as executor:
            future_to_task = {
                executor.submit(self._download_one_image, url, base, temp_dir, idx, total): (idx, url, base)
                for idx, url, base, _ in tasks
            }

            with tqdm(total=total, desc=title[:30], unit="img", disable=not show_progress) as pbar:
                for future in as_completed(future_to_task):
                    idx, url, base = future_to_task[future]
                    try:
                        ok = future.result()
                        if ok:
                            success_count += 1
                        else:
                            failed.append((idx, url))
                    except Exception as e:
                        print(f"  下载图片失败 [{idx+1}]: {e}", file=sys.stderr)
                        failed.append((idx, url))
                    pbar.update(1)

                    # 图片间间隔
                    if self.config.img_download_interval_sec > 0:
                        time.sleep(self.config.img_download_interval_sec)

        print(f"[{title}] 下载完成: 成功 {success_count}/{total}")

        if len(failed) > 0:
            print(f"  失败 {len(failed)} 张: {failed[:3]}...", file=sys.stderr)

        if success_count == 0:
            # 保留临时目录以便检查，并以异常向上层反映失败 (供 exit code 使用)
            raise RuntimeError(f"[{title}] 下载失败，没有成功图片 (临时目录: {temp_dir})")

        # 全部成功则重命名
        if final_dir.exists():
            shutil.rmtree(final_dir, ignore_errors=True)

        shutil.move(str(temp_dir), str(final_dir))
        print(f"[{title}] 已保存到: {final_dir}")

        # 漫画间休息
        if self.config.comic_download_interval_sec > 0:
            print(f"等待 {self.config.comic_download_interval_sec}s 后继续...")
            time.sleep(self.config.comic_download_interval_sec)

        return final_dir

    def _download_one_image(self, url: str, base_name: str, temp_dir: Path, idx: int, total: int) -> bool:
        """下载单张并保存"""
        try:
            # 检查是否已存在 (支持不同扩展)
            for ext in [".jpg", ".png", ".webp", ".gif"]:
                if (temp_dir / f"{base_name}{ext}").exists():
                    return True

            data = self.client.download_image(url, max_retries=self.config.img_max_retries)

            # 猜测扩展 (简单从 content-type 或 url)
            ext = self._guess_ext(data, url)

            save_path = temp_dir / f"{base_name}{ext}"
            save_path.write_bytes(data)
            return True
        except Exception as e:
            print(f"    图片 {idx+1}/{total} 下载失败: {e}", file=sys.stderr)
            return False

    def _guess_ext(self, data: bytes, url: str) -> str:
        # 简单 magic
        if data.startswith(b"\xff\xd8"):
            return ".jpg"
        elif data.startswith(b"\x89PNG"):
            return ".png"
        elif data.startswith(b"RIFF") and b"WEBP" in data[:20]:
            return ".webp"
        elif data.startswith(b"GIF"):
            return ".gif"
        else:
            # fallback from url
            p = Path(url)
            if p.suffix:
                return p.suffix.lower()
            return ".jpg"

    def _save_metadata(self, temp_dir: Path, comic: Comic):
        meta = asdict(comic)
        # 清理一些
        meta.pop("is_downloaded", None)
        meta_path = temp_dir / "元数据.json"
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def download_by_id(self, comic_id: int, force: bool = False, show_progress: bool = True) -> Optional[Path]:
        print(f"正在获取漫画信息 ID={comic_id} ...")
        comic = self.client.get_comic(comic_id)
        print(f"标题: {comic.title}")
        print(f"分类: {comic.category} | 页数: {comic.image_count}")
        return self.download_comic(comic, force=force, show_progress=show_progress)


def main_download_test():
    # quick test entry, not used in cli
    config = load_config()
    client = WnacgClient(config)
    downloader = Downloader(client, config)
    # example small comic
    downloader.download_by_id(288694)
