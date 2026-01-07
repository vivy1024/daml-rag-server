#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试安全工具对severity字段的使用

验证三个安全工具是否正确使用了severity字段：
1. contraindications_checker - 禁忌症检查器
2. safe_exercise_modifier - 安全动作修饰器
3. injury_risk_assessor - 损伤风险评估器

版本: v1.0.0
日期: 2025-12-15
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.infrastructure.neo4j_client import Neo4jClient
from src.applications.fitness.mcp_tools.safety.contraindications_checker import ContraindicationsChecker
from src.applications.fitness.mcp_tools.safety.safe_exercise_modifier import SafeExerciseModifier
from src.applications.fitness.mcp_tools.safety.injury_risk_assessor import InjuryRiskAssessor


async def test_contraindications_checker():
    """测试禁忌症检查器"""
    print("\n" + "="*80)
    print("测试1: contraindications_checker - 禁忌症检查器")
    print("="*80)
    
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    
    checker = ContraindicationsChecker(neo4j_client=neo4j_client)
    
    # 测试场景1: 肩袖损伤患者检查肩推动作（应该是绝对禁忌）
    print("\n场景1: 肩袖损伤患者检查肩推动作")
    print("-" * 80)
    
    input_data = {
        "user_id": "test_user_001",
        "exercise_ids": ["1"],  # 假设ID 1是肩推类动作
        "health_conditions": ["肩袖损伤"],
        "include_recommendations": True,
        "strict_mode": False
    }
    
    try:
        result = await checker.execute(input_data)
        
        if result["success"]:
            print(f"✅ 检查成功")
            print(f"检查动作数: {result['checked_exercises']}")
            print(f"有禁忌的动作数: {result['exercises_with_contraindications']}")
            print(f"高风险动作数: {result['high_risk_exercises']}")
            
            for exercise_result in result["exercise_results"]:
                print(f"\n动作: {exercise_result['exercise_name_zh']}")
                print(f"  有禁忌: {exercise_result['has_contraindications']}")
                print(f"  风险等级: {exercise_result['max_risk_level']}")
                
                if exercise_result["contraindications"]:
                    print(f"  禁忌症详情:")
                    for contra in exercise_result["contraindications"]:
                        severity = contra.get("severity", "未知")
                        print(f"    - {contra['contraindication_type']}")
                        print(f"      严重程度: {severity}")
                        print(f"      原因: {contra['reason']}")
                
                print(f"  建议:")
                recs = exercise_result["recommendations"]
                print(f"    可以执行: {recs['can_perform']}")
                if recs["precautions"]:
                    print(f"    注意事项: {', '.join(recs['precautions'][:2])}")
        else:
            print(f"❌ 检查失败")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    await neo4j_client.close()


async def test_safe_exercise_modifier():
    """测试安全动作修饰器"""
    print("\n" + "="*80)
    print("测试2: safe_exercise_modifier - 安全动作修饰器")
    print("="*80)
    
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    
    modifier = SafeExerciseModifier(neo4j_client=neo4j_client)
    
    # 测试场景2: 髌骨软化症患者修饰深蹲动作（应该是绝对禁忌）
    print("\n场景2: 髌骨软化症患者修饰深蹲动作")
    print("-" * 80)
    
    input_data = {
        "user_id": "test_user_002",
        "exercise_id": "100",  # 假设ID 100是深蹲类动作
        "modification_purpose": "rehabilitation",
        "user_injuries": ["髌骨软化症"],
        "modification_preference": "moderate"
    }
    
    try:
        result = await modifier.execute(input_data)
        
        if result["success"]:
            print(f"✅ 修饰成功")
            print(f"原动作: {result['original_exercise']['name_zh']}")
            
            # 禁忌症分析
            contra_analysis = result["contraindications_analysis"]
            print(f"\n禁忌症分析:")
            print(f"  有禁忌: {contra_analysis['has_contraindications']}")
            print(f"  风险等级: {contra_analysis['risk_level']}")
            print(f"  禁忌数量: {contra_analysis['contraindications_count']}")
            
            if contra_analysis["warnings"]:
                print(f"  警告:")
                for warning in contra_analysis["warnings"]:
                    print(f"    - {warning}")
            
            # 修改方案
            print(f"\n修改方案数: {len(result['modifications'])}")
            for i, mod in enumerate(result["modifications"][:2], 1):
                print(f"\n方案{i}: {mod['modification_type']}")
                print(f"  修改后动作: {mod['modified_name_zh']}")
                print(f"  安全评分: {mod['safety_score_before']} → {mod['safety_score_after']}")
                if mod["modifications_applied"]:
                    print(f"  应用的修改: {', '.join(mod['modifications_applied'][:2])}")
            
            # 医学指导
            print(f"\n医学指导:")
            print(f"  {result['medical_guidance'][:200]}...")
        else:
            print(f"❌ 修饰失败")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    await neo4j_client.close()


