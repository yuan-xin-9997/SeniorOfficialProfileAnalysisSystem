# -*- coding: utf-8 -*-
"""Wikitext cleaning + profile/career extraction (v2).

Usage: python extract_proto.py <article_file> [more_files...]
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path


def _setup_stdout() -> None:
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# ---------- wikitext cleaning ----------

DROP_TEMPLATES = {
    "rp", "reflist", "notelist", "efn", "small", "big", "nowrap", "lang", "nihongo",
    "ill", "clear", "toclimit", "main", "see also", "further", "sfn", "cite web",
    "cite news", "cite book", "cite journal", "citation", "cite", "cite doi",
    "noteTag", "notetag", "reflabel", "refn", "width", "DEFAULTSORT", "authority control",
    "cpc/logo", "pla-army", "pla-navy", "pla-air force", "prc", "roc", "cn",
    "chinese title", "noteat", "hid", "col-begin", "col-break", "col-end",
}
KEEP_FIRST_TEMPLATES = {
    "bd", "birth date and age", "birth date", "birth", "bda",
    "death date and age", "death date",
}


def strip_templates(text: str) -> str:
    for _ in range(15):
        m = re.search(r"\{\{([^{}]*)\}\}", text)
        if not m:
            break
        inner = m.group(1)
        name = inner.split("|")[0].strip().lower()
        args = [a.strip() for a in inner.split("|")[1:]]
        if name in KEEP_FIRST_TEMPLATES:
            repl = "".join(a for a in args if a and "=" not in a)
        elif name in DROP_TEMPLATES:
            repl = ""
        else:
            pos = [a for a in args if a and "=" not in a]
            repl = pos[0] if pos else ""
        text = text[: m.start()] + repl + text[m.end():]
    return text


def tidy(text: str) -> str:
    text = re.sub(r"，{2,}", "，", text)
    text = re.sub(r"[（(]\s*[)）]", "", text)
    text = re.sub(r"（\s*，", "（", text)
    text = re.sub(r"，\s*）", "）", text)
    text = re.sub(r"\{\{rp\|[^}]*\}\}", "", text)
    return text


def clean_wikitext(raw: str) -> str:
    text = re.sub(r"<ref[^>/]*/>", "", raw)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    # file/image links before generic links
    text = re.sub(r"\[\[(?:File|Image|文件|图像|檔案|档案|Image?):[^\]]*\]\]", "", text, flags=re.I)
    text = strip_templates(text)
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"'''?", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ")
    # drop everything before the article intro (infobox residue)
    m = re.search(r"'''[^']{1,40}'''", text)
    if m:
        text = text[m.start():]
    lines = [ln.strip() for ln in text.split("\n")]
    return tidy("\n".join(ln for ln in lines if ln))


SECTION_RE = re.compile(r"^(=+)\s*(.+?)\s*\1\s*$", re.M)
CAREER_SECTIONS = {
    "个人经历", "生平", "经历", "履历", "人物经历", "任职经历", "工作经历",
    "从政经历", "早年经历", "军旅生涯", "主要经历", "人物履历", "仕途", "职业生涯",
    "個人經歷", "經歷", "簡歷", "簡曆", "履歷", "人物經歷", "任職經歷", "工作經歷",
    "從政經歷", "早年經歷", "軍旅生涯", "主要經歷", "人物履歷", "職業生涯",
}


def extract_career_text(text: str) -> str:
    heads = list(SECTION_RE.finditer(text))
    levels = [len(h.group(1)) for h in heads]
    picked: list[str] = []
    in_career = False
    root_level = 0
    for i, h in enumerate(heads):
        title = h.group(2).strip()
        level = levels[i]
        if title in CAREER_SECTIONS:
            if not in_career:
                in_career = True
                root_level = level
        elif in_career and level <= root_level:
            in_career = False
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        if in_career:
            picked.append(text[h.end():end])
    if not picked:
        first = heads[0].start() if heads else len(text)
        body = text[:first]
        lines = [ln for ln in body.split("\n") if ln.strip()]
        # drop identity intro lines (no career verb) from the top
        k = 0
        for ln in lines:
            if CAREER_VERB.search(ln):
                break
            k += 1
        picked = lines[k:] or lines
    joined = "\n".join(picked)
    joined = re.sub(r"==+\s*(?:参考文献|外部链接|参见|参考资料|注释|家世|家族|个人生活|家庭|荣誉|评价|争议|言论|观点|轶事)\s*==+.*", "", joined, flags=re.S)
    return joined.strip()


# ---------- date parsing ----------

def fmt(y: str, m: str | None) -> str:
    return f"{y}.{int(m):02d}" if m else y


def find_ranges(s: str) -> list[tuple[str, str, int, int]]:
    """Date spans, best tier only: (start, end, span_start, span_end).
    Optional '日' suffixes are absorbed into the span."""
    out = []
    DAY = r"(?:\s*\d{1,2}\s*日)?"
    for m in re.finditer(
        rf"(\d{{4}})[年\.．](\d{{1,2}})?月?{DAY}\s*(?:—|–|~|─|－|到|至|-)\s*(\d{{4}})[年\.．](\d{{1,2}})?月?{DAY}", s
    ):
        out.append((fmt(m.group(1), m.group(2)), fmt(m.group(3), m.group(4)), m.start(), m.end()))
    if out:
        return out
    for m in re.finditer(
        rf"(\d{{4}})[年\.．](\d{{1,2}})?月?{DAY}\s*(?:—|–|~|－)?\s*(至今|现在|迄今)", s
    ):
        out.append((fmt(m.group(1), m.group(2)), "至今", m.start(), m.end()))
    if out:
        return out
    for m in re.finditer(r"(\d{4})\s*年\s*(?:—|–|~|－|到|至|-)\s*(\d{4})\s*年?", s):
        out.append((m.group(1), m.group(2), m.start(), m.end()))
    if out:
        return out
    for m in re.finditer(rf"(\d{{4}})[年\.．](\d{{1,2}})?月?{DAY}\s*起", s):
        out.append((fmt(m.group(1), m.group(2)), "", m.start(), m.end()))
    for m in re.finditer(rf"(\d{{4}})\s*年\s*(\d{{1,2}})\s*月{DAY}", s):
        out.append((fmt(m.group(1), m.group(2)), "", m.start(), m.end()))
    if out:
        return out
    for m in re.finditer(r"(\d{4})\s*年", s):
        out.append((m.group(1), "", m.start(), m.end()))
    return out


START_STOP = re.compile(r"^\s*(19|20)\d{2}\s*年\s*\d{1,2}\s*月?\s*(出生|诞生|出生，|出生。）)")
NOISE = re.compile(
    r"接待|会见|會見|訪問|访问|出访|到访|讲话|發表|发表|谈话|表示|指出|强调|認為|认为|报道|報道|采访|專訪|专访|演讲|致辞|致信|贺信|唁电|会见时"
)
EVENT_KEEP_EVENTUALLY = None  # events like 晋升/当选 kept


def piece_text(chunk: str, spans: list[tuple[int, int]]) -> list[str]:
    """Text AFTER each date span, up to the next date span (date leads content)."""
    pieces = []
    for i, (_s0, s1) in enumerate(spans):
        nxt = spans[i + 1][0] if i + 1 < len(spans) else len(chunk)
        pieces.append(chunk[s1:nxt])
    return pieces


def clean_piece(p: str) -> str:
    p = p.strip(" ，,。；;：:、")
    p = re.sub(r"^\s*(其间|其中|此后|后|同年|次年|不久|随后|早年在?|中共?成立后)[，：:：\s]*", "", p)
    p = re.sub(r"^\s*他|她(?=(曾任|先后|调|任|进入))", "", p)
    p = strip_identity_prefix(p)
    p = re.sub(r"^[現现]任", "", p)
    p = re.sub(r"\s+", "", p)
    return p


IDENTITY_RE = re.compile(
    r"，男，|，女，|男性，|女性，|中华人民共和国政治人物|中国共产党、中华人民共和国|中华人民共和国外交官|"
    r"政治人物，|籍贯|中华人民共和国军人|中国人民解放军中将|中国人民解放军上将|中国人民解放军少将"
)


IDENTITY_PREFIX = re.compile(
    r"^[）)】」》]?\s*[（(]?(?:男|女|男性|女性)[，,]?(?:汉族|[^，,]{1,4}族)?[，,]?"
    r"(?:\d{4}\s*年(?:\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?)?生?[，,]?)?"
    r"[\u4e00-\u9fa5·]{2,15}(?:省|市|自治区|县|旗|特别行政区)?人[，,]?"
    r"(?:中华人民共和国|中国共产党、中华人民共和国)?政治人物[，,]?"
    r"|\s*[（(]?(?:男|女|男性|女性)[，,](?:汉族|[^，,]{1,4}族)?[，,]?"
    r"|(?:中华人民共和国|中国共产党、中华人民共和国)?政治人物[，,]?"
    r"|中华人民共和国外交官[，,]?|中华人民共和国军人[，,]?"
)
LEAD_JUNK = "）)】」》>，,。；;：: （(、"


def strip_identity_prefix(p: str) -> str:
    prev = None
    while prev != p:
        prev = p
        p = p.lstrip(LEAD_JUNK)
        m = IDENTITY_PREFIX.match(p)
        if m:
            p = p[m.end():]
    return p.strip(LEAD_JUNK)


def is_identity(pos: str) -> bool:
    p = pos.strip()
    if not p:
        return True
    if p[0] in "）)（(【」》>,，。":
        return True
    if IDENTITY_RE.search(p[:20]):
        return True
    if len(p) <= 12 and p.endswith("人"):
        return True
    if re.search(r"人[,，](?:中国|中华|中共|现任|現任|曾任|历任)", p[:45]):
        return True
    return False


def parse_careers(cleaned: str, name: str = "") -> list[dict]:
    career_text = extract_career_text(cleaned)
    chunks = re.split(r"[。；;\n]", career_text)
    segs: list[dict] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if len(chunk) < 6 or NOISE.search(chunk):
            continue
        if START_STOP.search(chunk[:20]):
            continue
        ranges = find_ranges(chunk)
        if not ranges:
            continue
        spans = [(r[2], r[3]) for r in ranges]
        pieces = piece_text(chunk, spans)
        for (start, end, _s0, _s1), piece in zip(ranges, pieces):
            rest = clean_piece(piece)
            if not rest and not piece.strip():
                continue
            desc = tidy(chunk)
            segs.append(
                {
                    "start_date": start,
                    "end_date": end or "",
                    "position": rest[:250],
                    "description": desc[:1000],
                }
            )
    segs.sort(key=sort_key)
    # chain: empty end = next distinct start
    for i, seg in enumerate(segs):
        if not seg["end_date"]:
            nxt = segs[i + 1]["start_date"] if i + 1 < len(segs) else "至今"
            seg["end_date"] = nxt
    # drop identity fragments and family/birth sentences leaked into the timeline
    fam = re.compile(r"父亲|母亲|岳父|之子|其子|出生|诞生|逝世|去世")
    out = []
    for s in segs:
        if is_identity(s["position"]):
            continue
        if fam.search(s["position"][:30]):
            continue
        out.append(s)
    return out


def sort_key(seg: dict):
    m = re.match(r"(\d{4})(?:\.(\d{1,2}))?", str(seg.get("start_date", "")))
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)


ETH_RE = re.compile(
    r"(汉族|回族|满族|藏族|蒙古族|维吾尔族|苗族|彝族|壮族|布依族|朝鲜族|侗族|瑶族|白族|土家族|哈尼族|哈萨克族|傣族|黎族|傈僳族|佤族|畲族|高山族|拉祜族|水族|东乡族|纳西族|景颇族|柯尔克孜族|土族|达斡尔族|仫佬族|羌族|布朗族|撒拉族|毛南族|仡佬族|锡伯族|阿昌族|普米族|塔吉克族|怒族|乌孜别克族|俄罗斯族|鄂温克族|德昂族|保安族|裕固族|京族|塔塔尔族|独龙族|鄂伦春族|赫哲族|门巴族|珞巴族|基诺族)"
)
NATIVE_RE = re.compile(r"，\s*([\u4e00-\u9fa5·]{2,15}?)(?:省|市|自治区|特别行政区)?(?:人|籍贯|祖籍)[，。]")
NATIVE_RE2 = re.compile(r"\d{4}\s*年\s*\d{1,2}\s*月生\s*[,，]\s*([\u4e00-\u9fa5·]{2,15}?)人")
NATIVE_RE3 = re.compile(r"籍贯[:：]?\s*([\u4e00-\u9fa5·]{2,15}?)[，。]")
NATIVE_BAD = re.compile(r"^(中国共产党|中华人民共和国|政治|军人|官员|外交)")


def find_native(head: str) -> str:
    for pat in (NATIVE_RE, NATIVE_RE2, NATIVE_RE3):
        for m in pat.finditer(head):
            v = m.group(1)
            if v and not NATIVE_BAD.search(v):
                return v
    return ""
CAREER_VERB = re.compile(r"任|担任|调任|进入|当选|晋升|学习|毕业|参加工作|任职|入伍|服役|就读|考取|任教|工作")
EDU_RE = re.compile(
    r"(?:获|取得|授)?([^，。\n]{2,40}?(?:博士|硕士|学士)[^，。\n]{0,6}学位)|"
    r"([^，。\n]{0,30}?(?:大学|学院|党校|学校|研究院|中央党校)[^，。\n]{0,25}?(?:毕业|结业|研究生|进修))|"
    r"(研究生[^，。\n]{0,15}学历|大学[^，。\n]{0,12}学历|在职[^，。\n]{0,20}学历|中央党校[^，。\n]{0,20})"
)


def profile_from_text(cleaned: str) -> dict:
    head = cleaned[:4000].replace("\n", "，")
    out = {"ethnicity": "", "native_place": "", "education": ""}
    m = ETH_RE.search(head)
    out["ethnicity"] = m.group(1) if m else "汉族"
    out["native_place"] = find_native(head)
    seen: list[str] = []
    for m in EDU_RE.finditer(cleaned[:4000]):
        frag = tidy(m.group(0))[:120]
        if frag and frag not in seen:
            seen.append(frag)
        if len(seen) >= 2:
            break
    out["education"] = "；".join(seen)
    return out


if __name__ == "__main__":
    _setup_stdout()
    for arg in sys.argv[1:]:
        raw = Path(arg).read_text(encoding="utf-8")
        cleaned = clean_wikitext(raw)
        print("=" * 30, Path(arg).name)
        print("PROFILE:", profile_from_text(cleaned))
        segs = parse_careers(cleaned)
        for s in segs:
            print(f"  [{s['start_date']} — {s['end_date']}] {s['position']}")
        print()
