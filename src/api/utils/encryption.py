# -*- coding: utf-8 -*-
"""
Encryption Utilities - 数据加密工具

提供数据加密和解密功能：
- 敏感数据加密存储
- 密码哈希
- 令牌生成
- 数据脱敏

版本：v1.0.0
创建日期：2025-12-16
"""

import os
import hashlib
import secrets
import base64
from typing import Optional, Any
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """加密管理器 - 处理数据加密和解密"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        初始化加密管理器
        
        Args:
            encryption_key: 加密密钥（Base64编码），如果为None则从环境变量读取
        """
        if encryption_key:
            self.key = encryption_key.encode()
        else:
            # 从环境变量读取或生成新密钥
            env_key = os.getenv('ENCRYPTION_KEY')
            if env_key:
                self.key = env_key.encode()
            else:
                # 生成新密钥（仅用于开发环境）
                self.key = Fernet.generate_key()
                logger.warning(
                    "未设置ENCRYPTION_KEY环境变量，使用临时密钥。"
                    "生产环境必须设置固定密钥！"
                )
        
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """
        加密数据
        
        Args:
            data: 明文数据
            
        Returns:
            加密后的数据（Base64编码）
        """
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"加密失败: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        解密数据
        
        Args:
            encrypted_data: 加密的数据（Base64编码）
            
        Returns:
            解密后的明文数据
        """
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"解密失败: {e}")
            raise
    
    def encrypt_dict(self, data: dict, fields_to_encrypt: list) -> dict:
        """
        加密字典中的指定字段
        
        Args:
            data: 原始数据字典
            fields_to_encrypt: 需要加密的字段列表
            
        Returns:
            加密后的数据字典
        """
        encrypted_data = data.copy()
        for field in fields_to_encrypt:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = self.encrypt(str(encrypted_data[field]))
        return encrypted_data
    
    def decrypt_dict(self, data: dict, fields_to_decrypt: list) -> dict:
        """
        解密字典中的指定字段
        
        Args:
            data: 加密的数据字典
            fields_to_decrypt: 需要解密的字段列表
            
        Returns:
            解密后的数据字典
        """
        decrypted_data = data.copy()
        for field in fields_to_decrypt:
            if field in decrypted_data and decrypted_data[field]:
                try:
                    decrypted_data[field] = self.decrypt(decrypted_data[field])
                except Exception as e:
                    logger.warning(f"解密字段 {field} 失败: {e}")
                    decrypted_data[field] = None
        return decrypted_data


class PasswordHasher:
    """密码哈希器 - 安全的密码存储"""
    
    @staticmethod
    def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """
        哈希密码
        
        Args:
            password: 明文密码
            salt: 盐值（可选，如果为None则自动生成）
            
        Returns:
            (哈希后的密码, 盐值) 元组
        """
        if salt is None:
            salt = os.urandom(32)
        
        # 使用PBKDF2HMAC进行密码哈希
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode())
        
        # 返回Base64编码的哈希和盐值
        return (
            base64.urlsafe_b64encode(key).decode(),
            base64.urlsafe_b64encode(salt).decode()
        )
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """
        验证密码
        
        Args:
            password: 明文密码
            hashed_password: 哈希后的密码
            salt: 盐值
            
        Returns:
            密码是否匹配
        """
        try:
            # 解码盐值
            salt_bytes = base64.urlsafe_b64decode(salt.encode())
            
            # 重新哈希密码
            new_hash, _ = PasswordHasher.hash_password(password, salt_bytes)
            
            # 比较哈希值
            return new_hash == hashed_password
        except Exception as e:
            logger.error(f"密码验证失败: {e}")
            return False


class TokenGenerator:
    """令牌生成器 - 生成安全的访问令牌"""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        生成随机令牌
        
        Args:
            length: 令牌长度（字节）
            
        Returns:
            Base64编码的令牌
        """
        token_bytes = secrets.token_bytes(length)
        return base64.urlsafe_b64encode(token_bytes).decode()
    
    @staticmethod
    def generate_api_key(prefix: str = "sk") -> str:
        """
        生成API密钥
        
        Args:
            prefix: 密钥前缀
            
        Returns:
            API密钥（格式：prefix-随机字符串）
        """
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}-{random_part}"
    
    @staticmethod
    def generate_session_id() -> str:
        """
        生成会话ID
        
        Returns:
            会话ID
        """
        timestamp = datetime.now().isoformat()
        random_part = secrets.token_hex(16)
        combined = f"{timestamp}-{random_part}"
        
        # 使用SHA256哈希
        hash_obj = hashlib.sha256(combined.encode())
        return hash_obj.hexdigest()


