"""履历专用解析器分发入口。

按来源 URL 选择解析器：维基百科姊妹站点走 DOM 专用解析器，其余（官媒等）
走标准简历格式通用解析器。新增官员只要把 ``source_url`` 配成这两类页面，
履历刷新即自动使用对应解析器。
"""
from __future__ import annotations

from urllib.parse import urlsplit

from .govmedia import parse_gov_media
from .wikipedia import parse_wikipedia

__all__ = ["parse_resume", "is_wikipedia_url", "parser_label_for"]


def is_wikipedia_url(url: str) -> bool:
    host = (urlsplit(url or "").hostname or "").lower().rstrip(".")
    return host == "wikipedia.org" or host.endswith(".wikipedia.org")


def parser_label_for(url: str) -> str:
    return "维基百科解析器" if is_wikipedia_url(url) else "通用解析器"


def parse_resume(html: str, url: str, name: str = "") -> list[dict]:
    """解析页面 HTML，返回与 CareerData 字段对齐的任职经历字典列表。"""
    if not html:
        return []
    if is_wikipedia_url(url):
        return parse_wikipedia(html, name)
    return parse_gov_media(html, name)
