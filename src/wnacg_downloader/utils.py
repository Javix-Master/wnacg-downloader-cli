"""工具函数"""

import re
from pathlib import Path


def filename_filter(s: str) -> str:
    """过滤文件名中的非法字符，参考原 Rust 实现"""
    replacements = {
        "\\": " ",
        "/": " ",
        ":": "：",
        "*": "⭐",
        "?": "？",
        '"': "'",
        "<": "《",
        ">": "》",
        "|": "丨",
        "\0": "",
    }
    result = "".join(replacements.get(c, c) for c in s)
    # 额外清理
    result = re.sub(r'[\s]+', ' ', result).strip()
    # Windows 保留名
    reserved = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}
    if result.upper() in reserved:
        result = f"_{result}"
    return result[:200]  # 限制长度


def sanitize_filename(name: str) -> str:
    """更通用的文件名清理"""
    name = filename_filter(name)
    # 移除前后点和空格
    name = name.strip().strip(".")
    return name or "untitled"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def is_image_file(path: Path) -> bool:
    return path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
