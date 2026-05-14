"""batch90"""
from chunk_utils import make_chunk
from graph_alignment import normalize_muscles
from typing import List, Dict
import json, os

DATA = [
    {"title": "训练中的常见训练与训练中的常见训练与训练装备购买优先级", "cat": "methodology", "sub": "equipment_priority",
     "content": "## 训练装备购买优先级\n\n### 必须有（Day 1）\n1. **训练鞋**（平底硬底）：Converse/Vans ~200-400元\n   - 不要穿跑步鞋力量训练！\n2. **水壶**：任何能装500ml+的 ~30-50元\n3. **毛巾**：擦汗+擦器械 ~20元\n\n### 强烈推荐（1-3个月后）\n4. **举重腰带**：~200-500元\n   - 10mm皮革（力量举）或尼龙（通用）\n   - 用于>80% 1RM的深蹲/硬拉\n5. **弹力带套装**：~100-200元\n   - 热身激活/辅助引体/增加阻力\n   - 性价比极高的多用途工具\n\n### 可以考虑（6个月+）\n6. **助力带**：~50-100元\n   - 大重量硬拉/划船时握力不足\n7. **护腕**：~100-200元\n   - 大重量卧推/推举时腕关节保护\n8. **举重鞋**：~400-1000元\n   - 深蹲/前蹲/推举（踝背屈不足时）\n9. **膝套**：~100-300元\n   - 大重量深蹲时保暖+轻度支撑\n\n### 不需要\n- ❌ 手套（削弱握力反馈）\n- ❌ 腰带一直戴（削弱核心）\n- ❌ 过多护具（掩盖问题）\n- ❌ 昂贵的'健身服'（普通运动服就行）\n\n### 家庭健身房优先级\n1. 可调节哑铃（~1500元）\n2. 引体向上杆（~100元）\n3. 弹力带套装（~150元）\n4. 瑜伽垫（~100元）\n5. 可调节凳（~800元）\n6. 杠铃+杠片+深蹲架（~5000-10000元）",
     "keywords": ["装备", "购买", "优先级", "腰带", "鞋", "弹力带"], "muscles": []},

    {"title": "训练中的常见训练与训练中的常见训练与训练术语速查", "cat": "methodology", "sub": "terminology",
     "content": "## 训练术语速查\n\n### 训练参数术语\n| 术语 | 含义 |\n|------|------|\n| 1RM | 一次最大重量（只能做1次的重量）|\n| RPE | 主观努力程度（1-10分）|\n| RIR | 储备次数（还能做几次）|\n| TUT | 时间张力（肌肉承受张力的总时间）|\n| ROM | 活动范围（关节运动的角度）|\n| AMRAP | 尽可能多次（做到力竭）|\n| PR | 个人纪录 |\n| TM | 训练最大值（通常为1RM的85-90%）|\n\n### 训练方法术语\n| 术语 | 含义 |\n|------|------|\n| 渐进超负荷 | 逐渐增加训练刺激 |\n| Deload | 减载周（降低训练量恢复）|\n| Mesocycle | 中周期（4-6周一个训练阶段）|\n| 周期化 | 系统性规划训练变量变化 |\n| DUP | 每日波动周期化 |\n| 超级组 | 两个动作连续做不休息 |\n| Drop Set | 做到力竭→减重→继续 |\n| Rest-Pause | 力竭→休息10秒→继续 |\n\n### 营养术语\n| 术语 | 含义 |\n|------|------|\n| TDEE | 每日总能量消耗 |\n| BMR | 基础代谢率 |\n| MPS | 肌肉蛋白质合成 |\n| TEF | 食物热效应 |\n| NEAT | 非运动活动热量消耗 |\n| Macros | 宏量营养素（蛋白质/碳水/脂肪）|\n\n### 解剖/生理术语\n| 术语 | 含义 |\n|------|------|\n| 向心 | 肌肉缩短收缩（用力阶段）|\n| 离心 | 肌肉拉长收缩（下放阶段）|\n| 等长 | 肌肉长度不变的收缩 |\n| DOMS | 延迟性肌肉酸痛 |\n| CNS | 中枢神经系统 |\n| GH | 生长激素 |\n| EPOC | 运动后过量氧耗 |",
     "keywords": ["术语", "速查", "RPE", "1RM", "Deload", "TDEE", "定义"], "muscles": []},

    {"title": "训练中的常见训练与训练中的常见训练与训练常见缩写解释", "cat": "methodology", "sub": "abbreviations",
     "content": "## 训练常见缩写\n\n### 训练方案缩写\n| 缩写 | 全称 | 含义 |\n|------|------|------|\n| SS | Starting Strength | 新手力量方案 |\n| SL | StrongLifts | 新手5×5方案 |\n| PPL | Push/Pull/Legs | 推拉腿分化 |\n| UL | Upper/Lower | 上下分化 |\n| GVT | German Volume Training | 德国容量训练(10×10) |\n| PHUL | Power Hypertrophy Upper Lower | 力量肌肥大上下 |\n| PHAT | Power Hypertrophy Adaptive Training | 力量肌肥大适应训练 |\n| nSuns | 基于5/3/1的高容量方案 | 中级力量方案 |\n| GZCL | Cody Lefever的方法 | 分层训练结构 |\n\n### 动作缩写\n| 缩写 | 全称 |\n|------|------|\n| RDL | Romanian Deadlift（罗马尼亚硬拉）|\n| OHP | Overhead Press（过头推举）|\n| BB | Barbell（杠铃）|\n| DB | Dumbbell（哑铃）|\n| KB | Kettlebell（壶铃）|\n| BW | Bodyweight（自重）|\n| SSB | Safety Squat Bar（安全杠）|\n\n### 容量/强度缩写\n| 缩写 | 全称 |\n|------|------|\n| MEV | Minimum Effective Volume（最低有效容量）|\n| MAV | Maximum Adaptive Volume（最大适应容量）|\n| MRV | Maximum Recoverable Volume（最大可恢复容量）|\n| MV | Maintenance Volume（维持容量）|\n| SFR | Stimulus to Fatigue Ratio（刺激疲劳比）|\n\n### 营养缩写\n| 缩写 | 全称 |\n|------|------|\n| IF | Intermittent Fasting（间歇性断食）|\n| IIFYM | If It Fits Your Macros（灵活饮食）|\n| WPC | Whey Protein Concentrate（乳清浓缩）|\n| WPI | Whey Protein Isolate（乳清分离）|\n| BCAAs | Branched Chain Amino Acids（支链氨基酸）|",
     "keywords": ["缩写", "解释", "SS", "PPL", "RDL", "MEV", "术语"], "muscles": []},

    {"title": "训练中的常见训练与训练中的常见训练与训练知识来源推荐", "cat": "methodology", "sub": "resources",
     "content": "## 训练知识来源推荐\n\n### 中文资源\n| 类型 | 推荐 | 特点 |\n|------|------|------|\n| B站 | Jeff Nippard中文/杰夫叔 | 循证+实用 |\n| 书籍 | 《力量训练基础》(Rippetoe) | 新手必读 |\n| 书籍 | 《运动生理学》 | 理论基础 |\n| 公众号 | 各循证健身号 | 碎片化学习 |\n\n### 英文资源（质量最高）\n| 类型 | 推荐 | 特点 |\n|------|------|------|\n| YouTube | Jeff Nippard | 循证+视觉化 |\n| YouTube | Renaissance Periodization | 容量/周期化 |\n| YouTube | Alan Thrall | 动作教学 |\n| YouTube | AthleanX | 康复/功能 |\n| 网站 | Stronger By Science | 深度研究解读 |\n| 网站 | Renaissance Periodization | 训练编程 |\n| 播客 | Iron Culture | 循证讨论 |\n| 书籍 | Scientific Principles of Hypertrophy Training | 肌肥大圣经 |\n\n### 如何判断信息质量\n**可信信号**：\n- 引用具体研究\n- 承认不确定性\n- 考虑个体差异\n- 有专业认证/学历\n- 不卖'秘诀'\n\n**不可信信号**：\n- '这是唯一正确方法'\n- '3天练出腹肌'\n- 只展示结果不解释过程\n- 推销产品为主\n- 无科学依据\n\n### 学习建议\n- 选择2-3个可靠来源（不要关注太多）\n- 学到的东西至少执行8周再评估\n- 实践>理论（做比看更重要）\n- 基础原则不会变（不需要追最新'趋势'）",
     "keywords": ["资源", "推荐", "B站", "YouTube", "书籍", "判断质量"], "muscles": []},

    {"title": "训练中的常见训练与训练中的常见训练与训练知识的最终最终总结", "cat": "methodology", "sub": "absolute_final",
     "content": "## 训练知识绝对最终总结\n\n### 如果你只能记住这一页\n\n**训练**：\n- 每周3-5天力量训练\n- 复合动作为主（深蹲/卧推/硬拉/划船/推举）\n- 每次尝试进步（渐进超负荷）\n- 每3-5周Deload\n\n**营养**：\n- 蛋白质：体重×2g/天\n- 热量：增肌+300/减脂-400\n- 每餐有蛋白质\n\n**恢复**：\n- 睡眠7-9小时\n- 每肌群间隔48-72小时\n\n**心态**：\n- 一致性>完美\n- 耐心（以年为单位）\n- 享受过程\n\n### 如果你只能做一件事\n**每周训练3次，每次做深蹲+卧推+划船各3组。**\n这一件事就能让你比90%不训练的人更强壮、更健康。\n\n### 训练的终极意义\n训练不只是为了肌肉和力量。\n训练教会你：\n- 纪律（不管想不想都去做）\n- 耐心（真正的变化需要时间）\n- 韧性（面对困难继续前进）\n- 自信（证明自己能做到）\n- 健康（身体是一切的基础）\n\n这些品质会转移到生活的每一个方面。\n\n**训练是你能给自己的最好礼物。**\n\n**现在就开始。坚持下去。享受旅程。**",
     "keywords": ["绝对最终", "一页", "核心", "意义", "开始", "坚持"], "muscles": []},
]

def generate_batch90() -> List[Dict]:
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
    chunks = generate_batch90()
    print(f"生成 {len(chunks)} chunks")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "batch90.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print("已保存到 output/batch90.json")
