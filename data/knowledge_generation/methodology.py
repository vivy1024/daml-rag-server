"""
训练方法论知识生成

覆盖：渐进超负荷、周期化、容量理论、常见训练方法
"""

from chunk_utils import make_chunk
from typing import List, Dict


# SPLICE_1

PROGRESSIVE_OVERLOAD_DATA = [
    {"title": "渐进超负荷原则 — 概述",
     "content": "## 渐进超负荷原则\n\n渐进超负荷（Progressive Overload）是力量训练最基本的原则：要持续进步，必须逐步增加训练刺激。刺激可以通过以下维度增加：\n\n1. **重量**（最直接）：每次训练增加负荷\n2. **次数**：同样重量做更多次\n3. **组数**：增加训练容量\n4. **频率**：增加每星期训练次数\n5. **动作难度**：从简单变体到复杂变体\n6. **缩短休息时间**：增加代谢压力\n7. **增加离心控制时间**：增加机械张力\n\n注意：不是每次训练都必须进步。周与周之间的趋势性进步才是关键。单次训练的波动是正常的（睡眠/压力/营养都会影响）。",
     "keywords": ["渐进超负荷", "progressive overload", "训练原则", "力量进步"]},
    {"title": "线性渐进 — 新手最佳策略",
     "content": "## 线性渐进（Linear Progression）\n\n**适用人群**：训练经验 < 6个月的新手\n\n**原理**：新手神经适应快，每次训练都能增加重量。\n\n**执行方式**：\n- 复合动作：每次训练 +2.5kg（深蹲/硬拉）或 +1.25kg（卧推/推举）\n- 孤立动作：每次训练 +1.25kg 或增加1次重复\n- 如果某次无法完成目标次数，保持重量再尝试1-2次\n- 连续3次无法完成 → 减重10%重新开始（reset）\n\n**典型程序**：Starting Strength、StrongLifts 5×5\n\n**预期进步速度**：\n- 深蹲：+5kg/星期（前3个月）\n- 卧推：+2.5kg/星期（前3个月）\n- 硬拉：+5-7.5kg/星期（前3个月）\n\n**何时毕业**：连续2次 reset 后仍无法进步 → 转为中级策略",
     "keywords": ["线性渐进", "新手", "Starting Strength", "StrongLifts", "每次加重"]},
    {"title": "双重渐进 — 中级策略",
     "content": "## 双重渐进（Double Progression）\n\n**适用人群**：训练经验 6-24 个月\n\n**原理**：先增加次数到范围上限，再增加重量回到下限。\n\n**执行方式**：\n1. 设定次数范围（如 6-10 次）\n2. 用当前重量做到范围上限（10次）的所有组\n3. 下次训练增加重量（+2.5kg），次数回到下限（6次）\n4. 再逐步增加次数到上限\n5. 循环\n\n**示例**：\n- 第1周：80kg × 6,6,6\n- 第2周：80kg × 7,7,6\n- 第3周：80kg × 8,8,7\n- 第4周：80kg × 9,9,8\n- 第5周：80kg × 10,10,10 ← 达到上限\n- 第6周：82.5kg × 6,6,6 ← 加重回到下限\n\n**优势**：比线性渐进更灵活，允许自然波动",
     "keywords": ["双重渐进", "中级", "次数范围", "加重策略"]},
    {"title": "波动周期化 — 高级策略",
     "content": "## 波动周期化（Undulating Periodization）\n\n**适用人群**：训练经验 > 2年\n\n**原理**：在一星期内变化训练强度和容量，避免适应停滞。\n\n**日波动（DUP - Daily Undulating Periodization）**：\n- 周一：力量日（4×5 @ 85%）\n- 周三：肌肥大日（3×10 @ 70%）\n- 周五：爆发力日（5×3 @ 75%，快速向心）\n\n**周波动（WUP - Weekly Undulating Periodization）**：\n- 第1周：高容量（4×10）\n- 第2周：中等（4×6）\n- 第3周：高强度（5×3）\n- 第4周：Deload\n\n**优势**：\n- 同时发展多种素质\n- 减少单调性\n- 研究显示对中高级训练者效果优于线性周期化\n\n**注意**：需要良好的恢复能力和训练经验来管理疲劳",
     "keywords": ["波动周期化", "DUP", "WUP", "高级", "强度变化"]},
    {"title": "微加载策略 — 突破停滞",
     "content": "## 微加载（Micro-loading）\n\n**适用场景**：常规加重（2.5kg）无法完成时\n\n**方法**：\n- 使用 0.5kg/1kg/1.25kg 的小杠片\n- 磁性微片（贴在杠铃上）\n- 链条/弹力带渐进\n\n**适用动作**：\n- 过头推举（最容易停滞的动作）\n- 弯举类（小肌群动作）\n- 侧平举（哑铃跳跃太大时）\n\n**替代策略**（无微片时）：\n- 增加1次重复代替加重\n- 增加1组\n- 增加离心时间（3秒→4秒）\n- 减少组间休息（3分钟→2.5分钟）\n\n**心理建议**：0.5kg/星期 = 26kg/年。微小进步累积起来很可观。",
     "keywords": ["微加载", "停滞", "突破", "小杠片", "渐进"]},
    {"title": "Deload 策略 — 疲劳管理",
     "content": "## Deload（减载周）\n\n**什么是 Deload**：计划性地降低训练负荷，让身体从累积疲劳中恢复。不是休息，是低强度训练。\n\n**何时需要 Deload**：\n- 计划性：每 3-6 个训练周期安排一次（新手6周、中级4周、高级3周）\n- 反应性：连续2次训练表现下降、关节持续酸痛、睡眠质量下降、动力明显降低\n\n**Deload 方式**：\n1. **减容量**（推荐）：组数减半，重量保持 → 维持神经适应，减少肌肉损伤\n2. **减强度**：重量减至60-70%，组数保持 → 适合关节需要恢复时\n3. **减频率**：训练天数减半 → 适合生活压力大时\n4. **完全休息**：不训练3-5天 → 仅在过度训练时使用\n\n**Deload 期间**：\n- 保持正常饮食（不要减热量）\n- 增加睡眠\n- 可以做轻度有氧/拉伸\n- 心理上接受'退一步进两步'",
     "keywords": ["deload", "减载", "疲劳管理", "恢复", "过度训练"]},
    {"title": "RPE/RIR 自动调节系统",
     "content": "## RPE 与 RIR 自动调节\n\n**RPE（Rating of Perceived Exertion）**：主观用力程度评分（1-10）\n**RIR（Reps in Reserve）**：储备次数（还能做几次）\n\n**对应关系**：\n- RPE 10 = RIR 0（力竭）\n- RPE 9 = RIR 1（还能做1次）\n- RPE 8 = RIR 2（还能做2次）\n- RPE 7 = RIR 3（还能做3次）\n\n**如何使用**：\n- 力量训练：RPE 7-9（不建议经常力竭）\n- 肌肥大训练：RPE 7-10（最后1-2组可接近力竭）\n- 热身组：RPE 5-6\n- Deload：RPE 5-7\n\n**优势**：\n- 自动适应每日状态波动\n- 不需要严格的百分比计算\n- 允许好状态时多做、差状态时少做\n\n**学习曲线**：新手通常低估 RPE（以为 RPE 9 实际只有 RPE 7）。需要3-6个月练习才能准确评估。\n\n**建议**：用视频回看验证自己的 RPE 判断是否准确。",
     "keywords": ["RPE", "RIR", "自动调节", "主观用力", "储备次数"]},
]

