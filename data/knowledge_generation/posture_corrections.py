"""
体态评估与矫正知识生成

注意：related_muscles 使用图谱 Muscle 节点名称
"""

from chunk_utils import make_chunk
from typing import List, Dict

# 体态问题中涉及的肌肉 → 图谱名称映射
_MUSCLE_MAP = {
    "胸大肌": "胸部",
    "胸小肌": "胸部",
    "上斜方肌": "上斜方肌",
    "下斜方肌": "斜方肌下部",
    "菱形肌": "斜方肌（中背）",
    "前锯肌": "肩部",
    "冈下肌": "肩部",
    "小圆肌": "三角肌后束",
    "髂腰肌": "腹股沟",
    "股直肌": "股直肌",
    "竖脊肌": "下背部",
    "臀大肌": "臀部",
    "臀中肌": "臀中肌",
    "腹直肌": "腹直肌",
    "腹横肌": "腹直肌",
    "腘绳肌": "腿后肌群",
    "内收肌群": "大腿内侧",
    "股外侧肌": "股四头肌",
    "股内侧肌": "股四头肌内侧",
    "腓肠肌": "小腿",
    "胫骨后肌": "小腿",
    "腰方肌": "下背部",
}


def _map_muscles(muscle_str: str) -> List[str]:
    """将体态问题中的肌肉名称映射到图谱节点名称"""
    result = set()
    for name in muscle_str.split("、"):
        name = name.strip()
        mapped = _MUSCLE_MAP.get(name)
        if mapped:
            result.add(mapped)
        # 也尝试部分匹配
        for key, val in _MUSCLE_MAP.items():
            if key in name:
                result.add(val)
    return list(result) if result else ["未知"]


