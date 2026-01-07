#!/usr/bin/env python3
"""
修正MCP引用脚本
将所有comprehensive-fitness-coach-stdio引用改为python_builtin（表示Python内置工具）
"""

import os
import re
from pathlib import Path

# 需要修正的文件列表
FILES_TO_FIX = [
    "src/framework/clients/mcp_tool_manager.py",
    "src/applications/fitness/enhanced_dag_orchestrator.py",
    "scripts/validation/checkpoint_validation.py",
    "scripts/mcp/validate_mcp_mounts.py",
]

# 替换规则
REPLACEMENTS = {
    '"comprehensive-fitness-coach-stdio"': '"python_builtin"',
    "'comprehensive-fitness-coach-stdio'": "'python_builtin'",
    "comprehensive-fitness-coach-stdio": "python_builtin",
}

def fix_file(file_path: Path) -> bool:
    """修正单个文件"""
    if not file_path.exists():
        print(f"⚠️  文件不存在: {file_path}")
        return False
    
    try:
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 执行替换
        for old, new in REPLACEMENTS.items():
            content = content.replace(old, new)
        
        # 如果有变更，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 已修正: {file_path}")
            return True
        else:
            print(f"ℹ️  无需修正: {file_path}")
            return False
    
    except Exception as e:
        print(f"❌ 修正失败: {file_path}, 错误: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始修正MCP引用...")
    print("=" * 60)
    
    base_dir = Path(__file__).parent.parent
    fixed_count = 0
    
    for file_rel_path in FILES_TO_FIX:
        file_path = base_dir / file_rel_path
        if fix_file(file_path):
            fixed_count += 1
    
    print("=" * 60)
    print(f"✅ 修正完成！共修正 {fixed_count} 个文件")
    print("\n📝 说明:")
    print("  - comprehensive-fitness-coach-stdio → python_builtin")
    print("  - python_builtin 表示Python内置工具（15个）")
    print("  - user-profile-stdio 保持不变（TypeScript stdio MCP）")

if __name__ == "__main__":
    main()
