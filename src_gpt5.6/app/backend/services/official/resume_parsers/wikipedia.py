"""维基百科（zh.wikipedia.org 等姊妹站点）人物条目履历专用解析器。

中文政治人物条目的履历有两种形态，本模块都支持：

1. “生平/履历”章节：``div.mw-heading``（新版 Vector 皮肤）或裸 ``h2/h3/h4``
   （旧版皮肤）划出的章节，正文是带日期的叙事段落；
2. 信息框（infobox vcard）：部分条目生平章节很短甚至为空，任职经历以
   “职务 + 任期 YYYY年M月D日—YYYY年M月D日”的行式信息框呈现。

章节优先、信息框兜底、导语最后，全部走共享的日期区间引擎。
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from .dateparse import find_ranges, parse_career_text

# 章节标题命中即视为履历章节（简繁都收），与种子数据生成脚本保持同源。
CAREER_SECTIONS = {
    "个人经历", "生平", "经历", "履历", "人物经历", "任职经历", "工作经历",
    "从政经历", "早年经历", "军旅生涯", "主要经历", "人物履历", "仕途", "职业生涯",
    "簡歷", "簡曆", "履歷", "人物經歷", "任職經歷", "工作經歷", "從政經歷",
    "早年經歷", "軍旅生涯", "主要經歷", "人物履歷", "職業生涯",
}
# 命中这些词的章节（同级或以下）终止履历采集。
_SECTION_STOP = re.compile(
    r"参考文献|外部链接|参见|参考资料|注释|家世|家族|个人生活|家庭|荣誉|评价|争议"
    r"|言论|观点|轶事|任内政策|政治主张|主要观点|意识形态|著作"
)
_HEADING_TAGS = ("h2", "h3", "h4", "h5")
# 信息框里出现这些标签的行不是职务标题。
_INFOBOX_LABELS = {
    "任期", "前任", "继任", "总理", "副总理", "秘书长", "主席", "副主席", "总书记",
    "书记", "君主", "总统", "首相", "上任", "下任", "出生", "逝世", "籍贯", "国籍",
    "政党", "学历", "母校", "职业", "专业", "宗教信仰", "配偶", "子女", "父母",
    "签名", "网站",
}


def parse_wikipedia(html: str, name: str = "") -> list[dict]:
    soup = BeautifulSoup(html or "", "html.parser")
    content = soup.find(id="mw-content-text") or soup.body or soup
    if not isinstance(content, Tag):
        return []

    picked = _pick_career_lines(_structured_sections(content))
    if picked:
        segments = parse_career_text("\n".join(picked), name)
        if segments:
            return segments

    segments = _parse_infobox(content)
    if segments:
        return segments

    return _parse_intro(content, name)


def _iter_headings(content: Tag):
    """按文档顺序产出 (锚点元素, 层级, 标题)。

    新版皮肤标题被 ``div.mw-heading`` 包裹，锚点取包裹 div（其兄弟才是正文）；
    旧版皮肤直接用 h2/h3/h4 本身。标题文本去掉“[编辑]”尾巴。
    """
    for h in content.find_all(_HEADING_TAGS):
        if h.find_parent(id="vector-toc") or h.find_parent("nav"):
            continue
        title = re.sub(r"\[\s*编[辑輯]\s*\]", "", h.get_text(" ", strip=True)).strip()
        if not title:
            continue
        parent = h.parent
        anchor = parent if isinstance(parent, Tag) and "mw-heading" in (parent.get("class") or []) else h
        yield anchor, int(h.name[1]), title


def _is_heading_wrapper(el: Tag) -> bool:
    return el.name == "div" and "mw-heading" in (el.get("class") or [])


def _structured_sections(content: Tag) -> list[tuple[str, int, list[str]]]:
    """把正文切成 (标题, 层级, 文本行) 序列；首个标题之前为导语（空标题）。"""
    marks = list(_iter_headings(content))
    if not marks:
        return []
    anchors = [anchor for anchor, _lvl, _t in marks]

    lead_lines: list[str] = []
    for sib in anchors[0].previous_siblings:
        if isinstance(sib, Tag) and sib.name in ("p", "ul", "ol"):
            lead_lines.append(_inline_text(sib))

    structured: list[tuple[str, int, list[str]]] = [("", 1, lead_lines)]
    for i, (anchor, level, title) in enumerate(marks):
        lines: list[str] = []
        for sib in anchor.find_next_siblings():
            if i + 1 < len(anchors) and sib is anchors[i + 1]:
                break
            if not isinstance(sib, Tag):
                continue
            if _is_heading_wrapper(sib) or sib.name in _HEADING_TAGS:
                break
            if sib.name == "p":
                lines.append(_inline_text(sib))
            elif sib.name in ("ul", "ol"):
                lines.extend(_inline_text(li) for li in sib.find_all("li") if _inline_text(li))
        structured.append((title, level, lines))
    return structured


def _inline_text(el: Tag) -> str:
    """块内文本：剔除引用角标/编辑按钮，行内标签边界用空串连接。

    不能用 get_text("\\n")——条目正文里大量 <a> 链接会把一个句子切碎，
    导致“加入中国共产党”被切成“加入”这样的残句。
    """
    for noise in list(el.find_all(["sup", "span"])):
        try:
            classes = noise.get("class") or []
            if noise.name == "sup" or "mw-editsection" in classes or "reference" in classes or "noprint" in classes:
                noise.decompose()
        except AttributeError:
            continue  # 嵌套元素已被父级 decompose，跳过失效节点
    text = el.get_text("", strip=True)
    return re.sub(r"\s+", "", text) if text else ""


def _pick_career_lines(sections: list[tuple[str, int, list[str]]]) -> list[str]:
    """与种子生成脚本同源的章节挑选：进入履历章节后收集，直到同级非履历章节。"""
    picked: list[str] = []
    in_career = False
    root_level = 6
    for title, level, lines in sections:
        if title in CAREER_SECTIONS:
            if not in_career:
                in_career = True
                root_level = level
        elif in_career and (level <= root_level or _SECTION_STOP.search(title)):
            in_career = False
        if in_career:
            picked.extend(lines)
    if not picked:
        # 没有命中任何履历章节：给出全部章节正文，交给日期引擎过滤噪音，
        # 覆盖“生平”标题不在预设名单里但正文仍是履历的条目。
        picked = [line for _title, _level, lines in sections for line in lines]
    return picked


def _parse_infobox(content: Tag) -> list[dict]:
    """信息框兜底：“职务标题行 + 任期行”模式（如丁学东条目）。"""
    ib = content.find("table", class_=re.compile(r"\binfobox\b"))
    if not isinstance(ib, Tag):
        return []
    segments: list[dict] = []
    pending_title = ""
    for tr in ib.find_all("tr"):
        text = re.sub(r"\s+", "", tr.get_text(" ", strip=True))
        if not text:
            continue
        th = tr.find("th")
        th_text = re.sub(r"\s+", "", th.get_text(" ", strip=True)) if th else ""
        ranges = find_ranges(text)
        if "任期" in text and ranges:
            if pending_title:
                for start, end, _s0, _s1 in ranges:
                    segments.append(
                        {
                            "start_date": start,
                            "end_date": end or "至今",
                            "organization": pending_title,
                            "position": pending_title,
                            "location": "",
                            "administrative_rank": "",
                            "description": f"任期 {start} — {end or '至今'}",
                        }
                    )
            pending_title = ""
            continue
        if _is_office_title_row(th_text, text):
            pending_title = text
    segments.sort(key=lambda s: s["start_date"])
    return segments


def _is_office_title_row(th_text: str, row_text: str) -> bool:
    if not row_text or "任期" in row_text:
        return False
    if th_text in _INFOBOX_LABELS:
        return False
    if th_text and len(th_text) <= 4:
        return False  # 短标签行（民族/出生等）不是职务
    if len(row_text) > 60:
        return False
    if any(label in row_text for label in ("前任", "继任", "现任", "个人资料")):
        return False
    return bool(re.search(r"[\u4e00-\u9fa5]", row_text)) and len(row_text) >= 4


def _parse_intro(content: Tag, name: str) -> list[dict]:
    """最后兜底：没有章节、没有信息框时，用导语段落里带日期的句子。"""
    lines = [_inline_text(el) for el in content.find_all("p")]
    lines = [line for line in lines if line]
    return parse_career_text("\n".join(lines[:6]), name)
