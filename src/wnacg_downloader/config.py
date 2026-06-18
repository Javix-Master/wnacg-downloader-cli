"""配置管理"""

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional


DEFAULT_API_DOMAIN = "www.wn06.cfd"


@dataclass
class Config:
    cookie: str = ""
    download_dir: str = str(Path.home() / "wnacg-downloads")
    export_dir: str = str(Path.home() / "wnacg-exports")
    api_domain: str = DEFAULT_API_DOMAIN
    img_concurrency: int = 8
    comic_concurrency: int = 2  # not heavily used in CLI
    img_download_interval_sec: int = 1
    comic_download_interval_sec: int = 0
    img_max_retries: int = 3  # 單張圖片下載失敗時的重試次數
    use_original_filename: bool = False
    # download_format not fully implemented, always save original or jpg

    @property
    def download_path(self) -> Path:
        return Path(self.download_dir)

    @property
    def export_path(self) -> Path:
        return Path(self.export_dir)

    @property
    def base_url(self) -> str:
        return f"https://{self.api_domain}"


CONFIG_FILE_NAME = "config.json"


def get_config_path() -> Path:
    """Get config file path. Use ~/.config/wnacg-downloader/config.json or project local."""
    config_dir = Path.home() / ".config" / "wnacg-downloader"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / CONFIG_FILE_NAME


def load_config() -> Config:
    path = get_config_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Merge with defaults for new fields
            defaults = asdict(Config())
            for k, v in defaults.items():
                if k not in data:
                    data[k] = v
            return Config(**data)
        except Exception as e:
            print(f"警告: 加载配置失败 ({e})，使用默认配置")
    return Config()


def save_config(config: Config) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(config)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"配置已保存到 {path}")
