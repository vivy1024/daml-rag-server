"""
康复训练知识 — 第二批（剩余11种图谱中的损伤）
"""

from chunk_utils import make_chunk
from typing import List, Dict


REHAB_BATCH2_DATA = [
    {
        "injury": "髌骨软化症（补充：运动处方）",
        "graph_name": "髌骨软化症",
        "phases": [
            {"name": "运动处方与长期管理", "goal": "建立可持续的训练习惯", "exercises": "游泳/骑车（低冲击有氧）、渐进深蹲（0-60°→全幅度）、单腿训练（台阶上下）、弹力带侧走（臀中肌）", "avoid": "长时间屈膝静坐（电影院综合征）、突然增加跑量、忽视热身"},
        ],
    },
    {
        "injury": "髂胫束综合征",
        "graph_name": "髂胫束综合征",
        "mechanism": "髂胫束（ITB）在膝关节外侧反复摩擦股骨外上髁导致疼痛。常见于跑者（Runner's Knee外侧型）。原因：臀中肌薄弱→髋内收增加→ITB张力增大、突然增加跑量、下坡跑过多、跑步内旋过度。",
        "grading": "早期（跑步后痛）→中期（跑步中痛）→晚期（行走痛）",
        "phases": [
            {"name": "急性期（0-2周）", "goal": "减少摩擦刺激", "exercises": "冰敷膝外侧、避免触发活动（跑步/下楼梯）、臀中肌等长激活（侧卧抬腿保持）", "avoid": "跑步、下坡行走、深蹲（如果加重疼痛）"},
            {"name": "矫正期（2-6周）", "goal": "解决根本原因", "exercises": "臀中肌强化（蚌式/侧卧外展/Monster Walk）、单腿平衡训练、泡沫轴松解TFL和股外侧肌（注意：不要直接滚ITB本身）、髋外展肌耐力训练", "avoid": "直接按压ITB（它是筋膜不是肌肉，不会被'松解'）、继续跑步"},
            {"name": "恢复跑步期（6周+）", "goal": "渐进恢复", "exercises": "从步行→走跑交替→连续跑、每周增量<10%、平地优先、加强跑前臀肌激活热身", "avoid": "下坡跑（前期）、突然增加距离或速度"},
        ],
        "return_criteria": "跑步30分钟无膝外侧痛；单腿深蹲稳定无痛；臀中肌力量对称",
        "red_flags": "膝关节肿胀（可能合并半月板问题）、关节交锁",
    },
    {
        "injury": "髋关节撞击综合征（FAI）",
        "graph_name": "髋关节撞击",
        "mechanism": "股骨头或髋臼形态异常导致关节活动时骨性撞击。Cam型（股骨头不圆）、Pincer型（髋臼过深）、混合型。深蹲底部、高抬腿时腹股沟疼痛是典型症状。",
        "grading": "轻度（特定角度痛）→中度（日常活动受限）→重度（关节软骨损伤）",
        "phases": [
            {"name": "症状管理期", "goal": "避免撞击角度", "exercises": "避免深蹲过深（限制在无痛范围）、髋关节活动度训练（避免终末端）、核心稳定训练、游泳/骑车", "avoid": "深蹲到底（如果引发腹股沟痛）、大幅度髋屈曲+内旋+内收组合动作"},
            {"name": "强化期", "goal": "在安全ROM内建立力量", "exercises": "箱式深蹲（控制深度）、臀推（无撞击风险）、单腿罗马尼亚硬拉、侧卧髋外展", "avoid": "忽视疼痛信号、强行增加ROM"},
        ],
        "return_criteria": "日常活动无痛；能在个人安全ROM内完成力量训练；腹股沟无卡顿感",
        "red_flags": "关节交锁、夜间痛加重、ROM持续恶化（可能需要关节镜手术评估）",
    },
    {
        "injury": "颈椎病（颈椎退行性变）",
        "graph_name": "颈椎病",
        "mechanism": "颈椎间盘退变、骨质增生、韧带肥厚导致神经根或脊髓受压。原因：长期低头（手机/电脑）、颈部肌肉失衡（深层颈屈肌薄弱+上斜方肌紧张）、年龄退变。",
        "grading": "颈型（仅颈部症状）→神经根型（上肢放射痛/麻木）→脊髓型（四肢无力/步态异常→需手术）",
        "phases": [
            {"name": "急性期", "goal": "减轻症状", "exercises": "收下巴训练（深层颈屈肌激活）、颈椎等长抗阻（各方向用手抵抗）、上斜方肌拉伸、热敷", "avoid": "颈椎大幅度旋转/后仰、颈后推举、高翻、倒立"},
            {"name": "恢复期", "goal": "建立颈椎稳定性", "exercises": "深层颈屈肌耐力训练（仰卧收下巴保持）、肩胛骨稳定训练（YTWL）、胸椎活动度改善、上肢神经滑动（如有放射症状）", "avoid": "大重量耸肩、颈后深蹲（改为前蹲或安全杠）、长时间固定姿势"},
        ],
        "return_criteria": "颈部活动无痛；上肢症状消失；能完成日常训练无加重",
        "red_flags": "脊髓型症状（四肢无力/步态不稳/大小便异常）→立即就医；进行性上肢肌力下降",
    },
    {
        "injury": "高尔夫球肘（肱骨内上髁炎）",
        "graph_name": "高尔夫球肘",
        "mechanism": "前臂屈肌群（尤其旋前圆肌和桡侧腕屈肌）起点处退行性病变。原因：反复腕屈曲+前臂旋前动作（引体向上正握/弯举/高尔夫挥杆）。与网球肘对称（内侧vs外侧）。",
        "grading": "同网球肘：早期（活动后痛）→中期（活动中痛）→晚期（静息痛+握力下降）",
        "phases": [
            {"name": "负荷管理期（0-2周）", "goal": "减少刺激", "exercises": "等长腕屈曲（握拳保持45秒×5）、前臂旋后练习（无负重）", "avoid": "正握引体向上、大重量弯举、高尔夫挥杆"},
            {"name": "离心训练期（2-8周）", "goal": "肌腱重塑", "exercises": "离心腕屈曲（用健手辅助向心，患手控制离心5秒）、渐进握力训练、改为反握或中立握引体", "avoid": "疼痛>5/10的抓握活动"},
            {"name": "恢复期（8周+）", "goal": "恢复功能", "exercises": "渐进恢复正握引体、前臂全面训练（屈/伸/旋前/旋后）", "avoid": "忽视热身、突然增加抓握负荷"},
        ],
        "return_criteria": "握力达健侧90%；正握引体无痛；日常活动无内侧肘痛",
        "red_flags": "肘关节不稳定（尺侧副韧带损伤）、前臂内侧麻木（尺神经卡压）",
    },
    {
        "injury": "腕管综合征",
        "graph_name": "腕管综合征",
        "mechanism": "正中神经在腕管内受压。原因：反复腕屈伸（打字/鼠标）、腕管内压力增高（水肿/肌腱炎/妊娠）。症状：拇指/食指/中指麻木刺痛，夜间加重。",
        "grading": "轻度（间歇麻木）→中度（持续麻木+握力下降）→重度（鱼际肌萎缩）",
        "phases": [
            {"name": "保守治疗期", "goal": "减轻神经压迫", "exercises": "腕关节中立位夜间支具、正中神经滑动练习（每天3组×10次）、腕伸肌拉伸、人体工学调整（键盘/鼠标位置）", "avoid": "长时间腕屈曲位（如骑车握把）、大重量需要强力握持的动作"},
            {"name": "训练调整期", "goal": "维持训练同时避免加重", "exercises": "使用握力辅助带（减少握持需求）、改用开放式握法（如EZ杠）、加强前臂伸肌（平衡屈伸比例）", "avoid": "粗杠硬拉（改用细杠或助力带）、长时间握持哑铃"},
        ],
        "return_criteria": "夜间无麻木；Phalen测试阴性；握力恢复正常",
        "red_flags": "鱼际肌萎缩（大拇指根部肌肉变小）→考虑手术；持续麻木>6个月保守治疗无效",
    },
]


