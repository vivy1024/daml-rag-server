"""
batch31: 训练容量理论深化 — 每肌群具体训练建议

程序化生成：每个主要肌群的训练建议（最佳动作、容量、频率、常见错误）
"""

from chunk_utils import make_chunk
from graph_alignment import normalize_muscles
from typing import List, Dict
import json, os

MUSCLE_TRAINING = [
    {"muscle": "胸部", "graph": "胸部",
     "best_exercises": "杠铃卧推（力量）、哑铃卧推（ROM）、绳索夹胸（孤立）、上斜推（上胸）",
     "volume": "每周12-20组，分2-3次",
     "frequency": "每周2-3次",
     "rep_ranges": "力量：4-6次；肌肥大：8-12次；泵感：12-20次",
     "common_mistakes": "只做平板卧推忽略上斜|推拉比失衡（推太多拉太少）|不做飞鸟类孤立动作|肩胛骨不后缩",
     "tips": "上斜30°是上胸最佳角度；哑铃比杠铃ROM更大；绳索夹胸在收缩位张力最大；卧推时肩胛骨后缩保护肩关节"},

    {"muscle": "背部", "graph": "背阔肌",
     "best_exercises": "引体向上（宽度）、杠铃划船（厚度）、坐姿划船（厚度）、直臂下拉（孤立）",
     "volume": "每周14-22组（宽度+厚度分开计算），分2-3次",
     "frequency": "每周2-3次",
     "rep_ranges": "引体/划船：6-10次；下拉/孤立：10-15次",
     "common_mistakes": "只做下拉不做引体|手臂主导背部不发力|不做全ROM（不完全伸展）|忽略后三角肌",
     "tips": "背部训练的关键是'感受'——用肘部拉而非手；全ROM很重要（完全伸展到完全收缩）；面拉每次训练都做"},

    {"muscle": "肩部（三角肌）", "graph": "三角肌中束",
     "best_exercises": "过头推举（前+中束）、侧平举（中束）、面拉（后束）、反向飞鸟（后束）",
     "volume": "前束：6-8组（从推举获得大量间接刺激）；中束：14-20组；后束：12-16组",
     "frequency": "中束可以每天练（高频低量）；前束每周2次；后束每周2-3次",
     "rep_ranges": "推举：6-10次；侧平举：12-20次；面拉：15-25次",
     "common_mistakes": "前束过度训练（卧推已经练很多）|忽略后束|侧平举重量过大借力|不做面拉",
     "tips": "中束决定肩宽，是视觉效果最大的肌群；侧平举轻重量高次数效果好；后束薄弱=圆肩+肩伤风险"},

    {"muscle": "肱二头肌", "graph": "肱二头肌",
     "best_exercises": "杠铃弯举（整体）、上斜弯举（长头）、牧师凳弯举（短头）、锤式弯举（肱桡肌）",
     "volume": "每周10-14组，分2-3次",
     "frequency": "每周2-3次",
     "rep_ranges": "杠铃弯举：6-10次；哑铃变体：10-15次",
     "common_mistakes": "重量过大借力摆动|不做全ROM|只做一种弯举|忽略旋后（掌心朝上）",
     "tips": "上斜弯举拉伸长头最多（肩伸展位）；牧师凳收缩短头最多（肩屈曲位）；二头肌从拉类复合动作获得大量间接刺激"},

    {"muscle": "肱三头肌", "graph": "肱三头肌",
     "best_exercises": "窄距卧推（整体+力量）、过头臂屈伸（长头）、绳索下压（外侧头）、Dips（整体）",
     "volume": "每周8-12组（从推举获得间接刺激），分2-3次",
     "frequency": "每周2-3次",
     "rep_ranges": "窄距卧推：6-8次；过头臂屈伸：8-12次；下压：10-15次",
     "common_mistakes": "忽略长头（只做下压）|不做过头动作|肘关节不完全伸直|重量过大肘痛",
     "tips": "长头是最大的头（50%+体积），需要过头位置拉伸；三头肌从所有推举动作获得大量间接刺激；肘痛时减少容量"},

    {"muscle": "股四头肌", "graph": "股四头肌",
     "best_exercises": "杠铃深蹲（整体）、前蹲（更多股四）、腿举（高SFR）、腿屈伸（孤立）",
     "volume": "每周12-18组，分2-3次",
     "frequency": "每周2-3次",
     "rep_ranges": "深蹲：4-8次；腿举：8-12次；腿屈伸：12-15次",
     "common_mistakes": "深蹲深度不够|忽略单腿训练|只做深蹲不做孤立|膝盖内扣",
     "tips": "全ROM深蹲（大腿低于平行）对股四头肌刺激最大；腿屈伸最后30°VMO激活最大；前蹲比后蹲更多股四头肌"},

    {"muscle": "臀大肌", "graph": "臀部",
     "best_exercises": "臀推（缩短位）、深蹲（拉长位）、RDL（拉长位）、保加利亚分腿蹲（单侧）",
     "volume": "每周8-12组（优先发展时可到16-20组），分2-3次",
     "frequency": "每周2-4次",
     "rep_ranges": "臀推：8-12次；深蹲：6-8次；RDL：8-10次",
     "common_mistakes": "臀肌激活不足（腘绳肌/下背代偿）|不做臀推|只做深蹲|不做激活热身",
     "tips": "臀推是臀部缩短位力量的最佳动作；深蹲/RDL是拉长位力量；两者互补；训练前做臀肌激活（蚌式+臀桥）"},

    {"muscle": "腘绳肌", "graph": "腿后肌群",
     "best_exercises": "罗马尼亚硬拉（拉长位）、北欧腿弯举（离心）、腿弯举（孤立）、Good Morning",
     "volume": "每周10-16组，分2次",
     "frequency": "每周2次（恢复需求大）",
     "rep_ranges": "RDL：6-10次；北欧：6-8次；腿弯举：10-12次",
     "common_mistakes": "只做腿弯举忽略RDL|不做离心训练（北欧）|H:Q比失衡|忽略内侧腘绳肌",
     "tips": "北欧腿弯举是预防拉伤的金标准；RDL训练拉长位力量；脚尖方向影响内外侧激活；冲刺运动员必须重视腘绳肌离心力量"},

    {"muscle": "小腿", "graph": "小腿",
     "best_exercises": "站姿提踵（腓肠肌）、坐姿提踵（比目鱼肌）、单腿提踵（纠正不对称）",
     "volume": "每周12-16组，分3-4次",
     "frequency": "每周3-4次（小腿耐受高频率）",
     "rep_ranges": "站姿：10-15次；坐姿：15-20次",
     "common_mistakes": "ROM不完整（不下沉/不踮到最高）|频率太低|只做站姿忽略坐姿|速度过快弹跳",
     "tips": "小腿日常承受体重负荷，需要高次数+高频率才能刺激生长；全ROM是关键（充分拉伸+充分收缩）；直膝=腓肠肌，屈膝=比目鱼肌"},

    {"muscle": "核心（腹肌）", "graph": "腹直肌",
     "best_exercises": "悬垂举腿（下腹）、Ab Wheel（抗伸展）、Pallof Press（抗旋转）、Cable Crunch（上腹）",
     "volume": "每周8-12组直接训练（复合动作提供大量间接刺激），分3-4次",
     "frequency": "每周3-4次（核心恢复快）",
     "rep_ranges": "悬垂举腿：8-15次；Ab Wheel：8-12次；Pallof：10-12次每侧",
     "common_mistakes": "只做卷腹|忽略抗运动训练|追求高次数而非渐进超负荷|忽略腹斜肌",
     "tips": "六块腹肌的可见度主要取决于体脂率（男<12%，女<20%）；核心训练应包含抗伸展+抗旋转+抗侧屈；深蹲/硬拉本身就是强大的核心训练"},
]


def generate_batch31() -> List[Dict]:
    chunks = []
    for m in MUSCLE_TRAINING:
        content = f"## {m['muscle']}训练完全指南\n\n"
        content += f"**最佳动作**：{m['best_exercises']}\n\n"
        content += f"**每周容量**：{m['volume']}\n\n"
        content += f"**训练频率**：{m['frequency']}\n\n"
        content += f"**次数范围**：{m['rep_ranges']}\n\n"
        content += f"**常见错误**：\n"
        for err in m['common_mistakes'].split('|'):
            content += f"- {err}\n"
        content += f"\n**训练提示**：{m['tips']}"

        muscles = normalize_muscles([m['graph']])
        chunks.append(make_chunk(
            category="methodology",
            subcategory="muscle_training_guide",
            title=f"{m['muscle']}训练完全指南 — 动作/容量/频率",
            content=content,
            keywords=[m['muscle'], "训练指南", "容量", "频率", "动作选择"],
            related_muscles=muscles,
        ))
    return chunks


if __name__ == "__main__":
    chunks = generate_batch31()
    print(f"生成 {len(chunks)} 个肌群训练指南 chunks")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "batch31.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print("已保存到 output/batch31.json")