# SPLICE_2

PERIODIZATION_DATA = [
    {"title": "线性周期化 — 经典模型",
     "content": "## 线性周期化（Linear Periodization）\n\n**来源**：Matveyev（1960s），最早用于举重和田径\n\n**结构**：\n- 准备期（高容量低强度）→ 竞赛期（低容量高强度）→ 过渡期（恢复）\n\n**典型 Mesocycle（4周）**：\n- 第1周：4×12 @ 65%\n- 第2周：4×10 @ 70%\n- 第3周：4×8 @ 75%\n- 第4周：4×6 @ 80%\n- 第5周：Deload\n\n**优势**：简单易执行、适合新手和中级\n**劣势**：后期容量下降可能导致肌肉量流失；一次只发展一种素质\n\n**适用场景**：有明确比赛日期的运动员、新手建立基础",
     "keywords": ["线性周期化", "Matveyev", "mesocycle", "经典", "周期"]},
    {"title": "块状周期化 — 集中发展",
     "content": "## 块状周期化（Block Periodization）\n\n**来源**：Issurin（2000s），改进线性周期化\n\n**原理**：将训练分为2-4周的'块'，每块集中发展一种素质\n\n**典型结构**：\n- 积累块（Accumulation）：高容量，3-4周，发展肌肉量和工作能力\n- 转化块（Transmutation）：中等容量高强度，2-3周，发展最大力量\n- 实现块（Realization）：低容量最高强度，1-2周，表现峰值\n\n**优势**：\n- 集中刺激效果更好（残余训练效应）\n- 避免同时追求多目标的干扰\n- 适合高级训练者\n\n**残余训练效应**：\n- 有氧耐力：30天\n- 肌肉量：30天\n- 最大力量：30天\n- 爆发力：5-8天\n- 速度：5天\n\n这意味着可以在不同块之间保持之前发展的素质。",
     "keywords": ["块状周期化", "Block", "积累", "转化", "实现", "Issurin"]},
    {"title": "自动调节周期化 — 基于反馈",
     "content": "## 自动调节周期化（Autoregulated Periodization）\n\n**原理**：根据每日/每周的实际表现调整训练计划，而非严格遵循预设百分比。\n\n**实现方式**：\n1. **RPE 处方**：规定 RPE 而非具体重量（如'深蹲 4×5 @ RPE 8'）\n2. **APRE（Autoregulatory Progressive Resistance Exercise）**：\n   - 第1-2组用预设重量\n   - 第3组做到力竭\n   - 根据第3组次数调整第4组重量\n3. **Reactive Deload**：不预设 deload 时间，根据表现指标触发\n\n**表现指标**：\n- 速度下降 >20%（需要速度计）\n- RPE 比预期高 2+ 分\n- 连续2次训练未达目标\n- HRV 持续下降\n\n**优势**：最大化好状态的训练效果，最小化差状态的疲劳累积\n**劣势**：需要经验准确评估 RPE；新手不适用",
     "keywords": ["自动调节", "RPE处方", "APRE", "反馈", "个性化"]},
    {"title": "5/3/1 方法论 — Wendler",
     "content": "## 5/3/1 方法论（Jim Wendler）\n\n**核心理念**：慢即是快。每月只增加很小的重量，但持续数年不停滞。\n\n**结构（4周为一个周期）**：\n- 第1周（5s Week）：65%×5, 75%×5, 85%×5+\n- 第2周（3s Week）：70%×3, 80%×3, 90%×3+\n- 第3周（5/3/1 Week）：75%×5, 85%×3, 95%×1+\n- 第4周（Deload）：40%×5, 50%×5, 60%×5\n\n**'+'号组**：最后一组做尽可能多次（AMRAP），但保留1-2次储备\n\n**Training Max**：使用真实1RM的85-90%作为计算基准（保守起步）\n\n**每周期进步**：上肢 +2.5kg，下肢 +5kg（加在 Training Max 上）\n\n**辅助训练**：\n- BBB（Boring But Big）：主动作 5×10 @ 50-60%\n- FSL（First Set Last）：第一组重量再做 3-5×5\n- Joker Sets：状态好时加重做单次\n\n**适用人群**：中级到高级，追求长期稳定进步",
     "keywords": ["5/3/1", "Wendler", "Training Max", "AMRAP", "BBB", "周期"]},
    {"title": "训练频率与肌肥大",
     "content": "## 训练频率与肌肥大\n\n**肌蛋白合成（MPS）窗口**：训练后 24-72 小时内 MPS 升高。新手持续更久（~72h），高级训练者更短（~24-48h）。\n\n**频率建议**：\n- 新手：每肌群 2次/星期（全身训练 3次/星期）\n- 中级：每肌群 2次/星期（上下分化或推拉腿）\n- 高级：每肌群 2-3次/星期（高频率训练）\n\n**研究结论**（Schoenfeld 2016 meta-analysis）：\n- 每肌群 2次/星期 显著优于 1次/星期\n- 2次 vs 3次 差异不显著（但趋势支持更高频率）\n- 关键是**总容量相同**时，分散到更多天效果更好\n\n**实际建议**：\n- 弱项肌群可以提高到 3次/星期\n- 大肌群（腿/背）恢复慢，2次/星期通常足够\n- 小肌群（二头/三头/侧三角）恢复快，可以 3-4次/星期\n\n**注意**：频率增加时，每次训练的容量要相应减少，保持总容量不变或略增。",
     "keywords": ["训练频率", "肌肥大", "MPS", "肌蛋白合成", "每星期几次"]},
]

