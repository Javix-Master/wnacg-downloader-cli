"""WNACG API 客户端 (基于 HTML 抓取)"""

import json
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from .config import Config, load_config
from .utils import filename_filter


@dataclass
class Tag:
    name: str
    url: str


@dataclass
class ImgInList:
    caption: str
    url: str  # may start with //


@dataclass
class Comic:
    id: int
    title: str
    cover: str
    category: str
    image_count: int
    tags: List[Tag] = field(default_factory=list)
    intro: str = ""
    img_list: List[ImgInList] = field(default_factory=list)
    is_downloaded: Optional[bool] = None


@dataclass
class ComicInSearch:
    id: int
    title: str
    title_html: str
    cover: str
    additional_info: str
    is_downloaded: bool = False


@dataclass
class SearchResult:
    comics: List[ComicInSearch]
    current_page: int
    total_page: int


@dataclass
class UserProfile:
    username: str = ""
    # add more fields as needed


class WnacgClient:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or load_config()
        self.client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            },
            timeout=30.0,
            follow_redirects=True,
        )

    @property
    def base_url(self) -> str:
        return self.config.base_url

    def _get(self, url: str, **kwargs) -> httpx.Response:
        if not url.startswith("http"):
            url = f"{self.base_url}{url}"
        headers = kwargs.pop("headers", {})
        headers.setdefault("Referer", f"{self.base_url}/")
        resp = self.client.get(url, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp

    def _post_form(self, url: str, data: dict, **kwargs) -> httpx.Response:
        if not url.startswith("http"):
            url = f"{self.base_url}{url}"
        headers = kwargs.pop("headers", {})
        headers.setdefault("Referer", f"{self.base_url}/")
        resp = self.client.post(url, data=data, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp

    def login(self, username: str, password: str) -> str:
        """登录并返回 cookie 字符串"""
        form = {
            "login_name": username,
            "login_pass": password,
        }
        resp = self._post_form("/users-check_login.html", data=form)
        try:
            data = resp.json()
            if not data.get("ret"):
                raise RuntimeError(f"登录失败: {data}")
        except Exception:
            # 某些情况下可能不是json
            pass

        # 获取 set-cookie
        cookie = resp.headers.get("set-cookie")
        if not cookie:
            # 尝试从响应体或其他
            raise RuntimeError("登录响应中没有 set-cookie")

        # 更新 client 的 cookie
        self.client.headers["Cookie"] = cookie
        return cookie

    def set_cookie(self, cookie: str):
        if cookie:
            self.client.headers["Cookie"] = cookie
            self.config.cookie = cookie
            # optionally save

    def search_by_keyword(self, keyword: str, page_num: int = 1) -> SearchResult:
        params = {
            "q": keyword,
            "syn": "yes",
            "f": "_all",
            "s": "create_time_DESC",
            "p": page_num,
        }
        resp = self._get("/search/index.php", params=params)
        return self._parse_search_result(resp.text, is_search_by_tag=False)

    def search_by_tag(self, tag_name: str, page_num: int = 1) -> SearchResult:
        url = f"/albums-index-page-{page_num}-tag-{tag_name}.html"
        resp = self._get(url)
        return self._parse_search_result(resp.text, is_search_by_tag=True)

    def _parse_search_result(self, html: str, is_search_by_tag: bool) -> SearchResult:
        soup = BeautifulSoup(html, "lxml")
        comics = []
        for li in soup.select(".li.gallary_item"):
            try:
                comic = self._parse_comic_in_search(li)
                comics.append(comic)
            except Exception as e:
                print(f"解析搜索结果中的一项失败: {e}")
                continue

        # current page
        current_page = 1
        thispage = soup.select_one(".thispage")
        if thispage:
            try:
                current_page = int(thispage.get_text(strip=True))
            except:
                pass

        # total pages
        if is_search_by_tag:
            total_page = current_page
            paginator = soup.select(".f_left.paginator > a")
            if paginator:
                try:
                    last_text = paginator[-1].get_text(strip=True)
                    total_page = max(int(last_text), current_page)
                except:
                    pass
        else:
            # from total count
            try:
                b = soup.select_one("#bodywrap .result > b")
                total = int(b.get_text(strip=True).replace(",", ""))
                PAGE_SIZE = 24
                total_page = (total + PAGE_SIZE - 1) // PAGE_SIZE
            except:
                total_page = current_page

        return SearchResult(
            comics=comics,
            current_page=current_page,
            total_page=total_page,
        )

    def _parse_comic_in_search(self, li) -> ComicInSearch:
        title_a = li.select_one(".title > a")
        if not title_a:
            raise ValueError("no title a")

        href = title_a.get("href", "")
        id_match = re.search(r"/photos-index-aid-(\d+)\.html", href)
        if not id_match:
            raise ValueError(f"bad href {href}")
        cid = int(id_match.group(1))

        title_html = title_a.get("title", "").strip()
        title = filename_filter(title_a.get_text(strip=True) or title_html)

        img = li.select_one("img")
        cover_src = img.get("src", "") if img else ""
        if cover_src.startswith("//"):
            cover = "https:" + cover_src
        else:
            cover = cover_src

        info_div = li.select_one(".info_col")
        additional_info = info_div.get_text(strip=True) if info_div else ""

        return ComicInSearch(
            id=cid,
            title=title,
            title_html=title_html,
            cover=cover,
            additional_info=additional_info,
        )

    def get_comic(self, comic_id: int) -> Comic:
        url = f"/photos-index-aid-{comic_id}.html"
        resp = self._get(url)
        html = resp.text

        # also get img list
        img_list = self.get_img_list(comic_id)

        soup = BeautifulSoup(html, "lxml")

        # id from feed link
        feed_link = soup.select_one('head > link[href*="/feed-index-aid-"]')
        if not feed_link:
            raise ValueError("找不到漫画ID的 link")
        href = feed_link.get("href", "")
        id_str = href.replace("/feed-index-aid-", "").replace(".html", "")
        cid = int(id_str)

        h2 = soup.select_one("#bodywrap > h2")
        if not h2:
            raise ValueError("找不到标题 h2")
        title = filename_filter(h2.get_text(strip=True))

        # cover
        img = soup.select_one(".asTBcell.uwthumb > img")
        if not img:
            raise ValueError("找不到封面 img")
        cover_src = img.get("src", "").lstrip("/")
        if not cover_src.startswith("http"):
            if cover_src.startswith("//"):
                cover = "https:" + cover_src
            else:
                cover = f"https://{cover_src}"
        else:
            cover = cover_src

        # labels
        labels = soup.select(".asTBcell.uwconn > label")
        if len(labels) < 2:
            raise ValueError("找不到分类或页数 label")
        cat_text = labels[0].get_text(strip=True)
        category = cat_text.replace("分類：", "").strip() if "分類：" in cat_text else cat_text

        page_text = labels[1].get_text(strip=True)
        image_count_str = page_text.replace("頁數：", "").replace("P", "").strip()
        image_count = int(image_count_str)

        # tags
        tags = []
        api_domain = self.config.api_domain
        for a in soup.select(".tagshow"):
            name = a.get_text(strip=True)
            if not name:
                continue
            href = a.get("href", "")
            url = f"https://{api_domain}{href}" if href.startswith("/") else href
            tags.append(Tag(name=name, url=url))

        # intro
        intro_p = soup.select_one(".asTBcell.uwconn > p")
        intro = str(intro_p) if intro_p else ""

        return Comic(
            id=cid,
            title=title,
            cover=cover,
            category=category,
            image_count=image_count,
            tags=tags,
            intro=intro,
            img_list=img_list,
        )

    def get_img_list(self, comic_id: int) -> List[ImgInList]:
        url = f"/photos-gallery-aid-{comic_id}.html"
        resp = self._get(url)
        body = resp.text

        line = next((l for l in body.split("\n") if "var imglist =" in l), None)
        if not line:
            raise ValueError("没有找到包含 var imglist = 的行")

        start = line.find("[")
        end = line.rfind("]") + 1
        if start == -1 or end <= start:
            raise ValueError("无法定位 imglist JSON")

        json_str = line[start:end]
        json_str = (
            json_str
            .replace("url:", '"url":')
            .replace("caption:", '"caption":')
            .replace("fast_img_host+", "")
            .replace('\\"', '"')
        )

        try:
            raw_list = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"解析 imglist JSON 失败: {e}\n片段: {json_str[:200]}") from e

        img_list = []
        for item in raw_list:
            url = item.get("url", "")
            caption = item.get("caption", "")
            if url and not url.endswith("shoucang.jpg"):
                if url.startswith("//"):
                    url = "https:" + url
                img_list.append(ImgInList(caption=caption, url=url))

        return img_list

    def get_shelf(self, shelf_id: int, page_num: int = 1) -> List[ComicInSearch]:
        """获取书架，返回搜索结果格式的列表"""
        if not self.config.cookie:
            raise RuntimeError("需要先登录 (设置 cookie)")
        url = f"/users-users_fav-page-{page_num}-c-{shelf_id}.html"
        headers = {"Cookie": self.config.cookie}
        resp = self._get(url, headers=headers)
        # 复用 search 解析，但 book shelf 可能结构类似
        # 为简单起见，这里简化返回
        result = self._parse_search_result(resp.text, is_search_by_tag=True)
        return result.comics

    def get_user_profile(self) -> UserProfile:
        if not self.config.cookie:
            raise RuntimeError("需要登录")
        resp = self._get("/users.html", headers={"Cookie": self.config.cookie})
        # 简单解析，实际可扩展
        soup = BeautifulSoup(resp.text, "lxml")
        # 假设有用户名显示
        username_el = soup.select_one(".username") or soup.select_one("h2")
        username = username_el.get_text(strip=True) if username_el else "unknown"
        return UserProfile(username=username)

    def download_image(self, url: str, referer: Optional[str] = None, max_retries: int = 3) -> bytes:
        """下载单张图片，返回 bytes。

        失败时自动重试 max_retries 次：
        - 429 (限速/IP 被封)：退避较久后重试 (5s * attempt)。
        - 超时 / 连线错误 / 5xx：短退避后重试 (1.5s * attempt)。
        - 其他 4xx：直接抛出，不重试。
        """
        headers = {"Referer": referer or f"{self.base_url}/"}
        last_err: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                resp = self.client.get(url, headers=headers, timeout=60.0)
                if resp.status_code == 429:
                    last_err = RuntimeError("HTTP 429 (IP 被限速)")
                    time.sleep(5 * attempt)
                    continue
                resp.raise_for_status()
                return resp.content
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code >= 500:
                    time.sleep(1.5 * attempt)
                    continue
                raise  # 4xx (非 429) 无重试意义
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_err = e
                time.sleep(1.5 * attempt)

        raise RuntimeError(f"下载失败 (重试 {max_retries} 次后放弃): {last_err}")

    def close(self):
        self.client.close()