async def test_injury_risk_assessor():
    """测试损伤风险评估器"""
    print("\n" + "="*80)
    print("测试3: injury_risk_assessor - 损伤风险评估器")
    print("="*80)
    
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    
    assessor = InjuryRiskAssessor(neo4j_client=neo4j_client)
    
    # 测试场景3: 腰椎间盘突出患者评估硬拉动作（应该是绝对禁忌）
    print("\n场景3: 腰椎间盘突出患者评估硬拉动作")
    print("-" * 80)
    
    input_data = {
        "user_id": "test_user_003",
        "planned_exercises": ["200"],  # 假设ID 200是硬拉类动作
        "training_intensity": "moderate",
        "session_duration_minutes": 60,
        "include_prevention_plan": True,
        "risk_tolerance_level": "moderate",
        "previous_injuries": ["腰椎间盘突出"]
    }
    
    try:
        result = await assessor.execute(input_data)
        
        if result["success"]:
            print(f"✅ 评估成功")
            print(f"总体风险等级: {result['overall_risk_level']}")
            print(f"总体风险评分: {result['overall_risk_score']:.1f}")
            print(f"风险总结: {result['risk_summary']}")
            
            # 个人风险因素
            print(f"\n个人风险因素数: {len(result['personal_risk_factors'])}")
            for factor in result["personal_risk_factors"][:3]:
                print(f"  - {factor['category']}: {factor['factor']}")
                print(f"    风险等级: {factor['risk_level']}, 评分: {factor['score']}")
                print(f"    描述: {factor['description'][:80]}...")
            
            # 动作风险档案
            print(f"\n动作风险档案:")
            for profile in result["exercise_risk_profiles"]:
                print(f"  动作: {profile['exercise_name_zh']}")
                print(f"    固有风险: {profile['inherent_risk']:.1f}")
                print(f"    用户特定风险: {profile['user_specific_risk']:.1f}")
                print(f"    综合风险: {profile['combined_risk_score']:.1f}")
                print(f"    风险等级: {profile['risk_level']}")
                
                if profile["risk_factors"]:
                    print(f"    风险因素:")
                    for rf in profile["risk_factors"][:2]:
                        print(f"      - {rf['category']}: {rf['factor']}")
            
            # 建议
            if result["recommendations"]:
                print(f"\n建议:")
                for rec in result["recommendations"][:3]:
                    print(f"  - {rec}")
        else:
            print(f"❌ 评估失败")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    await neo4j_client.close()


async def verify_severity_field_in_db():
    """验证数据库中是否存在severity字段"""
    print("\n" + "="*80)
    print("验证: 数据库中的severity字段")
    print("="*80)
    
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    
    # 查询示例关系
    query = """
    MATCH (e:Exercise)-[r:CONTRAINDICATED_FOR]->(i:InjuryType)
    WHERE r.severity IS NOT NULL
    RETURN 
      e.name_zh as exercise_name,
      i.name_zh as injury_name,
      r.severity as severity,
      r.reason as reason
    LIMIT 10
    """
    
    try:
        result = await neo4j_client.query(query, {})
        
        if result.records:
            print(f"\n✅ 找到{len(result.records)}个包含severity字段的关系")
            print("\n示例关系:")
            print("-" * 80)
            
            severity_counts = {"absolute": 0, "relative": 0, "caution": 0}
            
            for i, record in enumerate(result.records[:5], 1):
                exercise_name = record.get("exercise_name", "Unknown")
                injury_name = record.get("injury_name", "Unknown")
                severity = record.get("severity", "Unknown")
                reason = record.get("reason", "")
                
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
                
                print(f"\n{i}. {exercise_name} → {injury_name}")
                print(f"   严重程度: {severity}")
                print(f"   原因: {reason[:80]}...")
            
            # 统计所有severity分布
            count_query = """
            MATCH (e:Exercise)-[r:CONTRAINDICATED_FOR]->(i:InjuryType)
            WHERE r.severity IS NOT NULL
            RETURN r.severity as severity, count(*) as count
            ORDER BY count DESC
            """
            
            count_result = await neo4j_client.query(count_query, {})
            
            print("\n" + "-" * 80)
            print("Severity字段分布:")
            for record in count_result.records:
                severity = record.get("severity", "Unknown")
                count = record.get("count", 0)
                print(f"  {severity}: {count}个关系")
        else:
            print(f"\n⚠️ 未找到包含severity字段的关系")
            print("可能原因:")
            print("  1. Phase 1/2/3尚未执行")
            print("  2. 关系创建时未添加severity字段")
    
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    
    await neo4j_client.close()


async def main():
    """主测试函数"""
    print("\n" + "="*80)
    print("安全工具Severity字段使用测试")
    print("="*80)
    print("\n测试目标:")
    print("1. 验证数据库中是否存在severity字段")
    print("2. 测试contraindications_checker是否正确使用severity")
    print("3. 测试safe_exercise_modifier是否正确使用severity")
    print("4. 测试injury_risk_assessor是否正确使用severity")
    
    # 验证数据库
    await verify_severity_field_in_db()
    
    # 测试三个工具
    await test_contraindications_checker()
    await test_safe_exercise_modifier()
    await test_injury_risk_assessor()
    
    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