def generate_rehabilitation_batch2() -> List[Dict]:
    """生成第二批康复训练知识"""
    chunks = []
    for rehab in REHAB_BATCH2_DATA:
        if "mechanism" in rehab:
            content = (
                f"## {rehab['injury']} — 损伤机制与分级\n\n"
                f"**损伤机制**：{rehab['mechanism']}\n\n"
                f"**分级**：{rehab['grading']}\n\n"
                f"**红旗信号**：{rehab.get('red_flags', '无特殊')}"
            )
            chunks.append(make_chunk(
                category="rehabilitation",
                subcategory="injury_mechanism",
                title=f"{rehab['injury']} — 损伤机制",
                content=content,
                keywords=[rehab["graph_name"], "损伤机制", "分级"],
                related_injuries=[rehab["graph_name"]],
            ))

        for phase in rehab["phases"]:
            content = (
                f"## {rehab['injury']} — {phase['name']}\n\n"
                f"**目标**：{phase['goal']}\n\n"
                f"**推荐训练**：{phase['exercises']}\n\n"
                f"**禁忌/避免**：{phase['avoid']}"
            )
            chunks.append(make_chunk(
                category="rehabilitation",
                subcategory="rehab_protocol",
                title=f"{rehab['injury']} — {phase['name']}",
                content=content,
                keywords=[rehab["graph_name"], "康复", "训练"],
                related_injuries=[rehab["graph_name"]],
            ))

        if "return_criteria" in rehab:
            content = (
                f"## {rehab['injury']} — 重返训练标准\n\n"
                f"**标准**：{rehab['return_criteria']}\n\n"
                f"**红旗信号**：{rehab['red_flags']}"
            )
            chunks.append(make_chunk(
                category="rehabilitation",
                subcategory="return_criteria",
                title=f"{rehab['injury']} — 重返训练标准",
                content=content,
                keywords=[rehab["graph_name"], "重返训练"],
                related_injuries=[rehab["graph_name"]],
            ))

    return chunks


if __name__ == "__main__":
    chunks = generate_rehabilitation_batch2()
    print(f"生成 {len(chunks)} 个康复训练(batch2) chunks")