POSTURE_DATA = [
    {
        "name": "上交叉综合征（圆肩+头前伸+驼背）",
        "appearance": "从侧面看：头部前移（耳朵在肩膀前方）、肩膀前倾内扣、胸椎后凸增大（驼背）、肩胛骨前倾外展",
        "tight_muscles": "胸大肌、胸小肌、上斜方肌、肩胛提肌、胸锁乳突肌、枕下肌群",
        "weak_muscles": "深层颈屈肌、下斜方肌、菱形肌、前锯肌、冈下肌/小圆肌",
        "assessment": "1) 侧面照片：耳垂是否在肩峰正上方；2) 墙壁测试：后脑勺能否自然贴墙；3) 肩胛骨位置：内侧缘是否贴近脊柱",
        "correction_stretch": "胸大肌门框拉伸（30秒×3）、胸小肌泡沫轴松解、上斜方肌侧屈拉伸、胸锁乳突肌旋转拉伸",
        "correction_strengthen": "面拉（3×15）、YTWL（2×10）、下斜方肌俯卧Y举、深层颈屈肌收下巴训练、前锯肌推墙plus",
        "daily_habits": "调整屏幕高度（眼睛平视上1/3）、每30分钟做收下巴+夹背动作、睡觉避免高枕头",
        "training_notes": "减少前平举和过多卧推；增加划船和面拉比例（推拉比至少1:1.5）；卧推时强调肩胛骨后缩下沉",
    },
    {
        "name": "下交叉综合征（骨盆前倾）",
        "appearance": "从侧面看：腰椎前凸增大（塌腰）、腹部前突、臀部后翘（非肌肉发达而是骨盆倾斜）、大腿前侧紧绷",
        "tight_muscles": "髂腰肌、股直肌、竖脊肌腰段、阔筋膜张肌",
        "weak_muscles": "臀大肌、腹直肌、腹横肌、腘绳肌",
        "assessment": "1) Thomas 测试：仰卧抱膝，另一腿大腿能否平放于床面；2) 骨盆倾斜角：ASIS 与 PSIS 连线与水平面夹角（正常5-10°，前倾>15°）",
        "correction_stretch": "弓步髂腰肌拉伸（30秒×3/侧）、沙发拉伸（股直肌）、竖脊肌猫牛式、泡沫轴阔筋膜张肌",
        "correction_strengthen": "臀桥（3×15，强调顶峰挤压）、死虫式（3×10/侧）、反向卷腹、鸟狗式",
        "daily_habits": "坐姿时骨盆中立（坐骨承重）、站立时收腹夹臀、避免长时间穿高跟鞋",
        "training_notes": "深蹲前充分激活臀肌（蚌式+臀桥）；硬拉注意骨盆中立不要过度伸展；加强腹部抗伸展训练（平板支撑、Ab Wheel）",
    },
    {
        "name": "膝内翻（O型腿）",
        "appearance": "站立时双膝无法并拢，小腿向外弯曲，双踝可以并拢但双膝间有明显间距",
        "tight_muscles": "阔筋膜张肌、髂胫束、股二头肌（外侧腘绳肌）、腓肠肌外侧头",
        "weak_muscles": "臀中肌、股内侧肌（VMO）、内收肌群",
        "assessment": "1) 站立位双踝并拢测量膝间距（>3cm 为异常）；2) 单腿深蹲观察膝关节是否外移；3) 排除骨骼结构性问题（需X光）",
        "correction_stretch": "髂胫束泡沫轴松解、阔筋膜张肌拉伸、腓肠肌外侧拉伸",
        "correction_strengthen": "蚌式（弹力带）、侧卧髋外展、单腿臀桥、VMO 强化（末端伸膝）",
        "daily_habits": "避免跷二郎腿、站立时注意膝盖朝向脚尖方向、选择支撑性好的鞋子",
        "training_notes": "深蹲时膝盖主动外推（对准脚尖方向）；避免窄距深蹲；加强臀中肌激活",
    },
    {
        "name": "膝外翻（X型腿）",
        "appearance": "站立时双膝并拢但双踝无法并拢，小腿向内弯曲，从正面看腿呈X形",
        "tight_muscles": "内收肌群、髂胫束远端、腓肠肌内侧头",
        "weak_muscles": "臀中肌（外展功能）、股外侧肌、腓骨长肌",
        "assessment": "1) 站立位双膝并拢测量踝间距；2) 单腿深蹲观察膝关节是否内扣；3) 动态外翻测试（跳跃落地时膝盖方向）",
        "correction_stretch": "内收肌蛙式拉伸、髂胫束泡沫轴",
        "correction_strengthen": "弹力带侧走（Monster Walk）、单腿罗马尼亚硬拉、侧平板支撑抬腿",
        "daily_habits": "跑步/跳跃时注意膝盖对准脚尖；避免W坐姿",
        "training_notes": "深蹲时在膝盖上方套弹力带（提供外展提示）；避免膝盖内扣的动作模式；加强落地力学训练",
    },
    {
        "name": "翼状肩胛",
        "appearance": "肩胛骨内侧缘或下角翘起，从背后看肩胛骨像翅膀一样突出",
        "tight_muscles": "胸小肌、胸大肌",
        "weak_muscles": "前锯肌（最主要）、下斜方肌、菱形肌",
        "assessment": "1) 墙壁俯卧撑观察肩胛骨是否翘起；2) 前推测试（双手前推墙壁时观察）；3) 俯卧撑底部肩胛骨位置",
        "correction_stretch": "胸小肌松解（网球/花生球）、胸大肌门框拉伸",
        "correction_strengthen": "前锯肌推墙Plus（3×15）、前锯肌俯卧撑Plus、高位前锯肌冲拳、熊爬",
        "daily_habits": "避免长时间手臂前伸（如趴桌子）；加强肩胛骨控制意识",
        "training_notes": "所有推的动作结束时加一个前锯肌Plus（肩胛骨前伸）；引体向上起始位做肩胛骨下沉",
    },
    {
        "name": "脊柱侧弯",
        "appearance": "从背后看脊柱呈S形或C形弯曲，可能伴有肩膀不等高、骨盆不等高、肋骨隆起",
        "tight_muscles": "凹侧肌肉（缩短侧）：竖脊肌、腰方肌、腹内外斜肌",
        "weak_muscles": "凸侧肌肉（拉长侧）：竖脊肌、腹内外斜肌",
        "assessment": "1) Adam前屈测试（弯腰时观察肋骨是否一侧隆起）；2) 铅垂线测试；3) Cobb角测量（需X光，>10°为侧弯）",
        "correction_stretch": "凹侧侧屈拉伸、凹侧旋转拉伸、猫牛式",
        "correction_strengthen": "凸侧侧平板支撑、不对称负重搬运（凸侧持重）、Schroth 方法呼吸训练",
        "daily_habits": "避免单侧背包；坐姿保持对称；睡觉避免固定一侧",
        "training_notes": "轻度侧弯（<20°）可正常训练但注意对称性；中度以上需要物理治疗师指导；避免大重量不对称负荷",
    },
    {
        "name": "扁平足",
        "appearance": "站立时足弓塌陷，足内侧几乎完全接触地面，可能伴有足外翻（后跟外翻）",
        "tight_muscles": "腓骨长短肌、小腿三头肌",
        "weak_muscles": "胫骨后肌（维持足弓的关键）、足底内在肌、趾屈肌",
        "assessment": "1) 湿脚印测试（足弓区域是否有印记）；2) 单腿提踵测试（后跟是否内翻）；3) 舟骨下降测试",
        "correction_stretch": "小腿三头肌拉伸（膝伸直+膝弯曲两种）、腓骨肌泡沫轴",
        "correction_strengthen": "短足训练（Short Foot Exercise）、毛巾抓取、单腿平衡、胫骨后肌弹力带训练",
        "daily_habits": "选择有足弓支撑的鞋子；赤足训练增强足底肌肉；避免长时间穿平底鞋",
        "training_notes": "深蹲时注意三点支撑（大拇趾球、小趾球、脚跟）；可使用举重鞋提供足弓支撑",
    },
    {
        "name": "骨盆不等高（功能性）",
        "appearance": "站立时一侧髂嵴高于另一侧，可能伴有一侧肩膀下沉、脊柱代偿性侧弯",
        "tight_muscles": "高侧：腰方肌、髂腰肌；低侧：内收肌群",
        "weak_muscles": "低侧：臀中肌、腰方肌；高侧：内收肌群",
        "assessment": "1) 站立位触诊双侧髂嵴高度；2) 排除真性腿长差异（仰卧位测量）；3) 单腿站立测试（Trendelenburg征）",
        "correction_stretch": "高侧腰方肌侧屈拉伸、高侧髂腰肌弓步拉伸",
        "correction_strengthen": "低侧臀中肌强化（侧卧外展、单腿站立）、低侧腰方肌侧平板",
        "daily_habits": "避免习惯性单侧站立；坐姿保持骨盆水平；检查是否有腿长差异需要鞋垫补偿",
        "training_notes": "单侧训练优先（先练弱侧）；避免大重量双侧负荷直到对称性改善；深蹲时注意杠铃是否水平",
    },
]


