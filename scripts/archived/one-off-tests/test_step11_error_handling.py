# -*- coding: utf-8 -*-
"""
测试步骤11错误处理功能

验证：
1. parse_validation_error 函数能正确解析422验证错误
2. format_validation_error_log 函数能生成清晰的日志消息
3. 错误处理不会阻塞工作流程
"""

import json
import sys
sys.path.insert(0, '/app')

from src.applications.fitness.workflow_executor import (
    parse_validation_error,
    format_validation_error_log
)
from src.applications.fitness.clients.backend_client import BackendValidationError


def test_parse_validation_error():
    """测试解析验证错误"""
    print("=" * 60)
    print("测试1: 解析422验证错误")
    print("=" * 60)
    
    # 模拟真实的422错误
    error_json = {
        "code": 422,
        "msg": "验证失败",
        "data": {
            "errors": {
                "user_id": ["The selected user id is invalid."]
            }
        }
    }
    
    error = BackendValidationError(f"验证失败: {json.dumps(error_json, ensure_ascii=False)}")
    
    result = parse_validation_error(error)
    
    print(f"错误类型: {result['error_type']}")
    print(f"错误码: {result['error_code']}")
    print(f"错误消息: {result['error_message']}")
    print(f"字段错误: {result['field_errors']}")
    print(f"用户不存在: {result['is_user_not_found']}")
    
    # 验证结果
    assert result['error_code'] == 422, "错误码应为422"
    assert result['is_user_not_found'] == True, "应检测到用户不存在"
    assert 'user_id' in result['field_errors'], "应包含user_id字段错误"
    
    print("\n✅ 测试1通过!")
    return True


def test_format_validation_error_log():
    """测试格式化错误日志"""
    print("\n" + "=" * 60)
    print("测试2: 格式化错误日志")
    print("=" * 60)
    
    error_details = {
        "error_type": "BackendValidationError",
        "error_code": 422,
        "error_message": "验证失败",
        "field_errors": {
            "user_id": ["The selected user id is invalid."]
        },
        "raw_error": "...",
        "is_user_not_found": True
    }
    
    log_message = format_validation_error_log("test123", 999, error_details)
    
    print("生成的日志消息:")
    print("-" * 40)
    print(log_message)
    print("-" * 40)
    
    # 验证日志包含关键信息
    assert "test123" in log_message, "应包含请求ID"
    assert "999" in log_message, "应包含用户ID"
    assert "422" in log_message, "应包含错误码"
    assert "user_id" in log_message, "应包含字段名"
    assert "用户ID在后端数据库中不存在" in log_message, "应包含用户不存在提示"
    
    print("\n✅ 测试2通过!")
    return True


def test_parse_non_json_error():
    """测试解析非JSON格式的错误"""
    print("\n" + "=" * 60)
    print("测试3: 解析非JSON格式错误")
    print("=" * 60)
    
    error = BackendValidationError("简单的错误消息")
    
    result = parse_validation_error(error)
    
    print(f"错误类型: {result['error_type']}")
    print(f"错误消息: {result['error_message']}")
    print(f"用户不存在: {result['is_user_not_found']}")
    
    # 验证结果
    assert result['error_type'] == "BackendValidationError"
    assert result['is_user_not_found'] == False
    assert result['field_errors'] == {}
    
    print("\n✅ 测试3通过!")
    return True


def test_parse_other_field_errors():
    """测试解析其他字段的验证错误"""
    print("\n" + "=" * 60)
    print("测试4: 解析其他字段验证错误")
    print("=" * 60)
    
    error_json = {
        "code": 422,
        "msg": "验证失败",
        "data": {
            "errors": {
                "session_id": ["The session id field is required."],
                "user_query": ["The user query must be at least 1 character."]
            }
        }
    }
    
    error = BackendValidationError(f"验证失败: {json.dumps(error_json, ensure_ascii=False)}")
    
    result = parse_validation_error(error)
    
    print(f"错误码: {result['error_code']}")
    print(f"字段错误: {result['field_errors']}")
    print(f"用户不存在: {result['is_user_not_found']}")
    
    # 验证结果
    assert result['error_code'] == 422
    assert result['is_user_not_found'] == False  # 不是user_id错误
    assert 'session_id' in result['field_errors']
    assert 'user_query' in result['field_errors']
    
    print("\n✅ 测试4通过!")
    return True


def main():
    """运行所有测试"""
    print("\n🧪 开始测试步骤11错误处理功能\n")
    
    tests = [
        test_parse_validation_error,
        test_format_validation_error_log,
        test_parse_non_json_error,
        test_parse_other_field_errors
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
