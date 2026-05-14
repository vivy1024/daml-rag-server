"""batch42: 更多动作教学 — 肩部/手臂孤立动作"""
from chunk_utils import make_chunk
from graph_alignment import normalize_muscles
from typing import List, Dict
import json, os

EXERCISES = [
    {"name": "前平举(Front Raise)", "target": "三角肌前束", "secondary": "上胸",
     "steps": "1.双手持哑铃于大腿前方\n2.掌心朝后或朝下\n3.手臂微屈固定\n4.向前抬起到肩膀高度（不超过）\n5.控制下放",
     "breathing": "抬起呼气，下放吸气", "errors": "借力摆动|抬过肩膀|肘完全伸直|速度过快",
     "tips": "前三角肌从推举动作获得大量间接刺激，通常不需要大量孤立训练。如果做：轻重量高次数(15-20)即可。交替做减少借力。",
     "muscles": ["三角肌前束", "上胸"]},

    {"name": "锤式弯举(Hammer Curl)", "target": "肱桡肌", "secondary": "肱二头肌",
     "steps": "1.双手持哑铃于身体两侧\n2.掌心相对（中立握）\n3.上臂贴身固定\n4.屈肘弯举（保持中立握不旋转）\n5.顶部挤压\n6.控制下放",
     "breathing": "弯举呼气，下放吸气", "errors": "上臂摆动|手腕旋转（变成标准弯举）|身体后仰|不完全伸直",
     "tips": "中立握=肱桡肌力矩臂最大；是前臂外观的主要贡献者；可以交替做或同时做；绳索锤式弯举全程张力更好。",
     "muscles": ["前臂肌群", "肱二头肌"]},

    {"name": "反向弯举(Reverse Curl)", "target": "肱桡肌+腕伸肌", "secondary": "肱二头肌",
     "steps": "1.正握（掌心朝下）握杠铃/EZ杠\n2.握距与肩同宽\n3.上臂贴身固定\n4.屈肘弯举\n5.顶部停顿\n6.控制下放",
     "breathing": "弯举呼气，下放吸气", "errors": "握距太宽/太窄|上臂移动|重量过大（腕关节压力）|速度过快",
     "tips": "是前臂伸肌群的最佳训练；预防网球肘（强化腕伸肌）；EZ杠比直杠对腕关节更友好；通常用比标准弯举轻30-40%的重量。",
     "muscles": ["前臂肌群", "腕伸肌群", "肱二头肌"]},

    {"name": "Zottman弯举", "target": "肱二头肌+肱桡肌", "secondary": "腕伸肌",
     "steps": "1.双手持哑铃，掌心朝前（旋后）\n2.标准弯举到顶部\n3.顶部旋转手腕（掌心朝下=旋前）\n4.以反握姿势缓慢下放（离心）\n5.底部再旋转回掌心朝前\n6.重复",
     "breathing": "弯举呼气，下放吸气", "errors": "旋转时肘移动|下放太快（错过离心）|重量过大|旋转不完整",
     "tips": "一个动作训练二头肌（向心）+前臂（离心）；是最高效的手臂动作之一；离心阶段（反握下放）是关键——要慢（3秒）。",
     "muscles": ["肱二头肌", "前臂肌群", "腕伸肌群"]},

    {"name": "绳索侧平举(单臂)", "target": "三角肌中束", "secondary": "上斜方肌",
     "steps": "1.侧对低位绳索\n2.远侧手握D把（绳索从身前经过）\n3.身体可略向绳索侧倾斜（增加底部张力）\n4.肘微屈固定\n5.向侧方抬起到肩膀高度\n6.顶部停顿1秒\n7.控制下放",
     "breathing": "抬起呼气，下放吸气", "errors": "耸肩|抬过肩膀|身体摆动|肘角度变化",
     "tips": "绳索版本在顶部张力最大（vs哑铃在中间最大）；身体略倾斜=底部也有张力=全程有效ROM更大；是中束训练的最佳变体。",
     "muscles": ["三角肌中束", "上斜方肌"]},

    {"name": "上斜弯举(Incline Curl)", "target": "肱二头肌长头", "secondary": "肱桡肌",
     "steps": "1.坐在45-60°上斜凳上\n2.双手持哑铃自然下垂（手臂在身体后方）\n3.掌心朝前\n4.屈肘弯举（上臂不前移）\n5.顶部挤压\n6.控制下放到完全伸直",
     "breathing": "弯举呼气，下放吸气", "errors": "上臂前移（减少长头拉伸）|凳角度太直|不完全伸直|借力摆动",
     "tips": "肩伸展位（手臂在身后）=长头被最大拉伸=长头最佳动作；是二头肌'峰值'（长头）的关键训练；角度越低（更平）拉伸越大但也越难。",
     "muscles": ["肱二头肌长头", "肱二头肌"]},

    {"name": "牧师凳弯举(Preacher Curl)", "target": "肱二头肌短头", "secondary": "肱桡肌",
     "steps": "1.坐在牧师凳前，上臂放在斜面上\n2.腋窝贴紧凳子顶部\n3.握EZ杠或哑铃\n4.从完全伸直位屈肘弯举\n5.顶部挤压\n6.控制下放（不要完全锁死肘关节底部）",
     "breathing": "弯举呼气，下放吸气", "errors": "腋窝离开凳面（借力）|底部完全锁死（肘关节压力）|重量过大|速度过快",
     "tips": "肩屈曲位（手臂在前方）=短头缩短更多=短头最佳动作；是最严格的弯举变体（无法借力）；底部不要完全伸直（保护肘关节）。",
     "muscles": ["肱二头肌短头", "肱二头肌"]},

    {"name": "绳索过头臂屈伸", "target": "肱三头肌长头", "secondary": "肱三头肌",
     "steps": "1.背对低位绳索\n2.双手握绳索把手于头后方\n3.前跨一步，身体略前倾\n4.上臂贴近耳朵，肘朝天\n5.伸肘将绳索向前上方推出\n6.顶部挤压三头肌\n7.控制回放到头后方",
     "breathing": "伸肘呼气，屈肘吸气", "errors": "肘关节外展|上臂前后移动|腰椎过伸|重量过大",
     "tips": "过头位置=长头最大拉伸=长头最佳绳索动作；绳索提供全程恒定张力（vs哑铃只有部分ROM有张力）；可以单臂做增加ROM。",
     "muscles": ["三头肌长头", "肱三头肌"]},

    {"name": "Kickback(哑铃臂屈伸)", "target": "肱三头肌", "secondary": "肱三头肌外侧头",
     "steps": "1.一手一膝撑凳（类似单臂划船起始位）\n2.另一手持哑铃，上臂平行地面\n3.肘关节固定在身体侧面\n4.伸肘将哑铃向后推直到手臂完全伸直\n5.顶部挤压1-2秒\n6.控制屈肘回放",
     "breathing": "伸肘呼气，屈肘吸气", "errors": "上臂下垂（不平行地面）|甩动借力|不完全伸直|肘关节移动",
     "tips": "在完全伸直位张力最大（缩短位训练）；适合轻重量高次数收尾；绳索版本全程张力更好；不适合大重量（杠杆不利）。",
     "muscles": ["肱三头肌", "肱三头肌外侧头"]},

    {"name": "直立划船(Upright Row)", "target": "三角肌中束+上斜方肌", "secondary": "肱二头肌",
     "steps": "1.双手正握杠铃/哑铃，窄于肩宽\n2.杠铃贴身体前方\n3.肘部向上向外拉起\n4.拉到肘部与肩膀同高（不超过）\n5.控制下放",
     "breathing": "上拉呼气，下放吸气", "errors": "拉得太高（肩峰撞击风险）|握距太窄|身体摆动|速度过快",
     "tips": "争议动作：窄握+拉过肩=肩峰撞击风险高。安全做法：宽握（肩宽或略宽）+只拉到肘与肩平齐。哑铃版本比杠铃更安全（自由路径）。如果肩痛→用侧平举替代。",
     "muscles": ["三角肌中束", "上斜方肌", "肱二头肌"]},
]

def generate_batch42() -> List[Dict]:
    chunks = []
    for ex in EXERCISES:
        content = "## {}\n\n**目标肌群**：{}\n**辅助肌群**：{}\n\n**动作要领**：\n{}\n\n**呼吸**：{}\n\n**常见错误**：\n{}\n\n**训练提示**：{}".format(
            ex["name"], ex["target"], ex["secondary"], ex["steps"], ex["breathing"],
            "\n".join(f"- {e}" for e in ex["errors"].split("|")), ex["tips"])
        muscles = normalize_muscles(ex.get("muscles", []))
        chunks.append(make_chunk(
            category="methodology", subcategory="exercise_instruction",
            title=f"{ex['name']} — 动作教学", content=content,
            keywords=[ex["name"], ex["target"]] + ex.get("muscles", [])[:2],
            related_muscles=muscles))
    return chunks

if __name__ == "__main__":
    chunks = generate_batch42()
    print(f"生成 {len(chunks)} chunks")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "batch42.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print("已保存到 output/batch42.json")
