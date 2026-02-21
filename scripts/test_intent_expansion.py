# -*- coding: utf-8 -*-
"""
意图分类器扩展测试 — 6 种新模式 × 5+ 测试用例
验证 retrieval-optimization-v2 Task 3
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.framework.retrieval.intent_classifier import classify_intent, StructuredQueryType

# ─── 测试用例定义 ─────────────────────────────────

TEST_CASES = {
    "SUPPLEMENT_ADVICE": [
        ("蛋白粉怎么选", "supplement_advice"),
        ("肌酸什么时候吃", "supplement_advice"),
        ("BCAA有必要吃吗", "supplement_advice"),
        ("乳清蛋白和酪蛋白区别", "supplement_advice"),
        ("氮泵的作用", "supplement_advice"),
        ("左旋肉碱有用吗", "supplement_advice"),
    ],
    "TRAINING_FREQUENCY": [
        ("胸肌多久练一次", "training_frequency"),
        ("一周练几次比较好", "training_frequency"),
        ("背阔肌的训练频率", "training_frequency"),
        ("腿需要休息几天", "training_frequency"),
        ("每周练胸几次", "training_frequency"),
    ],
    "TRAINING_SPLIT": [
        ("推拉腿怎么安排", "training_split"),
        ("五天分化计划", "training_split"),
        ("上下肢分化训练", "training_split"),
        ("训练怎么分化", "training_split"),
        ("制定一个训练计划", "training_split"),
    ],
    "EXERCISE_SUBSTITUTION": [
        ("引体向上的替代动作", "exercise_substitution"),
        ("用什么代替深蹲", "exercise_substitution"),
        ("没有杠铃怎么练卧推", "exercise_substitution"),
        ("深蹲可以用腿举替代吗", "exercise_substitution"),
        ("卧推的替代方案", "exercise_substitution"),
    ],
    "WARMUP_STRETCHING": [
        ("深蹲前怎么热身", "warmup_stretching"),
        ("训练后怎么拉伸", "warmup_stretching"),
        ("卧推前的热身动作", "warmup_stretching"),
        ("腿部训练后放松", "warmup_stretching"),
        ("肩部的激活动作", "warmup_stretching"),
    ],
    "NUTRITION_MACRO": [
        ("增肌期蛋白质摄入量", "nutrition_macro"),
        ("减脂碳水怎么安排", "nutrition_macro"),
        ("每天需要吃多少蛋白质", "nutrition_macro"),
        ("TDEE怎么算", "nutrition_macro"),
        ("怎么计算热量摄入", "nutrition_macro"),
        ("减脂期脂肪吃多少", "nutrition_macro"),
    ],
}

# ─── 原有模式回归测试（确保不破坏已有功能）─────────────

REGRESSION_CASES = [
    ("深蹲练哪些肌肉", "STRUCTURED", "exercise_muscles"),
    ("练胸肌的动作有哪些", "STRUCTURED", "muscle_exercises"),
    ("哑铃能做什么动作", "STRUCTURED", "exercise_by_equipment"),
    ("腰椎间盘突出不能做什么动作", "STRUCTURED", "safety_contraindications"),
    ("圆肩怎么矫正", "STRUCTURED", "postural_exercises"),
    ("卧推力量标准", "STRUCTURED", "strength_standards"),
    ("复合动作有哪些", "STRUCTURED", "exercise_by_mechanic"),
    ("适合新手的动作", "STRUCTURED", "exercise_by_level"),
    ("增肌期间怎么安排饮食", "STRUCTURED", "nutrition_macro"),
    ("健身多久能看到效果", "SEMANTIC", None),
]


def main():
    print("=" * 70)
    print("🧪 意图分类器扩展测试 — 6 种新模式")
    print("=" * 70)

    total = 0
    correct = 0
    failures = []

    # 测试新模式
    for category, cases in TEST_CASES.items():
        print(f"\n  ── {category} ({len(cases)} 用例) ──")
        cat_correct = 0

        for query, expected_type in cases:
            total += 1
            result = classify_intent(query)
            actual_type = result.structured_type.value if result.structured_type else None
            actual_intent = result.intent.name

            match = actual_type == expected_type
            if match:
                correct += 1
                cat_correct += 1
                icon = "✅"
            else:
                icon = "❌"
                failures.append((query, expected_type, actual_type, actual_intent))

            print(f"    {icon} \"{query}\" → {actual_intent}/{actual_type or 'None'} (conf={result.confidence:.2f})")

        cat_acc = cat_correct / len(cases) * 100
        print(f"    📈 {category}: {cat_correct}/{len(cases)} = {cat_acc:.0f}%")

    # 回归测试
    print(f"\n  ── 回归测试 ({len(REGRESSION_CASES)} 用例) ──")
    reg_correct = 0

    for query, expected_intent, expected_type in REGRESSION_CASES:
        total += 1
        result = classify_intent(query)
        actual_intent = result.intent.name
        actual_type = result.structured_type.value if result.structured_type else None

        intent_match = actual_intent == expected_intent
        type_match = actual_type == expected_type if expected_type else True
        match = intent_match and type_match

        if match:
            correct += 1
            reg_correct += 1
            icon = "✅"
        else:
            icon = "❌"
            failures.append((query, f"{expected_intent}/{expected_type}", f"{actual_intent}/{actual_type}", actual_intent))

        print(f"    {icon} \"{query}\" → {actual_intent}/{actual_type or 'None'}")

    reg_acc = reg_correct / len(REGRESSION_CASES) * 100
    print(f"    📈 回归测试: {reg_correct}/{len(REGRESSION_CASES)} = {reg_acc:.0f}%")

    # 汇总
    accuracy = correct / total * 100
    print(f"\n{'=' * 70}")
    print(f"📊 总计: {correct}/{total} = {accuracy:.1f}%")
    print(f"   {'✅ 达标 (>85%)' if accuracy > 85 else '⚠️ 未达标 (<85%)'}")

    if failures:
        print(f"\n❌ 失败用例 ({len(failures)}):")
        for q, exp, act, intent in failures:
            print(f"   \"{q}\" → 预期={exp}, 实际={act} (intent={intent})")

    print("=" * 70)
    return accuracy > 85


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
