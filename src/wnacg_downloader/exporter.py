"""导出为 CBZ / PDF"""

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import List, Optional

import img2pdf

from .config import Config, load_config
from .utils import ensure_dir, is_image_file


def generate_comicinfo_xml(comic_title: str, category: str = "", tags: List[str] = None, intro: str = "", page_count: int = 0) -> str:
    """生成简单的 ComicInfo.xml (Kavita / 漫画阅读器兼容)"""
    root = ET.Element("ComicInfo")
    ET.SubElement(root, "Manga").text = "Yes"
    ET.SubElement(root, "Series").text = comic_title
    ET.SubElement(root, "Publisher").text = "绅士漫画"
    ET.SubElement(root, "Genre").text = category
    if tags:
        ET.SubElement(root, "Tags").text = ", ".join(tags)
    ET.SubElement(root, "Summary").text = intro
    ET.SubElement(root, "Number").text = "1"
    ET.SubElement(root, "Format").text = "Special"
    ET.SubElement(root, "PageCount").text = str(page_count)
    ET.SubElement(root, "Count").text = "1"

    # pretty print
    from xml.dom import minidom
    rough = ET.tostring(root, encoding="utf-8")
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ", encoding=None)


def export_cbz(comic_dir: Path, export_dir: Optional[Path] = None, config: Optional[Config] = None) -> Path:
    """将已下载的漫画目录导出为 .cbz (zip + ComicInfo.xml)"""
    config = config or load_config()
    export_base = export_dir or config.export_path
    ensure_dir(export_base)

    title = comic_dir.name
    cbz_path = export_base / f"{title}.cbz"

    images = sorted(
        [p for p in comic_dir.iterdir() if is_image_file(p) and p.is_file()],
        key=lambda p: p.name
    )

    if not images:
        raise ValueError(f"{comic_dir} 中没有图片文件")

    # 尝试读取元数据
    meta_path = comic_dir / "元数据.json"
    tags = []
    category = ""
    intro = ""
    page_count = len(images)
    if meta_path.exists():
        import json
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        category = meta.get("category", "")
        intro = meta.get("intro", "")
        tags = [t["name"] for t in meta.get("tags", [])]

    xml_content = generate_comicinfo_xml(title, category, tags, intro, page_count)

    with zipfile.ZipFile(cbz_path, "w", compression=zipfile.ZIP_STORED) as zf:
        # 写入 ComicInfo.xml
        zf.writestr("ComicInfo.xml", xml_content)

        for img in images:
            zf.write(img, arcname=img.name)

    print(f"CBZ 已导出: {cbz_path}")
    return cbz_path


def export_pdf(comic_dir: Path, export_dir: Optional[Path] = None, config: Optional[Config] = None) -> Path:
    """使用 img2pdf 将图片目录导出为 PDF (每页一图，保持原始尺寸)"""
    config = config or load_config()
    export_base = export_dir or config.export_path
    ensure_dir(export_base)

    title = comic_dir.name
    pdf_path = export_base / f"{title}.pdf"

    images = sorted(
        [str(p) for p in comic_dir.iterdir() if is_image_file(p) and p.is_file()],
        key=lambda p: Path(p).name
    )

    if not images:
        raise ValueError(f"{comic_dir} 中没有图片文件")

    print(f"正在生成 PDF: {len(images)} 页 ...")
    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert(images))

    print(f"PDF 已导出: {pdf_path}")
    return pdf_path


def export_comic(comic_dir: Path, fmt: str = "cbz", **kwargs):
    fmt = fmt.lower()
    if fmt == "cbz":
        return export_cbz(comic_dir, **kwargs)
    elif fmt in ("pdf", "p"):
        return export_pdf(comic_dir, **kwargs)
    else:
        raise ValueError("支持的格式: cbz, pdf")
