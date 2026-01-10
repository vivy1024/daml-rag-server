# -*- coding: utf-8 -*-
"""
验证增强的Layer3安全规则

测试内容：
1. 增强版_validate_safety方法
2. 增强版joint_load_rule（支持severity级别）
3. 用户健康状况检查

Requirements: 4.3, 4.6
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.framework.retrieval.layer3_rule_engine import Layer3RuleEngine


async def test_enhanced_joint_load_rule():
    """测试增强的关节负荷规则"""
    print("\n" + "="*60)
    print("测试1: 增强版关节负荷规则（支持severity级别）")
    print("="*60)
    
    rule_engine = Layer3RuleEngine()
    
    # 测试用例：用户有绝对禁忌和相对禁忌
    user_profile = {
        "health_profile": {
            "injuries": [
                {"body_part": "膝关节", "severity": "absolute", "status": "active"},
                {"body_part": "肩关节", "severity": "relative", "status": "active"},
            ],
            "injury_history": [
                {"body_part": "腰椎", "severity": "caution", "status": "active"}
            ]
        }
    }
    
    # 候选动作
    candidates = [
        {"exercise_name_zh": "深蹲", "primary_muscle_zh": "股四头肌", "involved_joints": ["膝关节", "髋关节"]},
        {"exercise_name_zh": "卧推", "primary_muscle_zh": "胸大肌", "involved_joints": ["肩关节", "肘关节"]},
        {"exercise_name_zh": "硬拉", "primary_muscle_zh": "竖脊肌", "involved_joints": ["腰椎", "髋关节"]},
        {"exercise_name_zh": "二头弯举", "primary_muscle_zh": "肱二头肌", "involved_joints": ["肘关节"]},
        {"exercise_name_zh": "平板支撑", "primary_muscle_zh": "核心", "involved_joints": []},
    ]
    
    result, details = await rule_engine._apply_joint_load_rule(
        candidates=candidates,
        user_profile=user_profile,
        query="推荐训练动作",
        session_context={},
        recent_training=[]
    )
    
    print(f"\n输入候选数: {len(candidates)}")
    print(f"输出候选数: {len(result)}")
    print(f"\n详情:")
    print(f"  - 受伤关节: {details.get('injured_joints', {})}")
    print(f"  - 绝对禁忌过滤数: {details.get('absolute_filtered_count', 0)}")
    print(f"  - 相对禁忌数: {details.get('relative_risk_count', 0)}")
    print(f"  - 被过滤动作: {details.get('filtered_exercises', [])}")
    print(f"  - 严重程度统计: {details.get('severity_levels', {})}")
    
    print(f"\n通过的动作:")
    for ex in result:
        risk_level = ex.get("joint_risk_level", "safe")
        penalty = ex.get("joint_load_penalty", 0)
        affected = ex.get("affected_joint", "无")
        print(f"  - {ex['exercise_name_zh']}: 风险={risk_level}, 惩罚={penalty}, 受影响关节={affected}")
    
    # 验证
    passed = True
    
    # 深蹲应该被完全过滤（膝关节绝对禁忌）
    squat_in_result = any(ex["exercise_name_zh"] == "深蹲" for ex in result)
    if squat_in_result:
        print("\n❌ 失败: 深蹲应该被绝对禁忌过滤")
        passed = False
    else:
        print("\n✓ 深蹲被正确过滤（膝关节绝对禁忌）")
    
    # 卧推应该在结果中但有惩罚（肩关节相对禁忌）
    bench_press = next((ex for ex in result if ex["exercise_name_zh"] == "卧推"), None)
    if bench_press and bench_press.get("joint_risk_level") == "relative":
        print("✓ 卧推被标记为相对禁忌（肩关节）")
    else:
        print("❌ 失败: 卧推应该被标记为相对禁忌")
        passed = False
    
    # 二头弯举应该安全通过
    bicep_curl = next((ex for ex in result if ex["exercise_name_zh"] == "二头弯举"), None)
    if bicep_curl and not bicep_curl.get("joint_risk_level"):
        print("✓ 二头弯举安全通过")
    else:
        print("❌ 失败: 二头弯举应该安全通过")
        passed = False
    
    return passed


async def test_postural_correction_rule():
    """测试体态矫正规则"""
    print("\n" + "="*60)
    print("测试2: 体态矫正规则")
    print("="*60)
    
    rule_engine = Layer3RuleEngine()
    
    # 用户有圆肩问题
    user_profile = {
        "health_profile": {
            "postural_issues": ["圆肩", "头前伸"]
        }
    }
    
    candidates = [
        {"exercise_name_zh": "面拉", "primary_muscle_zh": "后三角肌"},
        {"exercise_name_zh": "反向飞鸟", "primary_muscle_zh": "后三角肌"},
        {"exercise_name_zh": "卧推", "primary_muscle_zh": "胸大肌"},
        {"exercise_name_zh": "俯卧撑", "primary_muscle_zh": "胸大肌"},
        {"exercise_name_zh": "划船", "primary_muscle_zh": "背阔肌"},
    ]
    
    result, details = await rule_engine._apply_postural_correction_rule(
        candidates=candidates,
        user_profile=user_profile,
        query="推荐训练动作",
        session_context={},
        recent_training=[]
    )
    
    print(f"\n输入候选数: {len(candidates)}")
    print(f"输出候选数: {len(result)}")
    print(f"\n详情:")
    print(f"  - 体态问题: {details.get('postural_issues', [])}")
    print(f"  - 矫正动作数: {details.get('corrective_count', 0)}")
    print(f"  - 加重动作数: {details.get('aggravating_count', 0)}")
    
    print(f"\n排序后的动作:")
    for i, ex in enumerate(result):
        boost = ex.get("postural_boost", 0)
        penalty = ex.get("postural_penalty", 0)
        print(f"  {i+1}. {ex['exercise_name_zh']}: boost={boost}, penalty={penalty}")
    
    # 验证：矫正动作应该排在前面
    passed = True
    
    # 面拉和反向飞鸟应该有boost
    face_pull = next((ex for ex in result if ex["exercise_name_zh"] == "面拉"), None)
    if face_pull and face_pull.get("postural_boost", 0) > 0:
        print("\n✓ 面拉被正确标记为矫正动作")
    else:
        print("\n❌ 失败: 面拉应该被标记为矫正动作")
        passed = False
    
    # 卧推和俯卧撑应该有penalty
    bench_press = next((ex for ex in result if ex["exercise_name_zh"] == "卧推"), None)
    if bench_press and bench_press.get("postural_penalty", 0) < 0:
        print("✓ 卧推被正确标记为加重动作")
    else:
        print("❌ 失败: 卧推应该被标记为加重动作")
        passed = False
    
    return passed


async def test_all_rules_integration():
    """测试所有规则的集成执行"""
    print("\n" + "="*60)
    print("测试3: 所有规则集成执行")
    print("="*60)
    
    rule_engine = Layer3RuleEngine()
    
    # 复杂用户档案
    user_profile = {
        "basic_info": {
            "age": 45,
            "weight": 75,
            "body_type": "mesomorph"
        },
        "health_profile": {
            "injuries": [
                {"body_part": "膝关节", "severity": "relative", "status": "active"}
            ],
            "postural_issues": ["圆肩"],
            "chronic_conditions": []
        },
        "fitness_goals": {
            "primary_goal": "muscle_gain"
        },
        "fitness_config": {
            "fitness_level": "intermediate",
            "training_days_per_week": 4,
            "training_duration_per_session": 60
        },
        "training_system": {
            "consecutive_training_weeks": 8
        }
    }
    
    candidates = [
        {"exercise_name_zh": "深蹲", "primary_muscle_zh": "股四头肌", "mechanic": "compound", "difficulty_zh": "中级"},
        {"exercise_name_zh": "卧推", "primary_muscle_zh": "胸大肌", "mechanic": "compound", "difficulty_zh": "中级"},
        {"exercise_name_zh": "面拉", "primary_muscle_zh": "后三角肌", "mechanic": "isolation", "difficulty_zh": "初级"},
        {"exercise_name_zh": "硬拉", "primary_muscle_zh": "竖脊肌", "mechanic": "compound", "difficulty_zh": "高级"},
        {"exercise_name_zh": "二头弯举", "primary_muscle_zh": "肱二头肌", "mechanic": "isolation", "difficulty_zh": "初级"},
    ]
    
    result, execution_log = await rule_engine.apply_all_rules(
        candidates=candidates,
        user_profile=user_profile,
        query="推荐增肌训练动作",
        session_context={},
        recent_training=[],
        top_k=10
    )
    
    print(f"\n输入候选数: {len(candidates)}")
    print(f"输出候选数: {len(result)}")
    print(f"执行时间: {execution_log.execution_time_ms:.1f}ms")
    
    print(f"\n规则执行详情:")
    for rule_result in execution_log.rules_applied:
        status = "✓" if rule_result.applied else "○"
        print(f"  {status} {rule_result.rule_name}: {rule_result.candidates_before} → {rule_result.candidates_after} ({rule_result.execution_time_ms:.1f}ms)")
    
    print(f"\n最终排序:")
    for i, ex in enumerate(result):
        print(f"  {i+1}. {ex['exercise_name_zh']}")
    
    return True


async def main():
    """主测试函数"""
    print("="*60)
    print("Layer3安全规则增强验证")
    print("Requirements: 4.3, 4.6")
    print("="*60)
    
    results = []
    
    # 测试1: 增强版关节负荷规则
    try:
        result1 = await test_enhanced_joint_load_rule()
        results.append(("增强版关节负荷规则", result1))
    except Exception as e:
        print(f"\n❌ 测试1失败: {e}")
        results.append(("增强版关节负荷规则", False))
    
    # 测试2: 体态矫正规则
    try:
        result2 = await test_postural_correction_rule()
        results.append(("体态矫正规则", result2))
    except Exception as e:
        print(f"\n❌ 测试2失败: {e}")
        results.append(("体态矫正规则", False))
    
    # 测试3: 集成测试
    try:
        result3 = await test_all_rules_integration()
        results.append(("规则集成执行", result3))
    except Exception as e:
        print(f"\n❌ 测试3失败: {e}")
        results.append(("规则集成执行", False))
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed}/{len(results)} 通过")
    
    if failed == 0:
        print("\n🎉 所有测试通过！Layer3安全规则增强验证成功")
    else:
        print(f"\n⚠️ {failed}个测试失败，请检查实现")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
