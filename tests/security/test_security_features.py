# -*- coding: utf-8 -*-
"""
Security Features Test - 安全功能测试

测试所有安全增强功能：
- 输入验证
- 限流保护
- 数据加密
- 密码哈希
- 令牌生成
- 数据脱敏

版本：v1.0.0
创建日期：2025-12-16
"""

import pytest
import time
from fastapi import HTTPException
from src.api.middleware.security import (
    InputValidator,
    RateLimiter,
    AuthenticationManager,
    SecurityLogger,
    DataMasker
)
from src.api.utils.encryption import (
    EncryptionManager,
    PasswordHasher,
    TokenGenerator,
    DataMasker as EncryptionDataMasker
)


class TestInputValidator:
    """测试输入验证器"""
    
    def test_validate_clean_input(self):
        """测试清理正常输入"""
        result = InputValidator.validate_and_clean('query', '  增肌计划  ')
        assert result == '增肌计划'
    
    def test_detect_xss_attack(self):
        """测试XSS攻击检测"""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_and_clean('query', '<script>alert("XSS")</script>')
        assert exc_info.value.status_code == 400
    
    def test_detect_sql_injection(self):
        """测试SQL注入检测"""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_and_clean('query', "'; DROP TABLE users; --")
        assert exc_info.value.status_code == 400
    
    def test_detect_path_traversal(self):
        """测试路径遍历检测"""
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_and_clean('query', '../../../etc/passwd')
        assert exc_info.value.status_code == 400
    
    def test_length_limit(self):
        """测试长度限制"""
        long_query = 'a' * 3000
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_and_clean('query', long_query)
        assert exc_info.value.status_code == 400
    
    def test_validate_dict(self):
        """测试字典验证"""
        data = {
            'user_id': '123',
            'query': '  增肌计划  ',
            'comment': 'test'
        }
        result = InputValidator.validate_dict(data, required_fields=['user_id', 'query'])
        assert result['query'] == '增肌计划'
        assert 'user_id' in result
    
    def test_missing_required_fields(self):
        """测试缺少必需字段"""
        data = {'user_id': '123'}
        with pytest.raises(HTTPException) as exc_info:
            InputValidator.validate_dict(data, required_fields=['user_id', 'query'])
        assert exc_info.value.status_code == 400


class TestRateLimiter:
    """测试限流器"""
    
    def test_rate_limit_basic(self):
        """测试基本限流"""
        limiter = RateLimiter(requests_per_minute=5, requests_per_hour=10)
        
        # 模拟请求对象
        class MockRequest:
            def __init__(self):
                self.client = type('obj', (object,), {'host': '127.0.0.1'})()
                self.headers = {}
                self.state = type('obj', (object,), {})()
        
        request = MockRequest()
        
        # 前5次请求应该成功
        for i in range(5):
            assert limiter.check_rate_limit(request) == True
        
        # 第6次请求应该被限流
        with pytest.raises(HTTPException) as exc_info:
            limiter.check_rate_limit(request)
        assert exc_info.value.status_code == 429
    
    def test_blacklist(self):
        """测试黑名单"""
        limiter = RateLimiter()
        client_id = "ip:192.168.1.100"
        
        # 添加到黑名单
        limiter.add_to_blacklist(client_id)
        assert client_id in limiter.blacklist
        
        # 从黑名单移除
        limiter.remove_from_blacklist(client_id)
        assert client_id not in limiter.blacklist


class TestAuthenticationManager:
    """测试认证管理器"""
    
    def test_public_path(self):
        """测试公开路径"""
        auth_manager = AuthenticationManager()
        assert auth_manager.is_public_path('/docs')
        assert auth_manager.is_public_path('/health')
        assert auth_manager.is_public_path('/api/health')
        assert not auth_manager.is_public_path('/api/v1/chat')
    
    def test_validate_token_dev_mode(self):
        """测试开发模式令牌验证"""
        auth_manager = AuthenticationManager(require_auth=False)
        user_info = auth_manager.validate_token('any-token')
        assert user_info is not None
        assert user_info['user_id'] == 'dev_user'


