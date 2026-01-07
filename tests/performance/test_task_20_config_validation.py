# -*- coding: utf-8 -*-
"""
任务20: 配置和文档验收测试

验收内容：
1. 验证所有配置文件完整性
2. 验证所有文档存在性
3. 验证测试脚本完整性
4. 生成配置验收报告

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-21
"""

import pytest
import yaml
import json
from pathlib import Path
from typing import Dict, Any, List


# 配置文件路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "performance_optimization.yaml"
DOCKER_COMPOSE_FILE = PROJECT_ROOT.parent / "docker-compose.yml"


class ConfigValidationResult:
    """配置验证结果"""
    
    def __init__(self):
        self.test_items = []
        self.passed_count = 0
        self.failed_count = 0
        self.warnings = []
    
    def add_test_item(
        self,
        category: str,
        name: str,
        passed: bool,
        expected: str,
        actual: str,
        details: str = ""
    ):
        """添加测试项"""
        self.test_items.append({
            "category": category,
            "name": name,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "details": details
        })
        
        if passed:
            self.passed_count += 1
        else:
            self.failed_count += 1
    
    def add_warning(self, message: str):
        """添加警告"""
        self.warnings.append(message)