def generate_posture_corrections() -> List[Dict]:
    """生成体态矫正知识 chunks"""
    chunks = []

    for posture in POSTURE_DATA:
        # Chunk 1: 识别与评估
        content = (
            f"## {posture['name']} — 识别与评估\n\n"
            f"**外观表现**：{posture['appearance']}\n\n"
            f"**紧张肌群**：{posture['tight_muscles']}\n\n"
            f"**薄弱肌群**：{posture['weak_muscles']}\n\n"
            f"**评估方法**：{posture['assessment']}"
        )
        related = _map_muscles(posture["tight_muscles"]) + _map_muscles(posture["weak_muscles"])
        chunks.append(make_chunk(
            category="posture",
            subcategory="assessment",
            title=f"{posture['name']} — 识别与评估",
            content=content,
            keywords=[posture["name"].split("（")[0], "体态", "评估", "紧张", "薄弱"],
            related_muscles=list(set(related)),
        ))

        # Chunk 2: 矫正方案
        content = (
            f"## {posture['name']} — 矫正方案\n\n"
            f"**拉伸（松解紧张肌群）**：{posture['correction_stretch']}\n\n"
            f"**强化（激活薄弱肌群）**：{posture['correction_strengthen']}\n\n"
            f"**日常习惯调整**：{posture['daily_habits']}\n\n"
            f"**训练注意事项**：{posture['training_notes']}"
        )
        chunks.append(make_chunk(
            category="posture",
            subcategory="correction",
            title=f"{posture['name']} — 矫正方案",
            content=content,
            keywords=[posture["name"].split("（")[0], "矫正", "拉伸", "强化"],
            related_muscles=list(set(_map_muscles(posture["weak_muscles"]))),
        ))

    return chunks


if __name__ == "__main__":
    chunks = generate_posture_corrections()
    print(f"生成 {len(chunks)} 个体态矫正 chunks")
    for c in chunks[:4]:
        print(f"  - {c['title']}")
