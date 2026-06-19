"""下載管理器 - 支援多執行緒圖片下載、斷點續傳(簡單存在跳過)、元數據"""

import json
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from tqdm import tqdm

from .client import Comic, WnacgClient
from .config import Config, load_config, save_config
from .utils import ensure_dir, filename_filter, is_image_file


class _RateLimiter:
    """跨執行緒限制請求發起速率：相鄰兩次 acquire() 之間至少間隔 interval 秒。

    用鎖串行化「發起」時點（下載本身仍並行），達成全域限速以降低被封鎖
    風險。實際間隔由呼叫端依並行數換算（見 download_comic）。
    """

    def __init__(self, interval: float):
        self.interval = interval
        self._lock = threading.Lock()
        self._next_time = 0.0

    def acquire(self) -> None:
        if self.interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            wait_for = self._next_time - now
            if wait_for > 0:
                time.sleep(wait_for)
                now = time.monotonic()
            self._next_time = now + self.interval


def get_temp_dir(download_dir: Path, title: str) -> Path:
    return download_dir / f".下載中-{title}"


def get_final_dir(download_dir: Path, title: str) -> Path:
    return download_dir / title


class Downloader:
    def __init__(self, client: Optional[WnacgClient] = None, config: Optional[Config] = None):
        self.config = config or load_config()
        self.client = client or WnacgClient(self.config)
        ensure_dir(self.config.download_path)
        ensure_dir(self.config.export_path)

    def download_comic(self, comic: Comic, force: bool = False, show_progress: bool = True) -> Path:
        """下載整本漫畫，回傳最終目錄路徑。

        若全部圖片下載失敗 (零成功)，拋出 RuntimeError，便於上層以 exit code 反映失敗。
        """
        title = comic.title
        download_dir = self.config.download_path
        final_dir = get_final_dir(download_dir, title)
        temp_dir = get_temp_dir(download_dir, title)

        if final_dir.exists() and not force:
            print(f"[{title}] 已存在，跳過下載 (使用 --force 強制重新下載)")
            return final_dir

        # 清理舊的暫存目錄
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        ensure_dir(temp_dir)

        # 取得圖片清單 (如果 comic 裡沒有則重新取得)
        if not comic.img_list:
            print(f"[{title}] 正在取得圖片清單...")
            comic.img_list = self.client.get_img_list(comic.id)

        # 過濾有效圖片
        valid_imgs = [img for img in comic.img_list if not img.url.endswith("shoucang.jpg")]
        total = len(valid_imgs)
        if total == 0:
            print(f"[{title}] 沒有有效圖片")
            return final_dir

        print(f"[{title}] 開始下載 {total} 張圖片 (並行={self.config.img_concurrency})")

        # 儲存元數據
        self._save_metadata(temp_dir, comic)

        # 準備任務
        tasks = []
        for idx, img in enumerate(valid_imgs):
            # 決定檔名
            if self.config.use_original_filename:
                # 從 url 取原名
                orig = Path(img.url).stem
                base = orig or f"{idx+1:04d}"
            else:
                base = f"{idx+1:04d}"

            tasks.append((idx, img.url, base, temp_dir))

        # 並行下載：並行與限速兼具。
        # img_download_interval_sec 視為「每個並行槽每隔 N 秒發一張」，
        # 故整體節奏 = img_concurrency / interval 張/秒
        # (例：interval=1 + 並行3 → 3 張/秒)。
        # 全域發起間隔 = interval / concurrency，把請求時點均勻散開。
        success_count = 0
        failed = []
        interval = self.config.img_download_interval_sec
        spacing = interval / self.config.img_concurrency if interval > 0 else 0
        limiter = _RateLimiter(spacing)

        with ThreadPoolExecutor(max_workers=self.config.img_concurrency) as executor:
            future_to_task = {
                executor.submit(self._download_one_image, url, base, temp_dir, idx, total, limiter): (idx, url, base)
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
                        print(f"  下載圖片失敗 [{idx+1}]: {e}", file=sys.stderr)
                        failed.append((idx, url))
                    pbar.update(1)

        print(f"[{title}] 下載完成: 成功 {success_count}/{total}")

        if len(failed) > 0:
            print(f"  失敗 {len(failed)} 張: {failed[:3]}...", file=sys.stderr)

        if success_count == 0:
            # 保留暫存目錄以便檢查，並以例外向上層反映失敗 (供 exit code 使用)
            raise RuntimeError(f"[{title}] 下載失敗，沒有成功圖片 (暫存目錄: {temp_dir})")

        # 全部成功則重新命名
        if final_dir.exists():
            shutil.rmtree(final_dir, ignore_errors=True)

        shutil.move(str(temp_dir), str(final_dir))
        print(f"[{title}] 已儲存到: {final_dir}")

        # 漫畫間休息
        if self.config.comic_download_interval_sec > 0:
            print(f"等待 {self.config.comic_download_interval_sec}s 後繼續...")
            time.sleep(self.config.comic_download_interval_sec)

        return final_dir

    def _download_one_image(self, url: str, base_name: str, temp_dir: Path, idx: int, total: int, limiter: "_RateLimiter") -> bool:
        """下載單張並儲存"""
        try:
            # 檢查是否已存在 (支援不同副檔名)
            for ext in [".jpg", ".png", ".webp", ".gif"]:
                if (temp_dir / f"{base_name}{ext}").exists():
                    return True

            # 已存在的不需限速；真正要發起請求前才取得時槽
            limiter.acquire()
            data = self.client.download_image(url, max_retries=self.config.img_max_retries)

            # 猜測副檔名 (簡單從 content-type 或 url)
            ext = self._guess_ext(data, url)

            save_path = temp_dir / f"{base_name}{ext}"
            save_path.write_bytes(data)
            return True
        except Exception as e:
            print(f"    圖片 {idx+1}/{total} 下載失敗: {e}", file=sys.stderr)
            return False

    def _guess_ext(self, data: bytes, url: str) -> str:
        # 簡單 magic
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
        meta_path = temp_dir / "元數據.json"
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def download_by_id(self, comic_id: int, force: bool = False, show_progress: bool = True) -> Optional[Path]:
        print(f"正在取得漫畫資訊 ID={comic_id} ...")
        comic = self.client.get_comic(comic_id)
        print(f"標題: {comic.title}")
        print(f"分類: {comic.category} | 頁數: {comic.image_count}")
        return self.download_comic(comic, force=force, show_progress=show_progress)


def main_download_test():
    # quick test entry, not used in cli
    config = load_config()
    client = WnacgClient(config)
    downloader = Downloader(client, config)
    # example small comic
    downloader.download_by_id(288694)
