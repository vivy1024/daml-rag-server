# -*- coding: utf-8 -*-
"""
日志文件验证脚本

验证日志中是否还存在以下错误：
1. TypeError（None值错误）
2. "No module named 'src.llm'"（模块导入错误）
3. "未知任务类型"警告
4. 验证所有步骤都有完整的日志记录

版本：v1.0.0
创建日期：2025-12-16
"""

import re
import logging
from typing import List, Dict, Tuple

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_log_for_errors(log_content: str) -> Dict[str, any]:
    """
    检查日志内容中的错误

    Args:
        log_content: 日志内容

    Returns:
        dict: 验证结果
    """
    results = {
        "type_errors": [],
        "module_import_errors": [],
        "unknown_task_warnings": [],
        "workflow_steps_complete": False,
        "total_lines": 0
    }

    lines = log_content.split('\n')
    results["total_lines"] = len(lines)

    # 检查TypeError
    type_error_pattern = re.compile(r"TypeError.*NoneType", re.IGNORECASE)
    for i, line in enumerate(lines):
        if type_error_pattern.search(line):
            results["type_errors"].append({
                "line_number": i + 1,
                "content": line.strip()
            })

    # 检查模块导入错误
    module_import_pattern = re.compile(r"No module named ['\"]src\.llm['\"]", re.IGNORECASE)
    for i, line in enumerate(lines):
        if module_import_pattern.search(line):
            results["module_import_errors"].append({
                "line_number": i + 1,
                "content": line.strip()
            })

    # 检查未知任务类型警告
    unknown_task_pattern = re.compile(r"未知任务类型", re.IGNORECASE)
    for i, line in enumerate(lines):
        if unknown_task_pattern.search(line):
            results["unknown_task_warnings"].append({
                "line_number": i + 1,
                "content": line.strip()
            })

    # 检查11步工作流程是否完整
    workflow_steps = [
        "步骤1",
        "步骤2",
        "步骤3",
        "步骤4",
        "步骤5",
        "步骤6",
        "步骤7",
        "步骤8",
        "步骤9",
        "步骤10",
        "步骤11"
    ]

    steps_found = []
    for step in workflow_steps:
        for line in lines:
            if step in line and "✅" in line:
                steps_found.append(step)
                break

    results["workflow_steps_complete"] = len(steps_found) == 11
    results["workflow_steps_found"] = steps_found

    return results


def print_validation_report(results: Dict[str, any]):
    """打印验证报告"""
    logger.info("=" * 80)
    logger.info("日志验证报告")
    logger.info("=" * 80)

    logger.info(f"\n📊 日志统计:")
    logger.info(f"  - 总行数: {results['total_lines']}")

    # TypeError检查
    logger.info(f"\n1️⃣  TypeError检查:")
    if len(results["type_errors"]) == 0:
        logger.info(f"  ✅ 未发现TypeError错误")
    else:
        logger.error(f"  ❌ 发现 {len(results['type_errors'])} 个TypeError错误:")
        for error in results["type_errors"][:5]:  # 只显示前5个
            logger.error(f"    行{error['line_number']}: {error['content'][:100]}")

    # 模块导入错误检查
    logger.info(f"\n2️⃣  模块导入错误检查:")
    if len(results["module_import_errors"]) == 0:
        logger.info(f"  ✅ 未发现'No module named src.llm'错误")
    else:
        logger.error(f"  ❌ 发现 {len(results['module_import_errors'])} 个模块导入错误:")
        for error in results["module_import_errors"][:5]:
            logger.error(f"    行{error['line_number']}: {error['content'][:100]}")

    # 未知任务类型警告检查
    logger.info(f"\n3️⃣  未知任务类型警告检查:")
    if len(results["unknown_task_warnings"]) == 0:
        logger.info(f"  ✅ 未发现'未知任务类型'警告")
    else:
        logger.warning(f"  ⚠️  发现 {len(results['unknown_task_warnings'])} 个未知任务类型警告:")
        for warning in results["unknown_task_warnings"][:5]:
            logger.warning(f"    行{warning['line_number']}: {warning['content'][:100]}")

    # 工作流程完整性检查
    logger.info(f"\n4️⃣  工作流程完整性检查:")
    if results["workflow_steps_complete"]:
        logger.info(f"  ✅ 11步工作流程完整")
        logger.info(f"  找到的步骤: {', '.join(results['workflow_steps_found'])}")
    else:
        logger.warning(f"  ⚠️  工作流程不完整")
        logger.warning(f"  找到的步骤 ({len(results['workflow_steps_found'])}/11): {', '.join(results['workflow_steps_found'])}")

    # 总结
    logger.info(f"\n" + "=" * 80)
    logger.info(f"验证总结:")

    all_passed = (
        len(results["type_errors"]) == 0 and
        len(results["module_import_errors"]) == 0 and
        len(results["unknown_task_warnings"]) == 0 and
        results["workflow_steps_complete"]
    )

    if all_passed:
        logger.info(f"🎉 所有验证通过！")
    else:
        issues = []
        if len(results["type_errors"]) > 0:
            issues.append(f"{len(results['type_errors'])}个TypeError")
        if len(results["module_import_errors"]) > 0:
            issues.append(f"{len(results['module_import_errors'])}个模块导入错误")
        if len(results["unknown_task_warnings"]) > 0:
            issues.append(f"{len(results['unknown_task_warnings'])}个未知任务警告")
        if not results["workflow_steps_complete"]:
            issues.append("工作流程不完整")

        logger.warning(f"⚠️  发现问题: {', '.join(issues)}")

    logger.info("=" * 80)

    return all_passed


def main():
    """主函数"""
    logger.info("开始日志验证...")

    # 从Docker容器获取日志
    import subprocess

    try:
        # 获取最近的日志（最后1000行）
        result = subprocess.run(
            ["docker", "logs", "fitness_daml_rag", "--tail", "1000"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(f"获取日志失败: {result.stderr}")
            return False

        log_content = result.stdout + result.stderr

        # 验证日志
        validation_results = check_log_for_errors(log_content)

        # 打印报告
        all_passed = print_validation_report(validation_results)

        return all_passed

    except subprocess.TimeoutExpired:
        logger.error("获取日志超时")
        return False
    except Exception as e:
        logger.error(f"日志验证失败: {e}")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
