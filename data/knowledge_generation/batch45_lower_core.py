"""batch45: 更多动作教学 — 下肢+核心动作"""
from chunk_utils import make_chunk
from graph_alignment import normalize_muscles
from typing import List, Dict
import json, os

EXERCISES = [
    {"name": "西班牙深蹲(Spanish Squat)", "target": "股四头肌", "secondary": "髌腱",
     "steps": "1.弹力带固定在低位（膝盖高度的柱子）\n2.弹力带套在膝盖后方（腘窝）\n3.向后退让弹力带有张力\n4.身体后倾（弹力带支撑）\n5.缓慢下蹲（弹力带让膝盖保持前方）\n6.在底部或任何角度保持等长收缩\n7.保持30-45秒×3-5组",
     "breathing": "正常呼吸不屏气", "errors": "弹力带位置太高/太低|身体不够后倾|膝盖内扣|时间太短",
     "tips": "是髌腱炎康复的金标准动作；等长收缩在无痛角度进行；允许疼痛≤5/10；渐进：增加时间→增加深度→增加负荷（手持哑铃）。",
     "muscles": ["股四头肌", "股四头肌内侧"]},

    {"name": "臀桥(Glute Bridge)", "target": "臀大肌", "secondary": "腘绳肌",
     "steps": "1.仰卧，双膝弯曲，脚踩地（脚跟靠近臀部）\n2.双臂放身体两侧\n3.通过脚跟发力，臀部向上推\n4.顶部身体从肩到膝一条直线\n5.顶部挤压臀部2秒（骨盆后倾）\n6.控制下放（不要砸下来）",
     "breathing": "推起呼气，下放吸气", "errors": "腰椎过伸（应该骨盆后倾）|用腘绳肌代偿|顶部不挤压|脚位太远（更多腘绳肌）",
     "tips": "是臀肌激活的基础动作；进阶：单腿→负重→脚抬高→臀推；如果感觉腘绳肌多于臀部→脚靠近臀部+有意识挤压臀部。",
     "muscles": ["臀部", "腿后肌群"]},

    {"name": "分腿蹲(Split Squat)", "target": "股四头肌+臀大肌", "secondary": "臀中肌",
     "steps": "1.前后脚站立（步幅约60-90cm）\n2.后脚脚尖着地\n3.躯干直立\n4.双膝同时弯曲下蹲\n5.后膝接近地面\n6.前脚用力蹬地站起",
     "breathing": "下蹲吸气，站起呼气", "errors": "前膝内扣|躯干过度前倾|步幅太小（膝盖压力大）|后脚用力过多",
     "tips": "是保加利亚分腿蹲的退阶版本；前倾更多=更多臀部；直立更多=更多股四头肌；可以手持哑铃或杠铃增加负荷。",
     "muscles": ["股四头肌", "臀部", "臀中肌"]},

    {"name": "腿举(窄站距-股四头肌重点)", "target": "股四头肌", "secondary": "臀大肌",
     "steps": "1.坐入腿举机\n2.双脚放在踏板下方，与肩同宽或略窄\n3.脚尖朝前或略外转\n4.解除安全锁\n5.控制下放到膝盖接近90°\n6.用力蹬起（通过前脚掌发力）",
     "breathing": "下放吸气，蹬起呼气", "errors": "臀部翘起|膝盖完全锁死|下放不够深|脚位太高",
     "tips": "脚位低+窄站距=最大化股四头肌；vs宽站距高脚位=更多臀部/内收肌；是深蹲的高SFR补充（减少下背疲劳）。",
     "muscles": ["股四头肌", "股直肌"]},

    {"name": "Cable Woodchop(绳索伐木)", "target": "腹斜肌", "secondary": "核心旋转链",
     "steps": "1.侧对高位绳索\n2.双手握把手\n3.双脚与肩同宽，微屈膝\n4.从高位向对侧低位做对角线拉动\n5.力量从髋部旋转发起\n6.手臂保持微屈固定（不是用手臂拉）\n7.控制回放",
     "breathing": "拉动时呼气，回放时吸气", "errors": "只用手臂拉（应该是躯干旋转）|脚不转动|速度过快失控|弯腰",
     "tips": "高到低=腹斜肌+前锯肌；低到高=腹斜肌+髋旋转；是核心旋转力量的最佳训练；模拟投掷/挥拍动作模式。",
     "muscles": ["腹斜肌"]},

    {"name": "Dead Bug进阶变体", "target": "腹横肌+腹直肌", "secondary": "核心抗伸展",
     "steps": "**基础版**：仰卧，双臂朝天，双腿抬起(90°)，对侧手脚交替伸出\n**进阶1**：加弹力带（手握弹力带增加抗伸展）\n**进阶2**：双腿同时伸出（更大杠杆）\n**进阶3**：手持哑铃/药球\n**进阶4**：腿完全伸直（不屈膝）\n\n**所有变体的关键**：腰椎始终贴地！如果腰部拱起=太难了，退阶。",
     "breathing": "伸出时呼气（收紧腹部），收回时吸气", "errors": "腰部拱起离开地面|速度过快|呼吸不协调|对侧不协调",
     "tips": "是最安全的核心训练之一（仰卧位=脊柱无负荷）；腰痛患者的首选核心动作；关键指标：能否在整个动作中保持腰椎贴地。",
     "muscles": ["腹直肌", "腹斜肌"]},

    {"name": "侧平板(Side Plank)进阶", "target": "腹斜肌+腰方肌", "secondary": "臀中肌",
     "steps": "**基础**：前臂侧撑，膝盖弯曲（退阶）\n**标准**：前臂侧撑，双脚叠放，身体直线\n**进阶1**：上方腿抬起（增加臀中肌）\n**进阶2**：上方手持哑铃\n**进阶3**：脚放在凳子上（增加杠杆）\n**进阶4**：Copenhagen侧平板（上腿放凳上，下腿悬空）\n\n保持时间：20-45秒/组",
     "breathing": "正常呼吸不屏气", "errors": "臀部下沉|身体前后倾斜|肩膀耸起|时间过长质量下降",
     "tips": "是核心抗侧屈的最佳训练；对脊柱侧弯/骨盆不等高有矫正作用（凸侧朝下多做）；比平板支撑更功能性（日常生活中侧向稳定需求大）。",
     "muscles": ["腹斜肌", "臀中肌"]},

    {"name": "Reverse Hyper(反向背伸展)", "target": "臀大肌+竖脊肌", "secondary": "腘绳肌",
     "steps": "1.俯卧在高平台/专用器械上（髋部在边缘）\n2.上半身固定，双手抓住平台\n3.双腿自然下垂\n4.用臀部和下背力量将双腿向后上方抬起\n5.抬到身体成一条直线（不过伸）\n6.控制下放",
     "breathing": "抬起呼气，下放吸气", "errors": "过度伸展（腰椎过伸）|用惯性甩腿|上半身移动|ROM不完整",
     "tips": "Louie Simmons（Westside Barbell）的标志性动作；对下背康复有益（牵引效果）；是硬拉的优秀辅助动作；没有专用器械可以用高凳/GHD替代。",
     "muscles": ["臀部", "下背部", "腿后肌群"]},
]

def generate_batch45() -> List[Dict]:
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
    chunks = generate_batch45()
    print(f"生成 {len(chunks)} chunks")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "batch45.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print("已保存到 output/batch45.json")
