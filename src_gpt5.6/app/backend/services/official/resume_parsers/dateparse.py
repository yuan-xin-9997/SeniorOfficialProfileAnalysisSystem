"""中文履历文本的日期区间识别与片段切分引擎。

核心逻辑适配自 ``scripts/ccdata/extract_proto.py``（生成 376 人种子数据时
验证过的实现），补充了“1973－1975年”这类省略首个“年”的区间写法，并去掉
了 wikitext 清洗部分——本模块只处理已经提取出来的纯文本行。
"""
from __future__ import annotations

import re

_DASH = r"(?:—|–|~|─|－|到|至|-)"
_DAY = r"(?:\s*\d{1,2}\s*日)?"

# 各档日期区间：(start, end, span_start, span_end)，只取命中的最高档。
_TIER_FULL = re.compile(
    rf"(\d{{4}})[年\.．](\d{{1,2}})?月?{_DAY}\s*{_DASH}\s*(\d{{4}})[年\.．](\d{{1,2}})?月?{_DAY}"
)
_TIER_UNTIL_NOW = re.compile(
    rf"(\d{{4}})[年\.．](\d{{1,2}})?月?{_DAY}\s*{_DASH}?\s*(至今|现在|迄今)"
)
# 裸年份区间：1973－1975年（首个“年”可省略，末尾“年”可有可无）。
_TIER_BARE_YEARS = re.compile(rf"(\d{{4}})\s*{_DASH}\s*(\d{{4}})\s*年?")
_TIER_SINCE = re.compile(rf"(\d{{4}})[年\.．](\d{{1,2}})?月?{_DAY}\s*起")
_TIER_YEAR_MONTH = re.compile(rf"(\d{{4}})\s*年\s*(\d{{1,2}})\s*月{_DAY}")
_TIER_YEAR_ONLY = re.compile(r"(\d{4})\s*年")

_BIRTH = re.compile(r"^\s*(19|20)\d{2}\s*年\s*\d{1,2}\s*月?\s*(出生|诞生|出生，|出生。）)")
_NOISE = re.compile(
    r"接待|会见|會見|訪問|访问|出访|到访|讲话|發表|发表|谈话|表示|指出|强调|認為|认为"
    r"|报道|報道|采访|專訪|专访|演讲|致辞|致信|贺信|唁电|会见时"
)
# 网页噪音（导航、版权、日期戳等）混进职位字段的特征。
_POSITION_JUNK = re.compile(
    r"星期|版权|备案|ICP|Copyright|浏览次数|责任编辑|来源[:：]|打印|字号|分享到"
    r"|上一篇|下一篇|返回顶部|网站地图|联系我们"
)
_FAMILY = re.compile(r"父亲|母亲|岳父|之子|其子|出生|诞生|逝世|去世")

_IDENTITY_RE = re.compile(
    r"，男，|，女，|男性，|女性，|中华人民共和国政治人物|中国共产党、中华人民共和国"
    r"|中华人民共和国外交官|政治人物，|籍贯|中华人民共和国军人|中国人民解放军中将"
    r"|中国人民解放军上将|中国人民解放军少将"
)
_IDENTITY_PREFIX = re.compile(
    r"^[）)】」》]?\s*[（(]?(?:男|女|男性|女性)[，,]?(?:汉族|[^，,]{1,4}族)?[，,]?"
    r"(?:\d{4}\s*年(?:\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?)?生?[，,]?)?"
    r"[\u4e00-\u9fa5·]{2,15}(?:省|市|自治区|县|旗|特别行政区)?人[，,]?"
    r"(?:中华人民共和国|中国共产党、中华人民共和国)?政治人物[，,]?"
    r"|\s*[（(]?(?:男|女|男性|女性)[，,](?:汉族|[^，,]{1,4}族)?[，,]?"
    r"|(?:中华人民共和国|中国共产党、中华人民共和国)?政治人物[，,]?"
    r"|中华人民共和国外交官[，,]?|中华人民共和国军人[，,]?"
)
_LEAD_JUNK = "）)】」》>，,。；;：: （(、－—–~─"
# 姓名去除后残留的引导动词（避免“任中共XX委书记”这类前缀），长词在前；
# “任职”开头的不剥（否则“任职国家电网”会被误剥成“职国家电网”）。
_LEADING_VERB = re.compile(r"^(?:挂职担任|火线调任|曾任|担任|调任|升任|改任|出任|选任|兼任|任)(?!职)")


def _fmt(y: str, m: str | None) -> str:
    return f"{y}.{int(m):02d}" if m else y


