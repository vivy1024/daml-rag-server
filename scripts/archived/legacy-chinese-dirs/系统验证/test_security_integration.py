# -*- coding: utf-8 -*-
"""
Security Integration Test - 安全功能集成测试

快速验证安全功能是否正常工作

版本：v1.0.0
创建日期：2025-12-16
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

# 设置工作目录
os.chdir(Path(__file__).parent.parent.parent)

# 直接导入模块
from src.api.middleware.security import InputValidator, RateLimiter, SecurityLogger
from src.api.utils.encryption import (
    get_encryption_manager,
    get_password_hasher,
    get_token_generator,
    get_data_masker
)


def test_input_validation():
    """测试输入验证"""
    print("🔍 测试输入验证...")
    
    # 测试正常输入
    try:
        result = InputValidator.validate_and_clean('query', '  增肌计划  ')
        assert result == '增肌计划', "正常输入清理失败"
        print("  ✅ 正常输入清理成功")
    except Exception as e:
        print(f"  ❌ 正常输入清理失败: {e}")
        return False
    
    # 测试XSS攻击检测
    try:
        InputValidator.validate_and_clean('query', '<script>alert("XSS")</script>')
        print("  ❌ XSS攻击检测失败（应该抛出异常）")
        return False
    except Exception:
        print("  ✅ XSS攻击检测成功")
    
    # 测试SQL注入检测
    try:
        InputValidator.validate_and_clean('query', "'; DROP TABLE users; --")
        print("  ❌ SQL注入检测失败（应该抛出异常）")
        return False
    except Exception:
        print("  ✅ SQL注入检测成功")
    
    return True


def test_encryption():
    """测试数据加密"""
    print("\n🔐 测试数据加密...")
    
    try:
        encryptor = get_encryption_manager()
        
        # 测试加密和解密
        original = "sensitive_data"
        encrypted = encryptor.encrypt(original)
        decrypted = encryptor.decrypt(encrypted)
        
        assert encrypted != original, "加密失败（密文与明文相同）"
        assert decrypted == original, "解密失败（解密后与原文不同）"
        
        print("  ✅ 数据加密/解密成功")
        return True
    except Exception as e:
        print(f"  ❌ 数据加密测试失败: {e}")
        return False


def test_password_hashing():
    """测试密码哈希"""
    print("\n🔑 测试密码哈希...")
    
    try:
        hasher = get_password_hasher()
        
        # 测试密码哈希
        password = "test_password_123"
        hashed, salt = hasher.hash_password(password)
        
        assert hashed != password, "密码哈希失败（哈希值与明文相同）"
        
        # 测试密码验证
        assert hasher.verify_password(password, hashed, salt), "正确密码验证失败"
        assert not hasher.verify_password("wrong_password", hashed, salt), "错误密码验证失败"
        
        print("  ✅ 密码哈希/验证成功")
        return True
    except Exception as e:
        print(f"  ❌ 密码哈希测试失败: {e}")
        return False


def test_token_generation():
    """测试令牌生成"""
    print("\n🎫 测试令牌生成...")
    
    try:
        generator = get_token_generator()
        
        # 测试生成令牌
        token1 = generator.generate_token()
        token2 = generator.generate_token()
        
        assert len(token1) > 0, "令牌生成失败（长度为0）"
        assert token1 != token2, "令牌生成失败（两次生成相同）"
        
        # 测试生成API密钥
        api_key = generator.generate_api_key(prefix="sk")
        assert api_key.startswith("sk-"), "API密钥生成失败（前缀错误）"
        
        print("  ✅ 令牌生成成功")
        return True
    except Exception as e:
        print(f"  ❌ 令牌生成测试失败: {e}")
        return False


def test_data_masking():
    """测试数据脱敏"""
    print("\n🎭 测试数据脱敏...")
    
    try:
        masker = get_data_masker()
        
        # 测试邮箱脱敏
        masked_email = masker.mask_email("user@example.com")
        assert masked_email == "u***@example.com", f"邮箱脱敏失败: {masked_email}"
        
        # 测试手机号脱敏
        masked_phone = masker.mask_phone("13800138000")
        assert masked_phone == "138****8000", f"手机号脱敏失败: {masked_phone}"
        
        # 测试令牌脱敏
        masked_token = masker.mask_token("sk-abc123def456", visible_chars=8)
        assert masked_token == "sk-abc12...", f"令牌脱敏失败: {masked_token}"
        
        print("  ✅ 数据脱敏成功")
        return True
    except Exception as e:
        print(f"  ❌ 数据脱敏测试失败: {e}")
        return False


def test_security_logger():
    """测试安全日志"""
    print("\n📝 测试安全日志...")
    
    try:
        # 测试数据清理
        data = {
            'user_id': '123',
            'password': 'secret123',
            'token': 'abc123',
            'query': 'test'
        }
        
        sanitized = SecurityLogger.sanitize_data(data)
        
        assert sanitized['user_id'] == '123', "用户ID不应被脱敏"
        assert sanitized['password'] == '***REDACTED***', "密码应被脱敏"
        assert sanitized['token'] == '***REDACTED***', "令牌应被脱敏"
        assert sanitized['query'] == 'test', "查询不应被脱敏"
        
        print("  ✅ 安全日志清理成功")
        return True
    except Exception as e:
        print(f"  ❌ 安全日志测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("🔒 安全功能集成测试")
    print("=" * 60)
    
    tests = [
        ("输入验证", test_input_validation),
        ("数据加密", test_encryption),
        ("密码哈希", test_password_hashing),
        ("令牌生成", test_token_generation),
        ("数据脱敏", test_data_masking),
        ("安全日志", test_security_logger)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name}测试异常: {e}")
            results.append((name, False))
    
    # 打印总结
    print("\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有安全功能测试通过！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