class DataMasker:
    """数据脱敏器 - 隐藏敏感信息"""
    
    @staticmethod
    def mask_email(email: str) -> str:
        """
        脱敏邮箱地址
        
        Args:
            email: 原始邮箱
            
        Returns:
            脱敏后的邮箱（例如：u***@example.com）
        """
        if not email or '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        if len(local) <= 1:
            masked_local = local + '*'
        elif len(local) == 2:
            masked_local = local[0] + '*'
        else:
            # 对于3个字符以上，只显示第一个字符，其余用***代替
            masked_local = local[0] + '***'
        
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """
        脱敏手机号
        
        Args:
            phone: 原始手机号
            
        Returns:
            脱敏后的手机号（例如：138****5678）
        """
        if not phone or len(phone) < 7:
            return phone
        
        return phone[:3] + '****' + phone[-4:]
    
    @staticmethod
    def mask_id_card(id_card: str) -> str:
        """
        脱敏身份证号
        
        Args:
            id_card: 原始身份证号
            
        Returns:
            脱敏后的身份证号（例如：110***********1234）
        """
        if not id_card or len(id_card) < 8:
            return id_card
        
        return id_card[:3] + '*' * (len(id_card) - 7) + id_card[-4:]
    
    @staticmethod
    def mask_token(token: str, visible_chars: int = 8) -> str:
        """
        脱敏令牌
        
        Args:
            token: 原始令牌
            visible_chars: 可见字符数
            
        Returns:
            脱敏后的令牌（例如：sk-abc123...）
        """
        if not token or len(token) <= visible_chars:
            return token
        
        return token[:visible_chars] + '...'
    
    @staticmethod
    def mask_dict(data: dict, fields_to_mask: dict) -> dict:
        """
        脱敏字典中的指定字段
        
        Args:
            data: 原始数据字典
            fields_to_mask: 需要脱敏的字段及其类型
                例如：{'email': 'email', 'phone': 'phone', 'token': 'token'}
            
        Returns:
            脱敏后的数据字典
        """
        masked_data = data.copy()
        
        for field, mask_type in fields_to_mask.items():
            if field in masked_data and masked_data[field]:
                value = str(masked_data[field])
                
                if mask_type == 'email':
                    masked_data[field] = DataMasker.mask_email(value)
                elif mask_type == 'phone':
                    masked_data[field] = DataMasker.mask_phone(value)
                elif mask_type == 'id_card':
                    masked_data[field] = DataMasker.mask_id_card(value)
                elif mask_type == 'token':
                    masked_data[field] = DataMasker.mask_token(value)
                else:
                    # 默认脱敏：只显示前后各2个字符
                    if len(value) > 4:
                        masked_data[field] = value[:2] + '*' * (len(value) - 4) + value[-2:]
        
        return masked_data


class SecureStorage:
    """安全存储 - 加密存储敏感数据"""
    
    def __init__(self, encryption_manager: Optional[EncryptionManager] = None):
        """
        初始化安全存储
        
        Args:
            encryption_manager: 加密管理器实例
        """
        self.encryption_manager = encryption_manager or EncryptionManager()
    
    def store_sensitive_data(
        self,
        data: dict,
        sensitive_fields: list
    ) -> dict:
        """
        存储敏感数据（加密）
        
        Args:
            data: 原始数据
            sensitive_fields: 敏感字段列表
            
        Returns:
            加密后的数据
        """
        return self.encryption_manager.encrypt_dict(data, sensitive_fields)
    
    def retrieve_sensitive_data(
        self,
        encrypted_data: dict,
        sensitive_fields: list
    ) -> dict:
        """
        检索敏感数据（解密）
        
        Args:
            encrypted_data: 加密的数据
            sensitive_fields: 敏感字段列表
            
        Returns:
            解密后的数据
        """
        return self.encryption_manager.decrypt_dict(encrypted_data, sensitive_fields)


# 全局实例（单例模式）
_encryption_manager = None
_password_hasher = PasswordHasher()
_token_generator = TokenGenerator()
_data_masker = DataMasker()


def get_encryption_manager() -> EncryptionManager:
    """获取全局加密管理器实例"""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def get_password_hasher() -> PasswordHasher:
    """获取全局密码哈希器实例"""
    return _password_hasher


def get_token_generator() -> TokenGenerator:
    """获取全局令牌生成器实例"""
    return _token_generator


def get_data_masker() -> DataMasker:
    """获取全局数据脱敏器实例"""
    return _data_masker


# 导出
__all__ = [
    'EncryptionManager',
    'PasswordHasher',
    'TokenGenerator',
    'DataMasker',
    'SecureStorage',
    'get_encryption_manager',
    'get_password_hasher',
    'get_token_generator',
    'get_data_masker'
]
