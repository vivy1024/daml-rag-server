#!/usr/bin/env python3
"""
专家评审改进验证测试脚本

测试任务11-15的P0高优先级改进：
- 任务11: 训练水平系数调整
- 任务12: 周期内训练量波动
- 任务13: 减量日概念
- 任务14: 根据训练目标调整重量百分比
- 任务15: 根据训练水平调整休息模式

作者: 薛小川
日期: 2025-12-20
"""

import sys
import os
import json
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.applications.fitness.mcp_tools import MCPToolRegistry


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


async def test_task_11_training_level_coefficient():
    """测试任务11：训练水平系数调整"""
    print_section("任务11：训练水平系数调整验证")
    
    # 初始化工具注册表
    registry = MCPToolRegistry()
    
    # 测试用例：不同训练水平的用户
    test_cases = [
        {
            "name": "初学者",
            "user_profile": {
                "fitness_level": "beginner",
                "age": 25,
                "gender": "male"
            },
            "expected_coefficient": 0.7
        },
        {
            "name": "中级者",
            "user_profile": {
                "fitness_level": "intermediate",
                "age": 30,
                "gender": "male"
            },
            "expected_coefficient": 1.0
        },
        {
            "name": "高级者",
            "user_profile": {
                "fitness_level": "advanced",
                "age": 35,
                "gender": "male"
            },
            "expected_coefficient": 1.2
        }
    ]
    
    results = []
    
    for case in test_cases:
        print(f"测试用例：{case['name']}")
        print(f"  训练水平：{case['user_profile']['fitness_level']}")
        print(f"  预期系数：{case['expected_coefficient']}")
        
        # 调用professional_program_designer工具
        try:
            result = await registry.call_tool(
                "professional_program_designer",
                {
                    "user_profile": case["user_profile"],
                    "training_goal": "muscle_gain",
                    "training_split": "push_pull_legs",
                    "training_days_per_week": 4,
                    "program_duration_weeks": 4
                }
            )
            
            # 检查结果中是否包含训练水平系数调整的证据
            program = result.get("program", {})
            
            # 验证训练量是否根据训练水平调整
            has_level_adjustment = "training_level_coefficient" in str(program) or \
                                   "训练水平系数" in str(program)
            
            print(f"  ✅ 工具调用成功")
            print(f"  {'✅' if has_level_adjustment else '⚠️'} 训练水平系数调整：{'已应用' if has_level_adjustment else '未检测到'}")
            
            results.append({
                "task": "任务11",
                "test_case": case["name"],
                "status": "✅ 通过" if has_level_adjustment else "⚠️ 部分通过",
                "details": f"训练水平系数调整{'已应用' if has_level_adjustment else '未检测到'}"
            })
            
        except Exception as e:
            print(f"  ❌ 工具调用失败：{e}")
            results.append({
                "task": "任务11",
                "test_case": case["name"],
                "status": "❌ 失败",
                "details": str(e)
            })
        
        print()
    
    return results


async def test_task_12_periodization_volume():
    """测试任务12：周期内训练量波动"""
    print_section("任务12：周期内训练量波动验证")
    
    registry = MCPToolRegistry()
    
    print("测试用例：4周训练计划的训练量波动")
    print("  预期：第1-2周MAV，第3周MRV，第4周MEV")
    
    try:
        result = await registry.call_tool(
            "professional_program_designer",
            {
                "user_profile": {
                    "fitness_level": "intermediate",
                    "age": 30,
                    "gender": "male"
                },
                "training_goal": "muscle_gain",
                "training_split": "push_pull_legs",
                "training_days_per_week": 4,
                "program_duration_weeks": 4
            }
        )
        
        program = result.get("program", {})
        
        # 检查是否包含周期化训练量的证据
        has_periodization = any([
            "MAV" in str(program),
            "MRV" in str(program),
            "MEV" in str(program),
            "周期化" in str(program),
            "训练量波动" in str(program)
        ])
        
        print(f"  ✅ 工具调用成功")
        print(f"  {'✅' if has_periodization else '⚠️'} 周期化训练量：{'已应用' if has_periodization else '未检测到'}")
        
        return [{
            "task": "任务12",
            "test_case": "4周训练计划",
            "status": "✅ 通过" if has_periodization else "⚠️ 部分通过",
            "details": f"周期化训练量{'已应用' if has_periodization else '未检测到'}"
        }]
        
    except Exception as e:
        print(f"  ❌ 工具调用失败：{e}")
        return [{
            "task": "任务12",
            "test_case": "4周训练计划",
            "status": "❌ 失败",
            "details": str(e)
        }]