def find_ranges(s: str) -> list[tuple[str, str, int, int]]:
    """返回文本中的日期区间，只取命中的最高档，可选“日”后缀并入区间。"""
    out: list[tuple[str, str, int, int]] = []
    for m in _TIER_FULL.finditer(s):
        out.append((_fmt(m.group(1), m.group(2)), _fmt(m.group(3), m.group(4)), m.start(), m.end()))
    if out:
        return out
    for m in _TIER_UNTIL_NOW.finditer(s):
        out.append((_fmt(m.group(1), m.group(2)), "至今", m.start(), m.end()))
    if out:
        return out
    for m in _TIER_BARE_YEARS.finditer(s):
        out.append((m.group(1), m.group(2), m.start(), m.end()))
    if out:
        return out
    for m in _TIER_SINCE.finditer(s):
        out.append((_fmt(m.group(1), m.group(2)), "", m.start(), m.end()))
    for m in _TIER_YEAR_MONTH.finditer(s):
        out.append((_fmt(m.group(1), m.group(2)), "", m.start(), m.end()))
    if out:
        return out
    for m in _TIER_YEAR_ONLY.finditer(s):
        out.append((m.group(1), "", m.start(), m.end()))
    return out


def _strip_identity_prefix(p: str) -> str:
    prev = None
    while prev != p:
        prev = p
        p = p.lstrip(_LEAD_JUNK)
        m = _IDENTITY_PREFIX.match(p)
        if m:
            p = p[m.end():]
    return p.strip(_LEAD_JUNK)


def _clean_piece(p: str, name: str = "") -> str:
    """日期后正文 → 职位字段：去身份前缀、去姓名引导、压掉全部空白。"""
    p = p.strip(" ，,。；;：:、　")
    p = re.sub(r"^\s*(其间|其中|此后|后|同年|次年|不久|随后|早年在?|中共?成立后)[，：:：\s]*", "", p)
    p = re.sub(r"^\s*[他她](?=(曾任|先后|调|任|进入))", "", p)
    p = _strip_identity_prefix(p)
    if name:
        p = re.sub(rf"^{re.escape(name)}(?:同志)?[，,：:、\s]*", "", p)
    p = re.sub(r"^[現现]任", "", p)
    p = _LEADING_VERB.sub("", p, count=1)
    p = re.sub(r"至今$", "", p)
    return re.sub(r"\s+", "", p)


def _is_identity(pos: str) -> bool:
    p = pos.strip()
    if not p:
        return True
    if p[0] in "）)（(【」》>,，。":
        return True
    if _IDENTITY_RE.search(p[:20]):
        return True
    if len(p) <= 12 and p.endswith("人"):
        return True
    if re.search(r"人[,，](?:中国|中华|中共|现任|現任|曾任|历任)", p[:45]):
        return True
    return False


def _sort_key(seg: dict):
    m = re.match(r"(\d{4})(?:\.(\d{1,2}))?", str(seg.get("start_date", "")))
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)


def parse_career_text(text: str, name: str = "") -> list[dict]:
    """从履历文本（行/句已按 \\n 组织）解析出任职经历列表。

    返回字典字段与 CareerData 对齐（不含 id/sort_order）：
    start_date / end_date / organization / position / location /
    administrative_rank / description。
    """
    segments: list[dict] = []
    for chunk in re.split(r"[。；;\n]", text or ""):
        chunk = chunk.strip()
        if len(chunk) < 6 or _NOISE.search(chunk) or _BIRTH.match(chunk[:20]):
            continue
        ranges = find_ranges(chunk)
        if not ranges:
            continue
        spans = [(r[2], r[3]) for r in ranges]
        for (start, end, _s0, s1), piece in zip(ranges, _pieces(chunk, spans)):
            rest = _clean_piece(piece, name)
            if not rest:
                continue
            segments.append(
                {
                    "start_date": start,
                    "end_date": end or "",
                    "organization": "",
                    "position": rest[:250],
                    "location": "",
                    "administrative_rank": "",
                    "description": re.sub(r"\s+", "", chunk)[:1000],
                }
            )
    segments.sort(key=_sort_key)
    # 空结尾 = 下一段的开始；最后一段视为在任。
    for i, seg in enumerate(segments):
        if not seg["end_date"]:
            seg["end_date"] = segments[i + 1]["start_date"] if i + 1 < len(segments) else "至今"
    out = []
    for seg in segments:
        if len(seg["position"]) < 3:
            continue
        if _is_identity(seg["position"]):
            continue
        if _FAMILY.search(seg["position"][:30]):
            continue
        if _POSITION_JUNK.search(seg["position"]):
            continue
        out.append(seg)
    return out


def _pieces(chunk: str, spans: list[tuple[int, int]]) -> list[str]:
    """每个日期区间之后的正文，直到下一个日期区间。"""
    pieces = []
    for i, (_s0, s1) in enumerate(spans):
        nxt = spans[i + 1][0] if i + 1 < len(spans) else len(chunk)
        pieces.append(chunk[s1:nxt])
    return pieces
