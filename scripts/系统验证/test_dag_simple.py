#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/app')

print("="*80)
print("开始测试")
print("="*80)

try:
    print("1. 导入模块...")
    from src.applications.fitness.dag_template_system import DAGTemplateManager
    print("✅ 导入成功")
    
    print("\n2. 初始化模板管理器...")
    manager = DAGTemplateManager()
    print(f"✅ 加载了 {len(manager.get_all_templates())} 个模板")
    
    print("\n3. 列出所有模板:")
    for template in manager.get_all_templates():
        print(f"   - {template.name} ({template.template_id})")
    
    print("\n="*80)
    print("✅ 测试完成")
    print("="*80)
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