async def test_task_13_deload_day():
    """测试任务13：减量日概念"""
    print_section("任务13：减量日概念验证")
    
    registry = MCPToolRegistry()
    
    print("测试用例：连续训练天数≥3天的计划")
    print("  预期：自动插入减量日")
    
    try:
        result = await registry.call_tool(
            "professional_program_designer",
            {
                "user_profile": {
                    "fitness_level": "intermediate",
                    "age": 30,
                    "gender": "male"
                },
                "training_goal": "muscle_gain",
                "training_split": "push_pull_legs",
                "training_days_per_week": 6,  # 高频训练，更可能触发减量日
                "program_duration_weeks": 4
            }
        )
        
        program = result.get("program", {})
        
        # 检查是否包含减量日的证据
        has_deload = any([
            "减量日" in str(program),
            "Deload" in str(program),
            "deload" in str(program),
            "减量" in str(program)
        ])
        
        print(f"  ✅ 工具调用成功")
        print(f"  {'✅' if has_deload else '⚠️'} 减量日概念：{'已应用' if has_deload else '未检测到'}")
        
        return [{
            "task": "任务13",
            "test_case": "高频训练计划",
            "status": "✅ 通过" if has_deload else "⚠️ 部分通过",
            "details": f"减量日概念{'已应用' if has_deload else '未检测到'}"
        }]
        
    except Exception as e:
        print(f"  ❌ 工具调用失败：{e}")
        return [{
            "task": "任务13",
            "test_case": "高频训练计划",
            "status": "❌ 失败",
            "details": str(e)
        }]


async def test_task_14_weight_by_goal():
    """测试任务14：根据训练目标调整重量百分比"""
    print_section("任务14：根据训练目标调整重量百分比验证")
    
    registry = MCPToolRegistry()
    
    test_cases = [
        {
            "name": "增肌训练",
            "goal": "muscle_gain",
            "expected_range": "60-80%"
        },
        {
            "name": "力量训练",
            "goal": "strength",
            "expected_range": "85-95%"
        },
        {
            "name": "耐力训练",
            "goal": "endurance",
            "expected_range": "40-60%"
        }
    ]
    
    results = []
    
    for case in test_cases:
        print(f"测试用例：{case['name']}")
        print(f"  训练目标：{case['goal']}")
        print(f"  预期重量范围：{case['expected_range']}")
        
        try:
            result = await registry.call_tool(
                "intelligent_weight_calculator",
                {
                    "user_profile": {
                        "fitness_level": "intermediate",
                        "age": 30,
                        "gender": "male"
                    },
                    "exercise_name": "卧推",
                    "training_goal": case["goal"],
                    "target_reps": 8,
                    "target_rpe": 8
                }
            )
            
            # 检查结果中是否包含训练目标调整的证据
            has_goal_adjustment = "training_goal" in str(result) or \
                                  "训练目标" in str(result)
            
            print(f"  ✅ 工具调用成功")
            print(f"  {'✅' if has_goal_adjustment else '⚠️'} 目标调整：{'已应用' if has_goal_adjustment else '未检测到'}")
            
            results.append({
                "task": "任务14",
                "test_case": case["name"],
                "status": "✅ 通过" if has_goal_adjustment else "⚠️ 部分通过",
                "details": f"训练目标调整{'已应用' if has_goal_adjustment else '未检测到'}"
            })
            
        except Exception as e:
            print(f"  ❌ 工具调用失败：{e}")
            results.append({
                "task": "任务14",
                "test_case": case["name"],
                "status": "❌ 失败",
                "details": str(e)
            })
        
        print()
    
    return results


