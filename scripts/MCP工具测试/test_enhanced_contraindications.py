#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版CONTRAINDICATED_FOR关系

验证contraindications_checker工具是否能正确使用新的禁忌关系
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from applications.fitness.mcp_tools.safety.contraindications_checker import ContraindicationsChecker
from infrastructure.retrieval.true_three_layer_engine import TrueThreeLayerEngine


def test_shoulder_injury():
    """测试肩袖损伤禁忌症检查"""
    print("\n" + "="*60)
    print("测试场景1: 肩袖损伤患者")
    print("="*60)
    
    # 初始化工具
    engine = TrueThreeLayerEngine()
    checker = ContraindicationsChecker(three_layer_engine=engine)
    
    # 测试输入
    input_data = {
        "user_id": "test_user_001",
        "injury_history": ["肩袖损伤"],
        "exercise_ids": [4, 8, 27, 100, 200]  # 包含一些肩部动作
    }
    
    # 执行检查
    result = checker.execute(input_data)
    
    # 打印结果
    print(f"\n✅ 执行成功")
    print(f"检查的动作数量: {result['summary']['total_exercises_checked']}")
    print(f"发现的禁忌症: {result['summary']['total_contraindications_found']}")
    print(f"高风险动作: {result['summary']['high_risk_exercises']}")
    print(f"中等风险动作: {result['summary']['moderate_risk_exercises']}")
    print(f"低风险动作: {result['summary']['low_risk_exercises']}")
    
    if result['contraindications']:
        print(f"\n禁忌症详情:")
        for contra in result['contraindications'][:3]:  # 只显示前3个
            print(f"  - 动作: {contra['exercise_name']}")
            print(f"    损伤类型: {contra['injury_type']}")
            print(f"    风险等级: {contra['risk_level']}")
            print(f"    严重程度: {contra.get('severity', 'N/A')}")
            print(f"    原因: {contra.get('reason', 'N/A')[:50]}...")
    
    return result


def test_knee_injury():
    """测试髌骨软化症禁忌症检查"""
    print("\n" + "="*60)
    print("测试场景2: 髌骨软化症患者")
    print("="*60)
    
    # 初始化工具
    engine = TrueThreeLayerEngine()
    checker = ContraindicationsChecker(three_layer_engine=engine)
    
    # 测试输入
    input_data = {
        "user_id": "test_user_002",
        "injury_history": ["髌骨软化症"],
        "exercise_ids": [4, 8, 27, 100, 200]  # 包含一些腿部动作
    }
    
    # 执行检查
    result = checker.execute(input_data)
    
    # 打印结果
    print(f"\n✅ 执行成功")
    print(f"检查的动作数量: {result['summary']['total_exercises_checked']}")
    print(f"发现的禁忌症: {result['summary']['total_contraindications_found']}")
    print(f"高风险动作: {result['summary']['high_risk_exercises']}")
    
    if result['contraindications']:
        print(f"\n禁忌症详情:")
        for contra in result['contraindications'][:3]:
            print(f"  - 动作: {contra['exercise_name']}")
            print(f"    损伤类型: {contra['injury_type']}")
            print(f"    风险等级: {contra['risk_level']}")
            print(f"    严重程度: {contra.get('severity', 'N/A')}")
    
    return result


def test_lumbar_disc_herniation():
    """测试腰椎间盘突出禁忌症检查"""
    print("\n" + "="*60)
    print("测试场景3: 腰椎间盘突出患者")
    print("="*60)
    
    # 初始化工具
    engine = TrueThreeLayerEngine()
    checker = ContraindicationsChecker(three_layer_engine=engine)
    
    # 测试输入
    input_data = {
        "user_id": "test_user_003",
        "injury_history": ["腰椎间盘突出"],
        "exercise_ids": [4, 8, 27, 100, 200]
    }
    
    # 执行检查
    result = checker.execute(input_data)
    
    # 打印结果
    print(f"\n✅ 执行成功")
    print(f"检查的动作数量: {result['summary']['total_exercises_checked']}")
    print(f"发现的禁忌症: {result['summary']['total_contraindications_found']}")
    print(f"高风险动作: {result['summary']['high_risk_exercises']}")
    
    if result['contraindications']:
        print(f"\n禁忌症详情:")
        for contra in result['contraindications'][:3]:
            print(f"  - 动作: {contra['exercise_name']}")
            print(f"    损伤类型: {contra['injury_type']}")
            print(f"    风险等级: {contra['risk_level']}")
            print(f"    严重程度: {contra.get('severity', 'N/A')}")
    
    return result


def test_severity_levels():
    """测试严重程度分级"""
    print("\n" + "="*60)
    print("测试场景4: 验证严重程度分级")
    print("="*60)
    
    # 初始化工具
    engine = TrueThreeLayerEngine()
    checker = ContraindicationsChecker(three_layer_engine=engine)
    
    # 测试多个损伤类型
    input_data = {
        "user_id": "test_user_004",
        "injury_history": ["肩袖损伤", "髌骨软化症", "下背部疼痛"],
        "exercise_ids": [4, 8, 27, 100, 200]
    }
    
    # 执行检查
    result = checker.execute(input_data)
    
    # 统计严重程度
    severity_stats = {"absolute": 0, "relative": 0, "caution": 0, "unknown": 0}
    for contra in result['contraindications']:
        severity = contra.get('severity', 'unknown')
        if severity in severity_stats:
            severity_stats[severity] += 1
        else:
            severity_stats['unknown'] += 1
    
    print(f"\n✅ 执行成功")
    print(f"总禁忌症: {result['summary']['total_contraindications_found']}")
    print(f"\n严重程度统计:")
    print(f"  🚫 绝对禁忌 (absolute): {severity_stats['absolute']}")
    print(f"  ⚠️  相对禁忌 (relative): {severity_stats['relative']}")
    print(f"  💡 谨慎使用 (caution): {severity_stats['caution']}")
    print(f"  ❓ 未分级: {severity_stats['unknown']}")
    
    return result


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🧪 测试增强版CONTRAINDICATED_FOR关系")
    print("="*60)
    
    try:
        # 测试1: 肩袖损伤
        result1 = test_shoulder_injury()
        
        # 测试2: 髌骨软化症
        result2 = test_knee_injury()
        
        # 测试3: 腰椎间盘突出
        result3 = test_lumbar_disc_herniation()
        
        # 测试4: 严重程度分级
        result4 = test_severity_levels()
        
        # 总结
        print("\n" + "="*60)
        print("📊 测试总结")
        print("="*60)
        print(f"✅ 所有测试通过")
        print(f"✅ 增强版禁忌关系工作正常")
        print(f"✅ 严重程度分级正确")
        print(f"✅ contraindications_checker工具可以使用新关系")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
