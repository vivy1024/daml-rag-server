"""batch93"""
from chunk_utils import make_chunk
from graph_alignment import normalize_muscles
from typing import List, Dict
import json, os

DATA = [
    {"title": "训练中的常见训练与训练中的常见训练与训练与关节活动度维护日常例程", "cat": "warmup", "sub": "daily_mobility",
     "content": "## 关节活动度日常维护例程（每天5分钟）\n\n### 为什么每天都要做\n- 关节活动度是'用进废退'的\n- 久坐后关节僵硬→训练前需要更长热身\n- 每天5分钟维护=训练前不需要额外活动度训练\n- 预防长期活动度下降\n\n### 5分钟全身CARs例程\n\n**颈椎**（30秒）：\n- 缓慢画最大的圆（正反各3圈）\n- 不要快速旋转\n\n**肩关节**（60秒）：\n- 手臂贴身侧，画最大的圆\n- 正反各5圈每侧\n- 全程最大张力\n\n**胸椎**（30秒）：\n- 坐姿，双手交叉抱胸\n- 缓慢旋转（左右各5次）\n\n**髋关节**（60秒）：\n- 站立扶墙，膝盖抬起画圆\n- 正反各5圈每侧\n- 骨盆不动\n\n**膝关节**（30秒）：\n- 站立，缓慢屈伸膝盖\n- 10次全ROM屈伸\n\n**踝关节**（30秒）：\n- 站立或坐姿\n- 画圈各10圈每侧\n\n**腕关节**（30秒）：\n- 画圈各10圈每侧\n- 屈伸各5次\n\n### 何时做\n- 最佳：早上起床后（唤醒关节）\n- 也可以：训练前（作为热身第一步）\n- 也可以：工作间隙（对抗久坐）\n\n### 关键原则\n- 缓慢（每个圆30-60秒）\n- 最大范围（画最大的圆）\n- 最大张力（全身绷紧）\n- 无痛（如果某个方向痛→减小范围）\n- 每天做（一致性>单次时长）",
     "keywords": ["CARs", "日常", "活动度", "5分钟", "关节", "维护"], "muscles": []},

    {"title": "训练中的常见训练与训练中的常见训练与训练与训练前激活序列", "cat": "warmup", "sub": "activation_sequence",
     "content": "## 训练前激活序列\n\n### 推日激活（3分钟）\n1. 弹力带拉开 2×15（后三角肌+菱形肌激活）\n2. 弹力带外旋 2×12（肩袖激活）\n3. 墙壁天使 2×8（肩胛骨上回旋）\n\n### 拉日激活（3分钟）\n1. 弹力带拉开 2×15（后三角肌激活）\n2. 肩胛骨下拉（悬挂位只做肩胛骨下沉）2×8\n3. 直臂下拉（轻重量）2×12（背阔肌预激活）\n\n### 腿日激活（5分钟）\n1. 蚌式开合 2×15每侧（臀中肌）\n2. 臀桥 2×12（臀大肌）\n3. 弹力带侧走 2×10步每方向（臀中肌）\n4. 深蹲到站 ×8（整合髋/踝/胸椎）\n\n### 为什么需要激活\n- 久坐后某些肌群'休眠'（尤其臀肌/下斜方肌）\n- 激活=重新建立神经连接\n- 激活后训练中目标肌群参与更多\n- 减少代偿（如深蹲时腘绳肌代替臀肌）\n\n### 激活 vs 热身\n- 热身：升高体温+关节润滑（通用）\n- 激活：针对性唤醒特定肌群（专项）\n- 顺序：通用热身→激活→专项热身→工作组\n\n### 不需要激活的情况\n- 如果你已经能很好地感受目标肌群\n- 如果训练前已经做了充分的动态拉伸\n- 如果时间极度有限（可以跳过，不是必须）\n\n### 关键原则\n- 轻重量/弹力带（不是训练，是唤醒）\n- 2-3分钟足够（不要变成另一次训练）\n- 专注感受目标肌群收缩\n- 如果某肌群'感觉不到'→激活更重要",
     "keywords": ["激活", "训练前", "推日", "拉日", "腿日", "臀肌"], "muscles": ["臀中肌", "三角肌后束"]},

    {"title": "训练中的常见训练与训练中的常见训练与训练与训练后放松序列", "cat": "recovery", "sub": "cooldown_sequence",
     "content": "## 训练后放松序列\n\n### 推日后放松（5分钟）\n1. 步行2分钟（心率恢复）\n2. 胸肌门框拉伸 30秒每侧\n3. 三角肌前束拉伸 30秒每侧\n4. 三头肌过头拉伸 30秒每侧\n5. 3次深呼吸（副交感神经激活）\n\n### 拉日后放松（5分钟）\n1. 步行2分钟\n2. 背阔肌侧拉伸 30秒每侧\n3. 二头肌墙壁拉伸 30秒每侧\n4. 前臂拉伸 30秒每侧\n5. 3次深呼吸\n\n### 腿日后放松（8分钟）\n1. 步行2分钟\n2. 髂腰肌半跪姿拉伸 45秒每侧\n3. 股四头肌站立拉伸 30秒每侧\n4. 腘绳肌仰卧拉伸 30秒每侧\n5. 臀部4字拉伸 30秒每侧\n6. 小腿直膝拉伸 30秒每侧\n7. 3次深呼吸\n\n### 放松的目的\n- 心率逐渐恢复（不要突然停止）\n- 心理上标志训练结束\n- 维持/改善柔韧性\n- 促进副交感神经激活（恢复模式）\n\n### 放松不能做什么\n- ❌ 预防DOMS\n- ❌ 加速肌肉恢复\n- ❌ 预防受伤\n\n### 如果时间不够\n- 最少做：步行2-3分钟（不要突然停止）\n- 拉伸可以跳过（不是必须）\n- 或：回家后/睡前做拉伸",
     "keywords": ["放松", "训练后", "拉伸", "步行", "深呼吸", "序列"], "muscles": []},

    {"title": "训练中的常见训练与训练中的常见训练与训练与训练中的常见错误动作图解描述", "cat": "methodology", "sub": "common_form_errors",
     "content": "## 常见动作错误描述\n\n### 深蹲常见错误\n**膝内扣**：从正面看，膝盖向内塌陷，偏离脚尖方向。像'X'形。\n**Good Morning**：从侧面看，臀部先起但躯干前倾不变，变成了类似硬拉的动作。\n**Butt Wink**：从侧面看，底部时骨盆突然后倾，腰椎从前凸变为屈曲。\n**脚跟抬起**：从侧面看，脚跟离开地面，重心前移到脚尖。\n\n### 卧推常见错误\n**肩膀前伸**：推到顶部时肩膀离开凳面，肩胛骨前伸。\n**弹起**：杠铃触胸后利用胸部弹性弹起，而非肌肉控制。\n**肘过度外展**：从上方看，上臂与躯干接近90°（应该45-60°）。\n**臀部离凳**：推举过程中臀部抬离凳面。\n\n### 硬拉常见错误\n**圆背**：从侧面看，上背和/或下背明显弯曲（应该保持中立）。\n**杠铃远离身体**：从侧面看，杠铃路径不是垂直的，而是向前弧形。\n**膝盖先锁死**：从侧面看，膝盖在杠铃离地后立即伸直，变成直腿硬拉。\n**过度后仰**：锁定时躯干过度后仰（应该只是站直）。\n\n### 如何自我检查\n1. 录像（侧面+正面）\n2. 对比正确动作视频\n3. 慢动作回放看细节\n4. 或：请有经验的人帮你看\n\n### 纠正的通用方法\n1. 减重（最直接有效）\n2. 慢速执行（有时间感受每个位置）\n3. 使用提示词（外部聚焦）\n4. 暂停训练（在问题位置停住感受）\n5. 辅助动作强化薄弱环节",
     "keywords": ["错误动作", "描述", "膝内扣", "圆背", "弹起", "纠正"], "muscles": []},

    {"title": "训练中的常见训练与训练中的常见训练与训练与训练知识库使用说明", "cat": "methodology", "sub": "kb_usage",
     "content": "## 知识库使用说明（AI Agent参考）\n\n### 知识库结构\n- 总chunks：4888+\n- 向量维度：1024（gte-large-zh）\n- 存储：data/v3/vectors/knowledge.npy + ids.json + payloads.json\n- 检索方式：余弦相似度向量检索\n\n### 知识类别分布\n| 类别 | 内容 |\n|------|------|\n| anatomy | 肌肉附着点/关节/筋膜 |\n| biomechanics | 运动链/力矩臂/动作分析 |\n| methodology | 训练方法/计划/动作教学/编程 |\n| nutrition | 营养/补剂/饮食方案 |\n| recovery | 恢复/睡眠/Deload |\n| rehabilitation | 康复/伤病/体态矫正 |\n| physiology | 运动生理学/能量系统/激素 |\n| psychology | 动机/习惯/心理技巧 |\n| special_populations | 特殊人群/年龄/疾病 |\n| faq | 常见问题/误区 |\n| warmup | 热身/拉伸/激活 |\n| posture | 体态评估/矫正 |\n\n### 检索建议\n- 用户问训练方法→检索methodology\n- 用户问营养→检索nutrition\n- 用户问疼痛/受伤→检索rehabilitation\n- 用户问动作技术→检索methodology(exercise_instruction)\n- 用户问恢复→检索recovery\n\n### 知识库的图谱对齐\n- related_muscles字段使用Neo4j图谱中的标准肌肉名称\n- 通过graph_alignment.py的normalize_muscles()函数对齐\n- 40个标准肌肉节点名称\n\n### 知识库的局限\n- AI生成内容（标注source: ai_knowledge_base）\n- 需要与图谱数据（确定性查询）互补使用\n- 不能替代专业医疗建议",
     "keywords": ["使用说明", "AI Agent", "检索", "类别", "图谱对齐", "结构"], "muscles": []},
]

def generate_batch93() -> List[Dict]:
    chunks = []
    for item in DATA:
        muscles = normalize_muscles(item.get("muscles", []))
        chunks.append(make_chunk(
            category=item.get("cat", "methodology"),
            subcategory=item.get("sub", "training"),
            title=item["title"],
            content=item["content"],
            keywords=item["keywords"],
            related_muscles=muscles,
        ))
    return chunks

if __name__ == "__main__":
    chunks = generate_batch93()
    print(f"生成 {len(chunks)} chunks")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "batch93.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print("已保存到 output/batch93.json")
