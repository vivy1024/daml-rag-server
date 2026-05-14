"""batch76"""
from chunk_utils import make_chunk
from graph_alignment import normalize_muscles
from typing import List, Dict
import json, os

DATA = [
    {"title": "训练中的常见训练周期模板", "cat": "methodology", "sub": "cycle_templates",
     "content": "## 训练周期模板\n\n### 4周基础Mesocycle模板\n```\n第1周：适应周（MEV，RPE 7）\n  - 每肌群10组/周\n  - 学习/恢复动作模式\n  - 建立基线\n\n第2周：建设周（+2组，RPE 7-8）\n  - 每肌群12组/周\n  - 开始渐进\n\n第3周：过载周（+2组，RPE 8-9）\n  - 每肌群14组/周\n  - 最高训练量\n\n第4周：Deload周（50%容量，RPE 5-6）\n  - 每肌群6-7组/周\n  - 恢复+超量恢复\n```\n\n### 6周力量Mesocycle模板\n```\n第1周：4×6 @ 75% RPE 7\n第2周：4×5 @ 78% RPE 7-8\n第3周：5×4 @ 82% RPE 8\n第4周：5×3 @ 85% RPE 8-9\n第5周：4×2 @ 90% RPE 9\n第6周：Deload 3×3 @ 60% RPE 5\n```\n\n### 8周肌肥大Mesocycle模板\n```\n第1-2周：3×10-12 每肌群10组/周 RPE 7\n第3-4周：3×8-10 每肌群12组/周 RPE 7-8\n第5-6周：4×8-10 每肌群14-16组/周 RPE 8-9\n第7周：4×6-8 每肌群16-18组/周 RPE 9\n第8周：Deload 2×10 每肌群6组/周 RPE 5-6\n```\n\n### 使用方法\n1. 选择适合你目标的模板\n2. 填入具体动作和重量\n3. 严格执行（不要中途改变）\n4. Deload后评估进步\n5. 下个Mesocycle调整（基于上个周期的数据）",
     "keywords": ["周期模板", "Mesocycle", "4周", "6周", "8周", "力量", "肌肥大"], "muscles": []},

    {"title": "训练中的常见训练记录分析方法", "cat": "methodology", "sub": "data_analysis",
     "content": "## 训练数据分析方法\n\n### 估算1RM追踪\n- 公式：1RM = 重量 × (1 + 次数/30)（Epley）\n- 每周计算主要动作的估算1RM\n- 画趋势图（Excel/App）\n- 上升=进步，平坦=停滞，下降=问题\n\n### 容量负荷追踪\n- 每周总容量 = Σ(重量×次数×组数)\n- 例：深蹲80kg×5×4 = 1600kg容量\n- 追踪每周总容量变化\n- Mesocycle内应该渐进增加\n\n### RPE趋势分析\n- 记录每组RPE\n- 同重量同次数的RPE变化：\n  - RPE降低=变强了（同重量更轻松）\n  - RPE升高=疲劳累积（需要Deload）\n\n### 体重×力量分析\n- Wilks/DOTS分数（标准化体重差异）\n- 或简单的：主要动作/体重 比值\n- 追踪相对力量变化（排除体重变化的影响）\n\n### 简单分析模板（每周5分钟）\n```\n本周 vs 上周：\n- 深蹲：80kg×5×4 → 80kg×6×4 ✓进步\n- 卧推：60kg×8×3 → 60kg×8×3 →持平\n- 硬拉：100kg×5×3 → 102.5kg×5×3 ✓进步\n\n整体评估：2/3动作进步，计划有效\n下周计划：卧推尝试加到62.5kg或增加1组\n```\n\n### 关键原则\n- 简单>复杂（能坚持的分析方法最好）\n- 看趋势不看单次（波动是正常的）\n- 数据指导决策（不是为了分析而分析）\n- 每周5分钟回顾就够了",
     "keywords": ["数据分析", "1RM估算", "容量", "RPE趋势", "追踪"], "muscles": []},

    {"title": "训练中的常见训练与营养整合清单", "cat": "nutrition", "sub": "integration_checklist",
     "content": "## 训练与营养整合清单\n\n### 每日营养检查清单\n- [ ] 蛋白质达标？（体重×2g）\n- [ ] 每餐有蛋白质？（20-40g/餐）\n- [ ] 热量匹配目标？（盈余/缺口/维持）\n- [ ] 水分充足？（30-40ml/kg）\n- [ ] 蔬菜水果？（每天5份+）\n- [ ] 训练前有进食？（1-3小时前）\n- [ ] 训练后有蛋白质？（1-2小时内）\n\n### 增肌期清单\n- [ ] 热量盈余+200-500kcal？\n- [ ] 蛋白质1.6-2.2g/kg？\n- [ ] 碳水充足（4-7g/kg）？\n- [ ] 每周增重0.25-0.5kg？\n- [ ] 力量在进步？\n\n### 减脂期清单\n- [ ] 热量缺口-300~-500kcal？\n- [ ] 蛋白质提高到2.0-2.4g/kg？\n- [ ] 训练强度维持（不降重量）？\n- [ ] 每周减重0.5-1%体重？\n- [ ] 每1-2周安排再喂日？\n- [ ] 睡眠7-9小时？\n\n### 训练日 vs 休息日\n| | 训练日 | 休息日 |\n|--|--------|--------|\n| 碳水 | 高 | 中-低 |\n| 蛋白质 | 高 | 高（不变！）|\n| 总热量 | 正常-略高 | 正常-略低 |\n| 水分 | 更多 | 正常 |\n\n### 最简化版本（如果只能做3件事）\n1. 每餐有蛋白质（手掌大小的肉/鱼/蛋/豆腐）\n2. 训练前不空腹太久（>4小时）\n3. 体重趋势作为热量反馈（不需要精确计算）",
     "keywords": ["整合清单", "每日", "增肌", "减脂", "训练日", "简化"], "muscles": []},

    {"title": "训练中的常见训练与恢复整合清单", "cat": "recovery", "sub": "recovery_checklist",
     "content": "## 训练与恢复整合清单\n\n### 每日恢复检查清单\n- [ ] 睡眠7-9小时？\n- [ ] 蛋白质达标？\n- [ ] 水分充足？\n- [ ] 训练后补充营养？\n- [ ] 有轻度活动（步行）？\n- [ ] 压力管理（不过度焦虑）？\n\n### 每周恢复检查\n- [ ] 至少1天完全休息？\n- [ ] 1-2天主动恢复？\n- [ ] 训练表现稳定/进步？\n- [ ] 没有持续疼痛？\n- [ ] 睡眠质量稳定？\n- [ ] 训练动力正常？\n\n### Deload信号检查\n出现以下2+个信号→需要Deload：\n- [ ] 连续2周力量下降\n- [ ] 静息心率升高5+bpm\n- [ ] 睡眠质量明显变差\n- [ ] 训练动力持续下降\n- [ ] 关节持续酸痛\n- [ ] 情绪波动/易怒\n- [ ] 食欲下降\n\n### 恢复优先级\n1. 睡眠（7-9小时）★★★★★\n2. 营养（蛋白质+热量）★★★★★\n3. 时间（48-72小时间隔）★★★★\n4. 压力管理 ★★★★\n5. 主动恢复（步行/瑜伽）★★★\n6. 拉伸/泡沫轴 ★★\n7. 补剂（镁/鱼油）★★\n8. 冰浴/按摩 ★★\n\n### 最简化版本（如果只能做3件事）\n1. 睡够7小时\n2. 吃够蛋白质\n3. 每3-5周Deload一次",
     "keywords": ["恢复清单", "每日", "每周", "Deload信号", "优先级"], "muscles": []},

    {"title": "训练中的常见训练总结 — 核心原则回顾", "cat": "methodology", "sub": "core_principles",
     "content": "## 训练核心原则总结\n\n### 10条不变的训练原则\n\n**1. 渐进超负荷**\n没有渐进=没有进步。每次训练尝试某种形式的进步。\n\n**2. 特异性（SAID）**\n练什么得什么。想变强→练力量。想增肌→练肌肥大。\n\n**3. 恢复与适应**\n训练是破坏，恢复才是建设。没有恢复=没有进步。\n\n**4. 个体差异**\n没有万能方案。找到适合你的参数。\n\n**5. 可逆性**\n用进废退。停止训练→适应消退。维持需要持续训练。\n\n**6. 一致性**\n长期坚持>短期爆发。3年每周3次>3个月每天练。\n\n**7. 技术优先**\n好的技术=更多目标肌群刺激+更少受伤风险。\n\n**8. 平衡**\n推拉平衡、前后平衡、左右平衡。失衡=受伤风险。\n\n**9. 耐心**\n真正的变化需要时间。以年为单位思考。\n\n**10. 享受**\n不享受=不可持续。找到你喜欢的训练方式。\n\n### 如果只记住一句话\n**'渐进超负荷+充足恢复+长期一致性=进步。其他都是细节。'**\n\n### 优先级金字塔\n```\n        一致性\n       /      \\\n    渐进超负荷\n   /            \\\n  营养+睡眠+恢复\n /                \\\n动作技术+计划结构\n/                    \\\n补剂+精确时机+高级技术\n```\n\n底层>顶层。先把底层做好，再关注顶层。",
     "keywords": ["核心原则", "总结", "渐进超负荷", "一致性", "恢复", "金字塔"], "muscles": []},
]

def generate_batch76() -> List[Dict]:
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
    chunks = generate_batch76()
    print(f"生成 {len(chunks)} chunks")
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, "batch76.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print("已保存到 output/batch76.json")