class TestEncryptionManager:
    """测试加密管理器"""
    
    def test_encrypt_decrypt(self):
        """测试加密和解密"""
        encryptor = EncryptionManager()
        
        original = "sensitive_data"
        encrypted = encryptor.encrypt(original)
        decrypted = encryptor.decrypt(encrypted)
        
        assert encrypted != original
        assert decrypted == original
    
    def test_encrypt_dict(self):
        """测试字典加密"""
        encryptor = EncryptionManager()
        
        data = {
            'user_id': '123',
            'email': 'user@example.com',
            'phone': '13800138000'
        }
        
        encrypted_data = encryptor.encrypt_dict(data, ['email', 'phone'])
        
        assert encrypted_data['user_id'] == '123'
        assert encrypted_data['email'] != 'user@example.com'
        assert encrypted_data['phone'] != '13800138000'
        
        # 解密
        decrypted_data = encryptor.decrypt_dict(encrypted_data, ['email', 'phone'])
        assert decrypted_data['email'] == 'user@example.com'
        assert decrypted_data['phone'] == '13800138000'


class TestPasswordHasher:
    """测试密码哈希器"""
    
    def test_hash_password(self):
        """测试密码哈希"""
        hasher = PasswordHasher()
        
        password = "test_password_123"
        hashed, salt = hasher.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert len(salt) > 0
    
    def test_verify_password(self):
        """测试密码验证"""
        hasher = PasswordHasher()
        
        password = "test_password_123"
        hashed, salt = hasher.hash_password(password)
        
        # 正确密码
        assert hasher.verify_password(password, hashed, salt) == True
        
        # 错误密码
        assert hasher.verify_password("wrong_password", hashed, salt) == False


class TestTokenGenerator:
    """测试令牌生成器"""
    
    def test_generate_token(self):
        """测试生成令牌"""
        generator = TokenGenerator()
        
        token1 = generator.generate_token()
        token2 = generator.generate_token()
        
        assert len(token1) > 0
        assert len(token2) > 0
        assert token1 != token2
    
    def test_generate_api_key(self):
        """测试生成API密钥"""
        generator = TokenGenerator()
        
        api_key = generator.generate_api_key(prefix="sk")
        
        assert api_key.startswith("sk-")
        assert len(api_key) > 10
    
    def test_generate_session_id(self):
        """测试生成会话ID"""
        generator = TokenGenerator()
        
        session_id1 = generator.generate_session_id()
        session_id2 = generator.generate_session_id()
        
        assert len(session_id1) == 64  # SHA256哈希长度
        assert session_id1 != session_id2


class TestDataMasker:
    """测试数据脱敏器"""
    
    def test_mask_email(self):
        """测试邮箱脱敏"""
        masker = DataMasker()
        
        masked = masker.mask_email("user@example.com")
        assert masked == "u***@example.com"
        
        masked = masker.mask_email("ab@example.com")
        assert masked == "a*@example.com"
    
    def test_mask_phone(self):
        """测试手机号脱敏"""
        masker = DataMasker()
        
        masked = masker.mask_phone("13800138000")
        assert masked == "138****8000"
    
    def test_mask_id_card(self):
        """测试身份证号脱敏"""
        masker = DataMasker()
        
        masked = masker.mask_id_card("110101199001011234")
        assert masked == "110***********1234"
    
    def test_mask_token(self):
        """测试令牌脱敏"""
        masker = DataMasker()
        
        masked = masker.mask_token("sk-abc123def456", visible_chars=8)
        assert masked == "sk-abc12..."
    
    def test_mask_dict(self):
        """测试字典脱敏"""
        masker = DataMasker()
        
        data = {
            'email': 'user@example.com',
            'phone': '13800138000',
            'token': 'sk-abc123def456'
        }
        
        masked_data = masker.mask_dict(data, {
            'email': 'email',
            'phone': 'phone',
            'token': 'token'
        })
        
        assert masked_data['email'] == 'u***@example.com'
        assert masked_data['phone'] == '138****8000'
        assert masked_data['token'] == 'sk-abc12...'


class TestSecurityLogger:
    """测试安全日志记录器"""
    
    def test_sanitize_data(self):
        """测试数据清理"""
        data = {
            'user_id': '123',
            'password': 'secret123',
            'token': 'abc123',
            'query': 'test'
        }
        
        sanitized = SecurityLogger.sanitize_data(data)
        
        assert sanitized['user_id'] == '123'
        assert sanitized['password'] == '***REDACTED***'
        assert sanitized['token'] == '***REDACTED***'
        assert sanitized['query'] == 'test'
    
    def test_sanitize_nested_dict(self):
        """测试嵌套字典清理"""
        data = {
            'user': {
                'id': '123',
                'password': 'secret123'
            },
            'api_key': 'key123'
        }
        
        sanitized = SecurityLogger.sanitize_data(data)
        
        assert sanitized['user']['id'] == '123'
        assert sanitized['user']['password'] == '***REDACTED***'
        assert sanitized['api_key'] == '***REDACTED***'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
