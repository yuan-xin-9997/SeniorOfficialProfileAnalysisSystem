# -*- coding: utf-8 -*-
"""对比新旧种子的 current_position 质量（临时校验脚本）。"""
import json
import re

old = {o["name"]: o for o in json.load(open("../../src_gpt5.6/data/seed/officials_20th_cc.json"))}
new = {o["name"]: o for o in json.load(open("seed_officials_20th_cc.json"))}

ROLE = ("书记", "部长", "局长", "主席", "省长", "市长", "董事长", "总经理", "主任", "委员长",
        "院长", "校长", "政委", "司令员", "行长", "社长", "总编辑", "总监", "理事长", "会长",
        "副会长", "副主席", "副部长", "副省长", "副市长", "副主任", "馆长", "台长", "秘书长",
        "检察长", "队长", "专员", "州长", "盟长", "常委", "委员", "秘书", "助理", "组长",
        "知青", "学习", "研究", "干部", "审计长", "参事", "科长", "处长", "司长", "厅长")
NEWS = re.compile(
    r"率领|抵达|出席|会见|陪同|代表团|庆祝大会|骨灰|撒入|主持召开|考察|调研|慰问|发表|讲话"
    r"|的提法|这段时间|也不是|开始使用|罕见|陪护|当选|写入|爆炸|事故|排放比|卸任|接任|履新|辞去|被免|免职")


def bad(p: str) -> bool:
    return bool(p) and (len(p) > 60 or bool(NEWS.search(p)) or not any(w in p for w in ROLE))


changed = [(n, old[n]["current_position"], new[n]["current_position"]) for n in new
           if old[n]["current_position"] != new[n]["current_position"]]
still_bad = [n for n in new if bad(new[n]["current_position"])]
empty = [n for n in new if not new[n]["current_position"]]
print(f"current_position 变化: {len(changed)} 人 | 修复后仍可疑: {len(still_bad)} | 现任为空: {len(empty)}")
if still_bad:
    print("仍可疑:", [(n, new[n]["current_position"][:40]) for n in still_bad[:10]])
if empty:
    print("为空:", empty[:10])
for n in ("蔡奇", "胡春华", "马兴瑞", "王文全", "丁薛祥", "习近平", "李强", "王小洪"):
    print(f"  {n}: {new[n]['current_position'][:56]}")
print()
print("变化样例:")
for n, o, w in changed[:8]:
    print(f"  {n}: {o[:36]!r} -> {w[:44]!r}")