# SPLICE_3

VOLUME_THEORY_DATA = [
    {"title": "RP 训练容量理论 — MEV/MAV/MRV",
     "content": "## RP 训练容量理论（Dr. Mike Israetel）\n\n**核心概念**：\n- **MV（Maintenance Volume）**：维持现有肌肉量的最低容量（~4-6组/星期）\n- **MEV（Minimum Effective Volume）**：开始产生肌肥大的最低容量\n- **MAV（Maximum Adaptive Volume）**：产生最大适应的容量范围\n- **MRV（Maximum Recoverable Volume）**：能恢复的最大容量，超过则过度训练\n\n**各肌群参考值（组/星期）**：\n| 肌群 | MEV | MAV | MRV |\n|------|-----|-----|-----|\n| 胸 | 8 | 14 | 20 |\n| 背 | 8 | 14 | 20 |\n| 肩（侧三角） | 6 | 12 | 18 |\n| 股四头 | 6 | 14 | 20 |\n| 腘绳肌 | 4 | 10 | 16 |\n| 臀 | 4 | 12 | 16 |\n| 二头 | 4 | 10 | 16 |\n| 三头 | 4 | 8 | 14 |\n\n**注意**：这些是群体平均值，个体差异可达±30%。需要通过训练日志追踪自己的最佳容量。\n\n来源：RP Strength, Dr. Mike Israetel 公开发表的训练容量指南",
     "keywords": ["RP", "MEV", "MAV", "MRV", "训练容量", "Mike Israetel", "组数"]},
    {"title": "容量递增策略 — Mesocycle 内的容量管理",
     "content": "## 容量递增策略\n\n**原理**：在一个 Mesocycle（通常4-6周）内，逐周增加容量，然后 Deload 恢复。\n\n**典型结构**：\n- 第1周：MEV（起始容量）\n- 第2周：MEV + 2组\n- 第3周：MEV + 4组\n- 第4周：接近 MRV\n- 第5周：Deload（回到 MV 或更低）\n\n**示例（胸肌）**：\n- 第1周：10组/星期\n- 第2周：12组/星期\n- 第3周：14组/星期\n- 第4周：16组/星期\n- 第5周：Deload 6组/星期\n\n**为什么递增**：\n1. 身体对固定刺激会适应（需要逐步增加）\n2. 疲劳是累积的（不能一开始就用最大容量）\n3. Deload 后超量恢复，下个周期可以从更高起点开始\n\n**SFR（Stimulus to Fatigue Ratio）**：\n- 选择 SFR 高的动作（刺激大、疲劳小）\n- 复合动作 SFR 通常高于孤立动作\n- 疲劳累积时优先削减 SFR 低的动作",
     "keywords": ["容量递增", "mesocycle", "SFR", "刺激疲劳比", "周期化容量"]},
    {"title": "训练容量个体化 — 如何找到自己的 MRV",
     "content": "## 如何找到自己的 MRV\n\n**方法**：系统性地增加容量，观察恢复指标。\n\n**步骤**：\n1. 从保守容量开始（MEV 附近）\n2. 每周增加 1-2 组\n3. 记录以下指标：\n   - 力量表现（是否持续进步）\n   - 泵感和酸痛（适度 vs 过度）\n   - 关节感觉（无痛 vs 持续酸痛）\n   - 睡眠质量\n   - 训练动力\n4. 当出现以下信号时，你已接近 MRV：\n   - 力量开始下降\n   - 酸痛持续超过72小时\n   - 关节持续不适\n   - 睡眠变差\n   - 训练动力明显下降\n\n**记录工具**：训练日志是最重要的工具。记录每次训练的：动作、重量、次数、RPE、主观感受。\n\n**个体差异因素**：\n- 年龄（年轻恢复快）\n- 睡眠质量\n- 营养（热量盈余时 MRV 更高）\n- 压力水平\n- 训练经验\n- 基因（肌纤维类型分布）",
     "keywords": ["MRV", "个体化", "恢复指标", "训练日志", "过度训练信号"]},
]


def generate_methodology() -> List[Dict]:
    """生成训练方法论知识 chunks"""
    chunks = []
    for item in PROGRESSIVE_OVERLOAD_DATA:
        chunks.append(make_chunk(
            category="methodology",
            subcategory="progressive_overload",
            title=item["title"],
            content=item["content"],
            keywords=item["keywords"],
        ))
    for item in PERIODIZATION_DATA:
        chunks.append(make_chunk(
            category="methodology",
            subcategory="periodization",
            title=item["title"],
            content=item["content"],
            keywords=item["keywords"],
        ))
    for item in VOLUME_THEORY_DATA:
        chunks.append(make_chunk(
            category="methodology",
            subcategory="volume_theory",
            title=item["title"],
            content=item["content"],
            keywords=item["keywords"],
        ))
    return chunks


if __name__ == "__main__":
    chunks = generate_methodology()
    print(f"生成 {len(chunks)} 个训练方法论 chunks")
    for c in chunks[:3]:
        print(f"  - {c['title']}")
