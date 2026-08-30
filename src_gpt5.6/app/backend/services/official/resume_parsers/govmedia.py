"""官媒及一般中文网站履历通用解析器。

新华社/人民网/中国政府网等发布的领导干部简历遵循高度统一的格式：

    蔡奇，男，汉族，1955年12月生，……
    1973－1975年　福建省永安县西洋公社插队知青
    1975－1978年　福建师范大学政教系政教专业学习

即以日期区间开头的行/句。本解析器抓取页面正文行（p/li），交给共享的日期
区间引擎过滤导航、版权、日期戳等噪音，不依赖任何特定站点的 DOM 结构。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from .dateparse import parse_career_text


def parse_gov_media(html: str, name: str = "") -> list[dict]:
    soup = BeautifulSoup(html or "", "html.parser")
    if not isinstance(soup, Tag):
        return []
    for noise in soup(["script", "style", "nav", "header", "footer", "noscript", "iframe"]):
        noise.decompose()

    lines: list[str] = []
    for el in soup.find_all(["p", "li"]):
        text = _inline_text(el)
        if text:
            lines.append(text)
    return parse_career_text("\n".join(lines), name)


def _inline_text(el: Tag) -> str:
    """块内文本：剔除引用角标，行内标签边界用空串连接，压掉空白。

    行内 <a> 等标签不能以换行连接，否则一个句子会被切成残句。
    """
    for noise in list(el.find_all(["sup", "span"])):
        try:
            classes = noise.get("class") or []
            if noise.name == "sup" or "reference" in classes or "noprint" in classes:
                noise.decompose()
        except AttributeError:
            continue  # 嵌套元素已被父级 decompose，跳过失效节点
    text = el.get_text("", strip=True)
    return re.sub(r"\s+", "", text) if text else ""

