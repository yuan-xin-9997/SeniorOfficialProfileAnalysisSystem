# -*- coding: utf-8 -*-
"""履历专用解析器单元测试（维基百科 DOM 解析 + 官媒通用解析 + 日期引擎）。"""
from __future__ import annotations

from app.backend.services.official.resume_parsers import (
    is_wikipedia_url,
    parse_resume,
)
from app.backend.services.official.resume_parsers.dateparse import find_ranges, parse_career_text

# ---------- 日期区间引擎 ----------


def test_find_ranges_formats():
    assert find_ranges("1973－1975年 福建插队") == [("1973", "1975", 0, 10)]
    assert find_ranges("2018年5月24日—2023年7月4日 任常务副秘书长")[0][:2] == ("2018.05", "2023.07")
    assert find_ranges("1978.03－1983.08 任干部")[0][:2] == ("1978.03", "1983.08")
    assert find_ranges("2015年4月至今 任常务副主任")[0][:2] == ("2015.04", "至今")
    assert find_ranges("1994年到1997年 学习")[0][:2] == ("1994", "1997")


def test_parse_career_text_chain_and_noise():
    text = "\n".join(
        [
            "1973－1975年　福建省永安县西洋公社插队知青",
            "1975－1978年　福建师范大学政教系政教专业学习",
            "1978－1983年　福建师范大学党委办公室干部",
            "1983年至今　任省团委书记",
            "版权所有 2001－2026年",
            "2025年12月5日 星期四",
        ]
    )
    segs = parse_career_text(text, "蔡奇")
    positions = [s["position"] for s in segs]
    assert positions == [
        "福建省永安县西洋公社插队知青",
        "福建师范大学政教系政教专业学习",
        "福建师范大学党委办公室干部",
        "省团委书记",
    ]
    # 链式补全：前一段结束=后一段开始
    assert [s["end_date"] for s in segs] == ["1975", "1978", "1983", "至今"]


def test_parse_career_text_strips_name_and_verb():
    text = "1983年，蔡奇任中共福建省委办公厅综合处副处长。1994年3月，蔡奇获得外放机会，挂职担任中共三明市委副书记。"
    segs = parse_career_text(text, "蔡奇")
    assert segs[0]["position"] == "中共福建省委办公厅综合处副处长"
    assert segs[0]["start_date"] == "1983"
    assert segs[1]["start_date"] == "1994.03"


# ---------- 维基百科 DOM 解析（Vector 新版皮肤）----------

WIKI_SECTIONS_HTML = """
<html><body><div id="mw-content-text">
  <p>蔡奇，男，1955年12月生，福建尤溪人，中华人民共和国政治人物。</p>
  <div class="mw-heading mw-heading2"><h2 id="生平">生平<span class="mw-editsection">[编辑]</span></h2></div>
  <div class="mw-heading mw-heading3"><h3 id="福建任职">福建任职</h3></div>
  <p>1983年，蔡奇任中共福建省委办公厅综合处副处长。</p>
  <p>1994年3月，蔡奇挂职担任中共三明市委副书记。</p>
  <div class="mw-heading mw-heading3"><h3 id="主政北京">主政北京</h3></div>
  <p>2017年5月，蔡奇任北京市委书记。</p>
  <div class="mw-heading mw-heading2"><h2 id="参考文献">参考文献</h2></div>
  <p>1999年，《某某志》记载了大量与履历无关的内容。</p>
</div></body></html>
"""


def test_wikipedia_section_parser():
    segs = parse_resume(WIKI_SECTIONS_HTML, "https://zh.wikipedia.org/wiki/%E8%94%A1%E5%A5%87", "蔡奇")
    assert [s["position"] for s in segs] == [
        "中共福建省委办公厅综合处副处长",
        "中共三明市委副书记",
        "北京市委书记",
    ]
    assert [s["start_date"] for s in segs] == ["1983", "1994.03", "2017.05"]
    assert segs[-1]["end_date"] == "至今"


