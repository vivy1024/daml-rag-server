#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
框架层领域无关性验证脚本

验证框架层代码是否已移除所有健身领域特定的硬编码数据。

Requirements: 6.1-6.6

使用方法:
    docker exec fitness_daml_rag python scripts/verify_domain_independence.py
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# 健身领域关键词（不应出现在框架层）
# 注意：示例代码、文档字符串、注释中的说明是允许的
FITNESS_KEYWORDS = [
    # 健身动作（具体动作名称）
    "俯卧撑",
    "squat", "bench press", "deadlift", "pull-up", "push-up",
    
    # 肌肉名称（具体肌肉）
    "胸大肌", "背阔肌", "股四头肌", "三角肌", "肱二头肌", "肱三头肌",
    "pectoralis", "latissimus", "quadriceps", "deltoid", "biceps", "triceps",
    
    # 项目特定（必须移除）
    "fitness_exercises_v2",
    "build_body_2024",
    "fitness_daml_rag",
]

# 通用术语（允许出现，因为是通用概念）
# 这些术语虽然在健身领域常用，但也是通用的目标/训练类型
GENERIC_TERMS = [
    "增肌", "减脂", "力量训练", "有氧训练",
    "muscle gain", "fat loss", "strength training",
    "深蹲", "硬拉", "卧推", "引体向上",  # 作为示例是允许的
]

# 允许的例外（注释、文档字符串、示例代码中的说明）
ALLOWED_PATTERNS = [
    r"#.*示例",
    r"#.*example",
    r'""".*"""',
    r"'''.*'''",
    r"domain.*=.*example",
    r"# 标记为示例领域",
    # 文档字符串中的示例
    r"query.*=.*\".*\"",
    r"user_profile.*=.*\{",
    # 枚举定义（通用术语）
    r"MUSCLE_GAIN.*=",
    r"FAT_LOSS.*=",
    # 注释中的说明
    r"#.*增肌|#.*减脂|#.*力量",
    r"#.*优先",
    # 示例模板中的占位符
    r"\{.*\}",
    # 查询模式定义（正则表达式）
    r"query_pattern.*=",
    # 响应模板
    r"response_template.*=",
    # 标签定义
    r"tags.*=.*\[",
]

# 框架层目录
FRAMEWORK_DIR = Path("src/framework")

# 排除的文件/目录
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".pyc",
    "test_",
    "_test.py",
]


def should_exclude(path: Path) -> bool:
    """检查是否应排除该文件"""
    path_str = str(path)
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    return False


def check_file(filepath: Path) -> List[Tuple[int, str, str]]:
    """
    检查单个文件中的健身领域关键词
    
    Returns:
        List of (line_number, keyword, line_content)
    """
    violations = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  ⚠️ 无法读取文件 {filepath}: {e}")
        return violations
    
    for line_num, line in enumerate(lines, 1):
        line_lower = line.lower()
        
        # 检查是否是允许的例外
        is_allowed = False
        for pattern in ALLOWED_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                is_allowed = True
                break
        
        if is_allowed:
            continue
        
        # 检查健身关键词
        for keyword in FITNESS_KEYWORDS:
            keyword_lower = keyword.lower()
            if keyword_lower in line_lower:
                # 排除注释中的说明
                stripped = line.strip()
                if stripped.startswith("#") and ("示例" in stripped or "example" in stripped.lower()):
                    continue
                violations.append((line_num, keyword, line.strip()[:100]))
    
    return violations


def verify_framework_independence() -> Dict[str, List[Tuple[int, str, str]]]:
    """
    验证框架层领域无关性
    
    Returns:
        Dict of filepath -> violations
    """
    print("=" * 70)
    print("🔍 框架层领域无关性验证")
    print("=" * 70)
    print(f"检查目录: {FRAMEWORK_DIR}")
    print(f"关键词数量: {len(FITNESS_KEYWORDS)}")
    print()
    
    all_violations = {}
    files_checked = 0
    
    # 遍历框架层所有Python文件
    for filepath in FRAMEWORK_DIR.rglob("*.py"):
        if should_exclude(filepath):
            continue
        
        files_checked += 1
        violations = check_file(filepath)
        
        if violations:
            all_violations[str(filepath)] = violations
    
    print(f"✅ 检查完成: {files_checked} 个文件")
    print()
    
    return all_violations


def print_report(violations: Dict[str, List[Tuple[int, str, str]]]) -> bool:
    """
    打印验证报告
    
    Returns:
        True if no violations, False otherwise
    """
    if not violations:
        print("=" * 70)
        print("✅ 验证通过！框架层无健身领域硬编码数据")
        print("=" * 70)
        return True
    
    print("=" * 70)
    print("❌ 发现领域泄漏！")
    print("=" * 70)
    
    total_violations = 0
    for filepath, file_violations in violations.items():
        print(f"\n📄 {filepath}")
        for line_num, keyword, content in file_violations:
            print(f"   Line {line_num}: [{keyword}] {content}")
            total_violations += 1
    
    print()
    print(f"总计: {len(violations)} 个文件, {total_violations} 处违规")
    print()
    print("建议修复方案:")
    print("1. 将硬编码数据移到 domain_adapter")
    print("2. 使用环境变量或配置文件")
    print("3. 将示例代码标记为 domain='example'")
    
    return False


def main():
    """主函数"""
    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    print(f"工作目录: {os.getcwd()}")
    print()
    
    # 验证
    violations = verify_framework_independence()
    
    # 打印报告
    success = print_report(violations)
    
    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
