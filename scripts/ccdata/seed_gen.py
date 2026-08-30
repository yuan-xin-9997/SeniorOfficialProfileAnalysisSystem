# -*- coding: utf-8 -*-
"""Generate the final seed JSON (OfficialCreate shape) from roster + profiles.

Output: seed_officials_20th_cc.json
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DIR = Path(__file__).parent

T2S = {"張玉卓": "张玉卓", "王庭凱": "王庭凯", "劉敬楨": "刘敬桢"}

LEVEL_MAP = {
    "正国": "国家级正职",
    "副国": "国家级副职",
    "正部": "正省部级",
    "副部": "副省部级",
    "正厅": "正厅局级",
    "副厅": "副厅局级",
    "正处": "正县处级",
    "副科": "副乡科级",
}

# 二十届中央政治局常委与委员公开名单（2022.10 二十届一中全会选出）。
PSC_NAMES = {"习近平", "李强", "赵乐际", "王沪宁", "蔡奇", "丁薛祥", "李希"}
POLITBURO_NAMES = PSC_NAMES | {
    "马兴瑞", "王毅", "尹力", "石泰峰", "刘国中", "李干杰", "李书磊", "李鸿忠",
    "何卫东", "何立峰", "张国清", "张又侠", "陈文清", "陈吉宁", "陈敏尔", "袁家军", "黄坤明",
}


def derive_party_role(name: str, is_member: bool) -> str:
    if name in PSC_NAMES:
        return "中央政治局常委"
    if name in POLITBURO_NAMES:
        return "中央政治局委员"
    return "中央委员" if is_member else "中央候补委员"

ROLE_WORDS = (
    "党委书记", "副书记", "书记", "部长", "局长", "主席", "省长", "市长", "董事长",
    "总经理", "主任", "委员长", "院长", "校长", "政委", "司令员", "院长", "行长",
    "社长", "总编辑", "总监", "理事长", "副会长", "副主席", "副部长", "副省长",
    "副市长", "副总经理", "副主任", "董事长", "馆长", "台长", "总会计师", "总经济师",
    "总工程师", "董事长", "秘书长", "审判长", "检察长", "局长", "队长", "科长",
    "组长", "委员", "常委", "处长", "司长", "厅长", "州长", "专员", "审计长", "参事",
)


def display_name(name: str) -> str:
    name = T2S.get(name, name)
    return re.sub(r"\s*[（(].*?[)）]\s*$", "", name).strip()


def derive_organization(pos: str) -> str:
    for w in ROLE_WORDS:
        i = pos.find(w)
        if i > 0:
            org = pos[:i].strip("，,、和与。")
            org = re.sub(r"^(中共中央|中共|中华人民共和国|国务院|中央)?", "", org) or pos[:i]
            # keep a meaningful org (don't return empty)
            org2 = pos[:i].strip("，,、和与。")
            return org2[:60]
    return ""


def current_from_roster(lines: list[str]) -> tuple[str, str]:
    """Return (current_position, '') from the last roster line.

    名单页的行往往不带日期（如“中央政治局常委、中央书记处书记”），
    这些正是干净的现任职务，必须以 allow_undated=True 解析。
    """
    if not lines:
        return "", ""
    for line in reversed(lines):
        seg = parse_roster_line(line, allow_undated=True)
        if seg and seg["position"]:
            # if the segment has an explicit end date, it is the last held post
            return seg["position"], ""
    return "", ""


# 新闻叙事特征：命中即不是“现任职务”而是事件报道句。
NEWS_PATTERN = re.compile(
    r"率领|抵达|出席|会见|陪同|代表团|庆祝大会|骨灰|撒入|主持召开|考察|调研|慰问|发表|讲话"
    r"|的提法|这段时间|也不是|开始使用|罕见|陪护|当选|写入|爆炸|事故|排放比|减税|增资"
    r"|卸任|接任|履新|辞去|被免|免职|接受纪律审查|监察调查"
)


def looks_like_position(text: str) -> bool:
    """现任职务质量门控：短小、含职务词、不含新闻叙事特征。"""
    if not text:
        return False
    if len(text) > 60:
        return False
    if NEWS_PATTERN.search(text):
        return False
    return any(w in text for w in ROLE_WORDS)


def parse_roster_line(line: str, allow_undated: bool = False) -> dict | None:
    line = line.strip()
    if not line:
        return None
    m = re.match(
        r"^(?:(\d{4})(?:\.(\d{1,2}))?)?\s*—\s*(?:(\d{4})(?:\.(\d{1,2}))?)?\s*(.+)$", line
    )
    if not m:
        m2 = re.match(r"^(\d{4})(?:\.(\d{1,2}))?\s+(.+)$", line)
        if m2:
            y1, m1, text = m2.groups()
            return {
                "start_date": f"{y1}.{int(m1):02d}" if m1 else y1,
                "end_date": "至今",
                "position": text[:250],
                "description": "（据二十届中央委员会名单页）",
            }
        if allow_undated and re.match(r"^[^\d—]", line):
            return {
                "start_date": "2022.10",
                "end_date": "至今",
                "position": line[:250],
                "description": "（据二十届中央委员会名单页，当选时任职务）",
            }
        return None
    y1, m1, y2, m2, text = m.groups()
    if y1:
        start = f"{y1}.{int(m1):02d}" if m1 else y1
    else:
        start = "2022.10"  # unknown start -> elected-at-congress approximation
    if y2:
        end = f"{y2}.{int(m2):02d}" if m2 else y2
    else:
        end = "至今"
    return {"start_date": start, "end_date": end, "position": text[:250], "description": "（据二十届中央委员会名单页）"}


def seg_key(s: dict) -> tuple:
    return (str(s.get("start_date", "")), str(s.get("position", ""))[:40])


def build_record(p: dict, is_member: bool, promoted: bool) -> dict:
    name = display_name(p["name"])
    level = p.get("level", "")
    note = p.get("note", "")
    struck = p.get("struck", False) or any(k in note for k in ("开除", "双开", "被查"))
    died = "逝世" in note or "去世" in note

    status = "已故" if died else ("落马" if struck else "在任")

    tags = []
    if is_member:
        tags.append("中共二十届中央委员")
        if promoted:
            tags.append("递补当选")
    else:
        tags.append("中共二十届中央候补委员")
    if level in ("正国", "副国"):
        tags.append("党和国家领导人")
    if "中国科学院院士" in note:
        tags.append("中国科学院院士")
    elif "中国工程院院士" in note:
        tags.append("中国工程院院士")
    if status == "落马":
        tags.append("落马")

    current_position, _ = current_from_roster(p.get("roster_positions", []))
    if not looks_like_position(current_position):
        current_position = ""

    membership = "委员" if is_member else "候补委员"
    if promoted and not is_member:
        membership = "委员（递补）"
    verb = "现任"
    if status == "落马":
        verb = "原任"
    elif status == "已故":
        verb = "生前任"
    suffix = f"，{verb}{current_position}" if current_position else ""
    summary = f"中共二十届中央{membership}{suffix}。"

    careers = []
    seen = set()
    for s in p["careers"]:
        k = seg_key(s)
        if k in seen:
            continue
        seen.add(k)
        careers.append(
            {
                "start_date": s.get("start_date", ""),
                "end_date": s.get("end_date", "") or "",
                "organization": "",
                "position": (s.get("position") or "")[:250],
                "location": "",
                "administrative_rank": "",
                "description": (s.get("description") or "")[:1000],
                "sort_order": 0,
            }
        )
    if not careers:
        for line in p.get("roster_positions", []):
            seg = parse_roster_line(line, allow_undated=True)
            if seg and seg["position"]:
                k = seg_key(seg)
                if k in seen:
                    continue
                seen.add(k)
                careers.append(
                    {
                        "start_date": seg["start_date"],
                        "end_date": seg["end_date"],
                        "organization": "",
                        "position": seg["position"][:250],
                        "location": "",
                        "administrative_rank": "",
                        "description": seg["description"],
                        "sort_order": 0,
                    }
                )
    # merge roster lines into sparse timelines (article missed recent positions)
    else:
        for line in p.get("roster_positions", []):
            seg = parse_roster_line(line)
            if seg and seg["position"]:
                k = seg_key(seg)
                if k not in seen:
                    seen.add(k)
                    careers.append(
                        {
                            "start_date": seg["start_date"],
                            "end_date": seg["end_date"],
                            "organization": "",
                            "position": seg["position"][:250],
                            "location": "",
                            "administrative_rank": "",
                            "description": seg["description"],
                            "sort_order": 0,
                        }
                    )
    # sort + chain ends + sort_order
    def ym(s: str):
        m = re.match(r"(\d{4})(?:\.(\d{1,2}))?", str(s))
        return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)

    careers.sort(key=lambda s: ym(s["start_date"]))
    for i, s in enumerate(careers):
        s["sort_order"] = i
        if not s["end_date"]:
            s["end_date"] = careers[i + 1]["start_date"] if i + 1 < len(careers) else "至今"

    # 现任职务兜底：从最新履历往回找第一条“像职务”的记录，
    # 宁可留空也不把新闻叙事句碎片当成现任职务。
    if not current_position:
        for seg in reversed(careers):
            if looks_like_position(seg["position"]):
                current_position = seg["position"][:255]
                break

    if not current_position and careers:
        current_position = ""
        suffix = f"，{verb}{current_position}" if current_position else ""
        summary = f"中共二十届中央{membership}{suffix}。"

    birth = p.get("birth", "")
    birth_date = None
    if birth:
        birth_date = birth + "-01"

    org = derive_organization(current_position)
    record = {
        "name": name,
        "gender": p.get("gender", ""),
        "birth_date": birth_date,
        "ethnicity": p.get("ethnicity", ""),
        "native_place": p.get("native_place", "")[:128],
        "education": p.get("education", "")[:255],
        "current_position": current_position[:255],
        "organization": org,
        "administrative_rank": LEVEL_MAP.get(level, level if level not in ("/", "—") else ""),
        "status": status,
        "party_role": derive_party_role(name, is_member),
        "summary": summary[:2000],
        "photo_url": "",
        "source_url": "https://zh.wikipedia.org/wiki/" + p.get("article", ""),
        "tags": tags,
        "careers": careers,
    }
    return record


def main() -> None:
    roster = json.loads((DIR / "roster.json").read_text(encoding="utf-8"))
    profiles = {p["article"]: p for p in json.loads((DIR / "profiles.json").read_text(encoding="utf-8"))}

    coopted_names = {m["name"] for m in roster["members"] if "递补" in m["note"]}
    records = []
    seen_articles = set()
    for m in roster["members"]:
        prof = profiles.get(m["article"])
        if not prof:
            continue
        seen_articles.add(m["article"])
        records.append(build_record(prof, is_member=True, promoted=m["name"] in coopted_names))
    for a in roster["alternates"]:
        if a["article"] in seen_articles:
            continue
        prof = profiles.get(a["article"])
        if not prof:
            continue
        records.append(build_record(prof, is_member=False, promoted=False))

    # disambiguate duplicate display names (e.g. two 王凯) with birth year suffix
    from collections import Counter
    name_counts = Counter(r["name"] for r in records)
    dup_names = {n for n, c in name_counts.items() if c > 1}
    for r in records:
        if r["name"] in dup_names:
            r["name"] = f"{r['name']}（{r['birth_date'][:4]}年生）"
            r["summary"] = r["summary"]

    out = DIR / "seed_officials_20th_cc.json"
    out.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")

    from collections import Counter

    print("records:", len(records))
    print("status:", Counter(r["status"] for r in records))
    print("with careers:", sum(1 for r in records if r["careers"]),
          "| avg careers:", round(sum(len(r["careers"]) for r in records) / len(records), 1))
    print("no careers:", [r["name"] for r in records if not r["careers"]])
    print("tags:", Counter(t for r in records for t in r["tags"]))
    print("ranks:", Counter(r["administrative_rank"] for r in records))


if __name__ == "__main__":
    main()
