"""
batch37: 更多动作教学 — 自由重量复合动作深化
"""
from chunk_utils import make_chunk
from graph_alignment import normalize_muscles
from typing import List, Dict
import json, os

EXERCISES = [
    {"name": "前蹲(Front Squat)", "target": "股四头肌", "secondary": "核心/上背",
     "steps": "1.杠铃放在前三角肌/锁骨上（前架位置）\n2.肘部抬高（上臂平行地面或略高）\n3.双脚肩宽，脚尖外转15-30°\n4.深吸气，核心收紧\n5.保持肘部高位，下蹲到最深\n6.躯干尽可能直立\n7.用力站起，全程肘部不下沉",
     "breathing": "下蹲前吸气屏住→站起后呼气",
     "errors": "肘部下沉（杠铃滚落）|躯干过度前倾|腕关节疼痛|深度不够",
     "tips": "前架困难→用交叉臂或绑带辅助；比后蹲更多股四头肌（躯干更直立）；核心抗屈曲需求极高；通常重量比后蹲低20-30%。",
     "muscles": ["股四头肌", "臀大肌", "腹直肌"]},

    {"name": "相扑硬拉", "target": "臀大肌+内收肌", "secondary": "股四头肌",
     "steps": "1.宽站距（脚尖外转45-80°）\n2.双手在两腿之间握杠（肩宽或窄于肩）\n3.髋部下沉，胸部挺起\n4.肩胛骨在杠铃正上方\n5.用力蹬地+推髋，杠铃垂直上升\n6.锁定时髋完全伸展",
     "breathing": "拉起前深吸气→拉起过程屏气→锁定后呼气",
     "errors": "膝盖内扣|髋部先起（变成直腿硬拉）|杠铃远离身体|圆背",
     "tips": "比传统硬拉行程短15-20%；躯干更直立=腰椎力矩臂更短；需要良好的髋外旋活动度；长躯干/短手臂的人可能更适合相扑。",
     "muscles": ["臀部", "大腿内侧", "股四头肌", "背阔肌"]},

    {"name": "窄距卧推", "target": "肱三头肌", "secondary": "胸大肌",
     "steps": "1.仰卧平凳，握距与肩同宽或略窄\n2.肩胛骨后缩下沉\n3.杠铃下放到下胸/剑突位置\n4.肘关节贴近身体（不外展）\n5.用力推起到手臂伸直\n6.全程肘关节角度<45°",
     "breathing": "下放时吸气→推起时呼气",
     "errors": "握距太窄（腕关节压力）|肘关节外展（变成标准卧推）|触胸位置太高|弹起借力",
     "tips": "握距=肩宽即可（不需要双手紧贴）；是三头肌力量发展的最佳动作；也是卧推锁定力量的辅助动作；比孤立三头动作能用更大重量。",
     "muscles": ["肱三头肌", "胸部", "三角肌前束"]},

    {"name": "Good Morning", "target": "竖脊肌+腘绳肌", "secondary": "臀大肌",
     "steps": "1.杠铃放在上背（类似深蹲位置）\n2.双脚与肩同宽\n3.膝盖微屈并锁定\n4.髋铰链：臀部向后推，躯干前倾\n5.下降到躯干接近平行地面（或腘绳肌拉伸极限）\n6.用臀部和下背力量站起",
     "breathing": "前倾时吸气→站起时呼气",
     "errors": "膝盖过度弯曲（变成深蹲）|圆背|下降过深（失去中立脊柱）|重量过大",
     "tips": "是下背力量的最佳训练动作之一；比硬拉对下背的孤立刺激更大；从轻重量开始学习；Westside Barbell的核心辅助动作。",
     "muscles": ["竖脊肌", "腘绳肌", "臀大肌"]},

    {"name": "Dips(双杠臂屈伸)", "target": "胸大肌下部+三头肌", "secondary": "三角肌前束",
     "steps": "1.双手撑住双杠，手臂伸直支撑体重\n2.身体略前倾（更多胸部）或直立（更多三头）\n3.屈肘下降，直到上臂平行地面或略低\n4.用力推起到手臂伸直\n5.全程控制，不要摆荡",
     "breathing": "下降时吸气→推起时呼气",
     "errors": "下降过深（肩关节压力）|身体摆荡|肩膀耸起|速度过快",
     "tips": "前倾=更多胸部（尤其下胸）；直立=更多三头肌；是上肢推力的王者动作；肩痛时避免（或限制深度）；负重Dips是高级力量动作。",
     "muscles": ["中胸与下胸", "肱三头肌", "三角肌前束"]},

    {"name": "Pendlay Row(力量划船)", "target": "背阔肌+上背", "secondary": "竖脊肌",
     "steps": "1.杠铃在地面，俯身至躯干平行地面\n2.正握，略宽于肩\n3.每次从地面完全静止开始拉\n4.爆发性拉向下胸/上腹\n5.顶部挤压背部\n6.控制下放回地面（每次完全静止）",
     "breathing": "拉起时呼气→放下时吸气",
     "errors": "躯干抬起借力|不从地面完全静止开始|拉向腹部太低|圆背",
     "tips": "vs普通划船：每次从静止开始=消除拉伸反射=更纯粹的力量；更爆发性；对上背/后三角刺激更大；是力量举选手的常用辅助动作。",
     "muscles": ["背阔肌", "斜方肌（中背）", "三角肌后束", "竖脊肌"]},

    {"name": "Push Press(借力推举)", "target": "三角肌+三头肌", "secondary": "股四头肌",
     "steps": "1.杠铃在前架位置（锁骨/前三角肌上）\n2.双脚与肩同宽\n3.快速微蹲（膝盖弯曲15-20°）\n4.立即爆发性蹬腿+推举\n5.利用腿部驱动将杠铃推过头顶\n6.手臂完全伸直锁定\n7.控制下放回前架",
     "breathing": "微蹲时吸气→蹬腿推举时呼气",
     "errors": "微蹲太深（变成Push Jerk）|蹬腿和推举不协调|过度后仰|膝盖内扣",
     "tips": "比严格推举能多推20-30%重量；训练过头位置的超负荷；是从推举到挺举的过渡动作；腿部驱动是关键（不是手臂先推）。",
     "muscles": ["三角肌前束", "三角肌中束", "肱三头肌", "股四头肌"]},

    {"name": "Trap Bar硬拉(六角杠硬拉)", "target": "全身后链", "secondary": "股四头肌",
     "steps": "1.站在六角杠中间\n2.双手握住两侧把手（高把手或低把手）\n3.髋铰链+屈膝，类似深蹲和硬拉的混合\n4.胸部挺起，背部中立\n5.用力蹬地站起\n6.锁定时髋完全伸展",
     "breathing": "拉起前深吸气→拉起屏气→锁定呼气",
     "errors": "圆背|膝盖内扣|重心前移（应该在足中部）|锁定时过度后仰",
     "tips": "比传统硬拉更安全（重心在身体中间而非前方）；对下背压力更小；新手学习硬拉模式的最佳选择；高把手=更短行程=更大重量。",
     "muscles": ["臀部", "腿后肌群", "股四头肌", "背阔肌"]},

    {"name": "地板卧推(Floor Press)", "target": "胸大肌+三头肌", "secondary": "三角肌前束",
     "steps": "1.仰卧在地面，膝盖弯曲脚踩地\n2.杠铃在架上或搭档递给你\n3.正常卧推握距\n4.下放直到上臂触地（自然限制ROM）\n5.短暂停顿（消除拉伸反射）\n6.用力推起到手臂伸直",
     "breathing": "下放时吸气→推起时呼气",
     "errors": "上臂触地后弹起（应该停顿）|肘关节过度外展|臀部抬起|握距太窄/太宽",
     "tips": "ROM被地面限制=减少肩关节压力（肩伤时的卧推替代）；消除拉伸反射=纯粹的推力；重点训练卧推的上半程/锁定力量；Westside常用辅助动作。",
     "muscles": ["胸部", "肱三头肌", "三角肌前束"]},

    {"name": "罗马椅背伸展(45°Back Extension)", "target": "竖脊肌+臀大肌", "secondary": "腘绳肌",
     "steps": "1.调整罗马椅垫子高度（髋骨在垫子上缘）\n2.脚踩住脚踏板，身体前倾\n3.双手交叉胸前或放脑后\n4.从前倾位用臀部和下背力量抬起躯干\n5.抬到身体成一条直线（不过伸）\n6.顶部挤压臀部\n7.控制下放",
     "breathing": "抬起时呼气→下放时吸气",
     "errors": "过度伸展（腰椎过伸）|速度过快|只用下背不用臀部|ROM不完整",
     "tips": "圆背版本=更多竖脊肌；直背版本=更多臀大肌；可以抱杠片/哑铃增加负荷；是硬拉的优秀辅助动作；也适合腰痛康复（轻负荷）。",
     "muscles": ["下背部", "臀部", "腿后肌群"]},
]

def generate_batch37() -> List[Dict]:
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
    chunks = generate_batch37()
    print(f"生成 {len(chunks)} chunks")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "batch37.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print("已保存到 output/batch37.json")
