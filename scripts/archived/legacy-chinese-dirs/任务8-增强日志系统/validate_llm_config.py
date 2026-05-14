#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证LLM响应配置文件的完整性

检查项：
1. 所有9个模板都有配置
2. 每个模板包含所有必需字段
3. 参数范围合理
4. 提示词模板包含必需的占位符
"""

import yaml
import sys
from pathlib import Path

# 必需的模板ID列表
REQUIRED_TEMPLATES = [
    "greeting",
    "complete_training_plan",
    "nutrition_planning",
    "safety_assessment",
    "exercise_optimization",
    "comprehensive_fitness",
    "quick_consultation",
    "progress_analysis",
    "rehabilitation_training"
]

# 必需的配置字段
REQUIRED_FIELDS = [
    "max_tokens",
    "temperature",
    "response_style",
    "tone",
    "length_constraint",
    "prompt_template"
]

# 提示词模板中的必需占位符
REQUIRED_PLACEHOLDERS = {
    "greeting": ["{query}", "{response_hint}"],
    "quick_consultation": ["{query}", "{user_profile}", "{response_hint}"],
    "default": ["{query}", "{user_profile}", "{mcp_tools_count}", "{retrieval_count}", "{response_hint}"]
}


def validate_config():
    """验证配置文件"""
    config_path = Path(__file__).parent.parent / "config" / "llm_response_config.yaml"
    
    print(f"📋 验证配置文件: {config_path}")
    print("=" * 60)
    
    # 1. 加载配置文件
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print("✅ YAML格式正确")
    except Exception as e:
        print(f"❌ YAML格式错误: {e}")
        return False
    
    # 2. 检查顶层结构
    if 'templates' not in config:
        print("❌ 缺少 'templates' 顶层键")
        return False
    
    if 'default' not in config:
        print("❌ 缺少 'default' 默认配置")
        return False
    
    print("✅ 顶层结构正确")
    
    # 3. 检查所有模板是否存在
    templates = config['templates']
    missing_templates = []
    for template_id in REQUIRED_TEMPLATES:
        if template_id not in templates:
            missing_templates.append(template_id)
    
    if missing_templates:
        print(f"❌ 缺少模板: {missing_templates}")
        return False
    
    print(f"✅ 所有9个模板都存在")
    
    # 4. 检查每个模板的字段
    all_valid = True
    for template_id in REQUIRED_TEMPLATES:
        template_config = templates[template_id]
        
        # 检查必需字段
        missing_fields = []
        for field in REQUIRED_FIELDS:
            if field not in template_config:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ 模板 {template_id} 缺少字段: {missing_fields}")
            all_valid = False
            continue
        
        # 检查参数范围
        max_tokens = template_config['max_tokens']
        temperature = template_config['temperature']
        
        if not (50 <= max_tokens <= 20000):
            print(f"❌ 模板 {template_id} 的 max_tokens={max_tokens} 超出范围 [50, 20000]")
            all_valid = False
        
        if not (0.0 <= temperature <= 1.0):
            print(f"❌ 模板 {template_id} 的 temperature={temperature} 超出范围 [0.0, 1.0]")
            all_valid = False
        
        # 检查提示词模板占位符
        prompt_template = template_config['prompt_template']
        
        # 根据模板类型选择必需占位符
        if template_id == "greeting":
            required_placeholders = REQUIRED_PLACEHOLDERS["greeting"]
        elif template_id == "quick_consultation":
            required_placeholders = REQUIRED_PLACEHOLDERS["quick_consultation"]
        else:
            required_placeholders = REQUIRED_PLACEHOLDERS["default"]
        
        missing_placeholders = []
        for placeholder in required_placeholders:
            if placeholder not in prompt_template:
                missing_placeholders.append(placeholder)
        
        if missing_placeholders:
            print(f"❌ 模板 {template_id} 的提示词缺少占位符: {missing_placeholders}")
            all_valid = False
        
        if all_valid:
            print(f"✅ 模板 {template_id}: max_tokens={max_tokens}, temperature={temperature}")
    
    # 5. 检查默认配置
    default_config = config['default']
    missing_fields = []
    for field in REQUIRED_FIELDS:
        if field not in default_config:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"❌ 默认配置缺少字段: {missing_fields}")
        all_valid = False
    else:
        print(f"✅ 默认配置完整")
    
    # 6. 总结
    print("=" * 60)
    if all_valid:
        print("🎉 配置文件验证通过！")
        print(f"\n📊 统计信息:")
        print(f"   - 模板数量: {len(templates)}")
        print(f"   - 最小 max_tokens: {min(t['max_tokens'] for t in templates.values())}")
        print(f"   - 最大 max_tokens: {max(t['max_tokens'] for t in templates.values())}")
        print(f"   - 最低 temperature: {min(t['temperature'] for t in templates.values())}")
        print(f"   - 最高 temperature: {max(t['temperature'] for t in templates.values())}")
        return True
    else:
        print("❌ 配置文件验证失败")
        return False


if __name__ == "__main__":
    success = validate_config()
    sys.exit(0 if success else 1)