WIKI_INFOBOX_HTML = """
<html><body><div id="mw-content-text">
  <p>丁学东，男，汉族，1960年2月生，江苏常州人，政治人物。</p>
  <table class="infobox vcard">
    <tr><th>丁学东</th></tr>
    <tr><td colspan="2">中华人民共和国国务院常务副秘书长</td></tr>
    <tr><td>任期 2018年5月24日—2023年7月4日</td></tr>
    <tr><th>总理</th><td>李克强 → 李强</td></tr>
    <tr><th>前任</th><td>肖捷</td></tr>
    <tr><th>继任</th><td>王志军</td></tr>
    <tr><td colspan="2">中国投资有限责任公司 董事长</td></tr>
    <tr><td>任期 2013年7月—2017年2月</td></tr>
    <tr><th>前任</th><td>楼继伟</td></tr>
    <tr><th>出生</th><td>1960年2月（66歲） 江苏省 常州市</td></tr>
  </table>
</div></body></html>
"""


def test_wikipedia_infobox_parser():
    segs = parse_resume(WIKI_INFOBOX_HTML, "https://zh.wikipedia.org/wiki/%E4%B8%81%E5%AD%A6%E4%B8%9C", "丁学东")
    # 按开始时间排序；信息框兜底时职务标题同时写入 organization 和 position
    assert [(s["start_date"], s["end_date"]) for s in segs] == [
        ("2013.07", "2017.02"),
        ("2018.05", "2023.07"),
    ]
    assert segs[1]["position"] == "中华人民共和国国务院常务副秘书长"
    assert segs[1]["organization"] == segs[1]["position"]
    # 前任/继任/出生等信息框噪音行不产生履历
    assert all("楼继伟" not in s["position"] for s in segs)


# ---------- 官媒通用解析器 ----------

GOV_MEDIA_HTML = """
<html><body>
  <div class="nav"><ul><li>2025年12月5日 星期四</li><li>网站首页</li></ul></div>
  <div class="article">
    <p>蔡奇，男，汉族，1955年12月生，福建尤溪人，1973年3月参加工作，1975年8月加入中国共产党，
    福建师范大学经济法律学院政治经济学专业毕业，在职研究生学历，经济学博士学位。</p>
    <p>现任中央政治局委员，北京市委书记。</p>
    <p>1973－1975年　福建省永安县西洋公社插队知青</p>
    <p>1975－1978年　福建师范大学政教系政教专业学习</p>
    <p>1983－1987年　福建省委办公厅综合处干部、副处长</p>
    <p>2017年5月－　北京市委书记</p>
  </div>
  <footer><p>版权所有：2001－2026年</p></footer>
</body></html>
"""


def test_gov_media_parser():
    url = "http://www.locpg.gov.cn/zt/2017-10/25/c_129726760.htm"
    segs = parse_resume(GOV_MEDIA_HTML, url, "蔡奇")
    assert is_wikipedia_url(url) is False
    positions = [s["position"] for s in segs]
    assert "福建省永安县西洋公社插队知青" in positions
    assert "福建师范大学政教系政教专业学习" in positions
    assert "福建省委办公厅综合处干部、副处长" in positions
    assert "参加工作" in positions
    # 真实页面中“入党+学历”常在同一段落，作为一条经历合并抽出
    assert any(p.startswith("加入中国共产党") for p in positions)
    # 导航与版权噪音不产生履历
    assert all("星期" not in p and "版权" not in p for p in positions)
    first = next(s for s in segs if s["position"] == "福建省永安县西洋公社插队知青")
    assert (first["start_date"], first["end_date"]) == ("1973", "1975")


def test_parser_dispatch_and_empty_result():
    assert is_wikipedia_url("https://zh.wikipedia.org/wiki/X") is True
    assert is_wikipedia_url("https://zh.m.wikipedia.org/wiki/X") is True
    assert is_wikipedia_url("http://www.locpg.gov.cn/x.htm") is False
    # 无日期内容的页面返回空列表（刷新任务据此判定失败并保留原履历）
    assert parse_resume("<html><body><p>无法解析的页面</p></body></html>", "http://x.gov.cn/a.html", "张三") == []