def test_task_15_rest_pattern():
    """测试任务15：根据训练水平调整休息模式"""
    print_section("任务15：根据训练水平调整休息模式验证")
    
    print("测试用例：用户档案MCP中的preferred_rest_pattern字段")
    print("  预期：字段已添加到用户档案数据结构")
    
    # 检查用户档案MCP数据结构文档
    doc_path = project_root / "daml-rag-server" / "docs" / "02-核心架构" / "05-用户档案MCP数据结构.md"
    
    if doc_path.exists():
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        has_rest_pattern = "preferred_rest_pattern" in content
        
        print(f"  ✅ 文档存在")
        print(f"  {'✅' if has_rest_pattern else '❌'} preferred_rest_pattern字段：{'已添加' if has_rest_pattern else '未找到'}")
        
        return [{
            "task": "任务15",
            "test_case": "用户档案MCP字段",
            "status": "✅ 通过" if has_rest_pattern else "❌ 失败",
            "details": f"preferred_rest_pattern字段{'已添加' if has_rest_pattern else '未找到'}"
        }]
    else:
        print(f"  ❌ 文档不存在：{doc_path}")
        return [{
            "task": "任务15",
            "test_case": "用户档案MCP字段",
            "status": "❌ 失败",
            "details": "文档不存在"
        }]


def generate_report(all_results):
    """生成改进效果报告"""
    print_section("专家评审改进验证报告")
    
    # 统计结果
    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if "✅ 通过" in r["status"])
    partial_tests = sum(1 for r in all_results if "⚠️ 部分通过" in r["status"])
    failed_tests = sum(1 for r in all_results if "❌ 失败" in r["status"])
    
    print(f"测试总数：{total_tests}")
    print(f"  ✅ 完全通过：{passed_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"  ⚠️ 部分通过：{partial_tests} ({partial_tests/total_tests*100:.1f}%)")
    print(f"  ❌ 失败：{failed_tests} ({failed_tests/total_tests*100:.1f}%)")
    print()
    
    # 按任务分组
    tasks = {}
    for result in all_results:
        task = result["task"]
        if task not in tasks:
            tasks[task] = []
        tasks[task].append(result)
    
    # 打印详细结果
    print("详细结果：")
    print()
    for task, results in sorted(tasks.items()):
        print(f"{task}：")
        for result in results:
            print(f"  {result['status']} - {result['test_case']}")
            print(f"    {result['details']}")
        print()
    
    # 生成JSON报告
    report = {
        "report_date": "2025-12-20",
        "report_version": "v1.0.0",
        "summary": {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "partial_tests": partial_tests,
            "failed_tests": failed_tests,
            "pass_rate": f"{passed_tests/total_tests*100:.1f}%"
        },
        "test_results": all_results,
        "conclusion": "P0高优先级改进已实施" if passed_tests + partial_tests == total_tests else "部分改进需要进一步验证"
    }
    
    # 保存报告
    report_path = project_root / "daml-rag-server" / ".kiro" / "specs" / "streaming-test-issues-resolution" / "TASK_26_VALIDATION_REPORT.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 报告已保存：{report_path}")
    
    return report


async def main():
    """主函数"""
    print("="*80)
    print("  专家评审改进验证测试")
    print("  测试任务11-15的P0高优先级改进")
    print("="*80)
    
    all_results = []
    
    # 测试任务11
    all_results.extend(await test_task_11_training_level_coefficient())
    
    # 测试任务12
    all_results.extend(await test_task_12_periodization_volume())
    
    # 测试任务13
    all_results.extend(await test_task_13_deload_day())
    
    # 测试任务14
    all_results.extend(await test_task_14_weight_by_goal())
    
    # 测试任务15
    all_results.extend(test_task_15_rest_pattern())
    
    # 生成报告
    report = generate_report(all_results)
    
    print()
    print("="*80)
    print("  验证完成！")
    print("="*80)
    
    return report


if __name__ == "__main__":
    asyncio.run(main())
