#!/usr/bin/env python3
"""
LLM响应配置管理器演示脚本

演示如何使用LLMResponseConfigManager加载配置、获取配置、构建提示词

使用方法：
    python scripts/demo_config_manager.py
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.framework.config import LLMResponseConfigManager
import json


def main():
    print("=" * 80)
    print("LLM响应配置管理器演示")
    print("=" * 80)
    print()
    
    # 1. 初始化配置管理器
    print("1️⃣  初始化配置管理器...")
    manager = LLMResponseConfigManager()
    print(f"   ✅ 成功加载 {len(manager.configs)} 个模板配置")
    print()
    
    # 2. 列出所有模板ID
    print("2️⃣  所有可用的模板ID:")
    template_ids = manager.get_all_template_ids()
    for i, template_id in enumerate(template_ids, 1):
        print(f"   {i}. {template_id}")
    print()
    
    # 3. 获取greeting模板配置
    print("3️⃣  获取greeting模板配置:")
    greeting_config = manager.get_config("greeting")
    print(f"   - max_tokens: {greeting_config.max_tokens}")
    print(f"   - temperature: {greeting_config.temperature}")
    print(f"   - response_style: {greeting_config.response_style}")
    print(f"   - tone: {greeting_config.tone}")
    print(f"   - length_constraint: {greeting_config.length_constraint}")
    print()
    
    # 4. 构建greeting提示词
    print("4️⃣  构建greeting提示词:")
    greeting_prompt = manager.build_prompt(
        "greeting",
        query="你好",
        response_hint="简短友好，1-2句话"
    )
    print("   " + "-" * 76)
    print("   " + greeting_prompt.replace("\n", "\n   "))
    print("   " + "-" * 76)
    print()
    
    # 5. 获取complete_training_plan模板配置
    print("5️⃣  获取complete_training_plan模板配置:")
    plan_config = manager.get_config("complete_training_plan")
    print(f"   - max_tokens: {plan_config.max_tokens}")
    print(f"   - temperature: {plan_config.temperature}")
    print(f"   - response_style: {plan_config.response_style}")
    print(f"   - tone: {plan_config.tone}")
    print(f"   - length_constraint: {plan_config.length_constraint[:50]}...")
    print()
    
    # 6. 构建complete_training_plan提示词
    print("6️⃣  构建complete_training_plan提示词（前300字）:")
    user_profile = {
        "name": "测试用户",
        "age": 25,
        "goal": "增肌"
    }
    plan_prompt = manager.build_prompt(
        "complete_training_plan",
        query="制定一个4周的增肌训练计划",
        user_profile=json.dumps(user_profile, ensure_ascii=False),
        response_hint="详细专业的分析和建议",
        mcp_tools_count=5,
        retrieval_count=10
    )
    print("   " + "-" * 76)
    print("   " + plan_prompt[:300].replace("\n", "\n   ") + "...")
    print("   " + "-" * 76)
    print()
    
    # 7. 测试未知模板（使用默认配置）
    print("7️⃣  测试未知模板（使用默认配置）:")
    unknown_config = manager.get_config("unknown_template")
    print(f"   - max_tokens: {unknown_config.max_tokens}")
    print(f"   - temperature: {unknown_config.temperature}")
    print(f"   - response_style: {unknown_config.response_style}")
    print()
    
    # 8. 检查模板是否存在
    print("8️⃣  检查模板是否存在:")
    print(f"   - greeting存在: {manager.has_config('greeting')}")
    print(f"   - unknown_template存在: {manager.has_config('unknown_template')}")
    print()
    
    print("=" * 80)
    print("演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
