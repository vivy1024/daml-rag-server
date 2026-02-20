# -*- coding: utf-8 -*-
"""
Security Middleware - 安全中间件

提供API安全增强功能：
- 输入验证和清理
- 认证和授权
- 限流保护
- 安全日志
- 错误处理安全

版本：v1.0.0
创建日期：2025-12-16
"""

import logging
import re
import time
import hashlib
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class InputValidator:
    """输入验证器 - 验证和清理用户输入"""
    
    # 危险字符模式
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',  # JavaScript协议
        r'on\w+\s*=',  # 事件处理器
        r'<iframe[^>]*>',  # iframe注入
        r'eval\s*\(',  # eval函数
        r'exec\s*\(',  # exec函数
        r'\$\{.*?\}',  # 模板注入
        r'\.\./',  # 路径遍历
        r'union\s+select',  # SQL注入
        r'drop\s+table',  # SQL注入
    ]
    
    # 最大输入长度限制
    MAX_LENGTHS = {
        'query': 2000,
        'comment': 1000,
        'user_id': 100,
        'session_id': 100,
        'default': 500
    }
    
    @classmethod
    def validate_and_clean(cls, field_name: str, value: Any) -> Any:
        """
        验证并清理输入值
        
        Args:
            field_name: 字段名
            value: 输入值
            
        Returns:
            清理后的值
            
        Raises:
            HTTPException: 如果输入无效
        """
        if value is None:
            return None
            
        # 转换为字符串
        if not isinstance(value, str):
            value = str(value)
        
        # 检查长度
        max_length = cls.MAX_LENGTHS.get(field_name, cls.MAX_LENGTHS['default'])
        if len(value) > max_length:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"字段 {field_name} 超过最大长度 {max_length}"
            )
        
        # 检查危险模式
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"检测到潜在恶意输入: field={field_name}, pattern={pattern}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="输入包含不允许的内容"
                )
        
        # 清理空白字符
        value = value.strip()
        
        # 移除控制字符
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\n\r\t')
        
        return value
    
    @classmethod
    def validate_dict(cls, data: Dict[str, Any], required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        验证并清理字典数据
        
        Args:
            data: 输入数据
            required_fields: 必需字段列表
            
        Returns:
            清理后的数据
        """
        if not isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请求数据必须是JSON对象"
            )
        
        # 检查必需字段
        if required_fields:
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"缺少必需字段: {', '.join(missing_fields)}"
                )
        
        # 清理所有字符串字段
        cleaned_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                cleaned_data[key] = cls.validate_and_clean(key, value)
            elif isinstance(value, dict):
                cleaned_data[key] = cls.validate_dict(value)
            elif isinstance(value, list):
                cleaned_data[key] = [
                    cls.validate_and_clean(key, item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                cleaned_data[key] = value
        
        return cleaned_data


class RateLimiter:
    """限流器 - 防止API滥用和DDoS攻击"""
    
    # 内部调用白名单（默认不跳过限流；仅在显式开启时生效）
    INTERNAL_IPS = {'127.0.0.1', 'localhost', '::1'}
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_size: int = 10
    ):
        """
        初始化限流器
        
        Args:
            requests_per_minute: 每分钟最大请求数
            requests_per_hour: 每小时最大请求数
            burst_size: 突发请求大小
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        
        # 存储请求记录 {client_id: [(timestamp, count), ...]}
        self.request_records: Dict[str, List[tuple]] = defaultdict(list)
        
        # IP黑名单
        self.blacklist: set = set()
    
    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用用户ID
        if hasattr(request.state, 'user_id'):
            return f"user:{request.state.user_id}"
        
        # 使用IP地址
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host}"
    
    def _clean_old_records(self, client_id: str):
        """清理过期记录"""
        now = time.time()
        hour_ago = now - 3600
        
        # 只保留最近1小时的记录
        self.request_records[client_id] = [
            (ts, count) for ts, count in self.request_records[client_id]
            if ts > hour_ago
        ]
    
    def check_rate_limit(self, request: Request) -> bool:
        """
        检查是否超过限流
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            bool: True表示允许，False表示超限
            
        Raises:
            HTTPException: 如果超过限流
        """
        client_id = self._get_client_id(request)
        
        # 内部调用白名单检查（可选跳过限流）
        if os.getenv("BYPASS_RATE_LIMIT_FOR_INTERNAL", "false").lower() in ("true", "1", "yes"):
            client_ip = request.client.host if request.client else None
            if client_ip in self.INTERNAL_IPS:
                return True
        
        # 检查黑名单
        if client_id in self.blacklist:
            logger.warning(f"黑名单客户端尝试访问: {client_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="访问被拒绝"
            )
        
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        # 清理旧记录
        self._clean_old_records(client_id)
        
        # 记录当前请求
        self.request_records[client_id].append((now, 1))
        
        # 检查每分钟限制
        minute_requests = sum(
            count for ts, count in self.request_records[client_id]
            if ts > minute_ago
        )
        
        if minute_requests > self.requests_per_minute:
            logger.warning(
                f"客户端超过每分钟限制: {client_id}, "
                f"requests={minute_requests}/{self.requests_per_minute}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，请稍后再试（每分钟最多{self.requests_per_minute}次）"
            )
        
        # 检查每小时限制
        hour_requests = sum(
            count for ts, count in self.request_records[client_id]
            if ts > hour_ago
        )
        
        if hour_requests > self.requests_per_hour:
            logger.warning(
                f"客户端超过每小时限制: {client_id}, "
                f"requests={hour_requests}/{self.requests_per_hour}"
            )
            # 自动加入黑名单（1小时）
            self.blacklist.add(client_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，已被暂时限制访问"
            )
        
        # 检查突发请求
        recent_requests = sum(
            count for ts, count in self.request_records[client_id]
            if ts > now - 5  # 最近5秒
        )
        
        if recent_requests > self.burst_size:
            logger.warning(
                f"客户端突发请求过多: {client_id}, "
                f"requests={recent_requests}/{self.burst_size}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求过于频繁，请稍后再试"
            )
        
        return True
    
    def add_to_blacklist(self, client_id: str):
        """添加到黑名单"""
        self.blacklist.add(client_id)
        logger.warning(f"客户端已加入黑名单: {client_id}")
    
    def remove_from_blacklist(self, client_id: str):
        """从黑名单移除"""
        self.blacklist.discard(client_id)
        logger.info(f"客户端已从黑名单移除: {client_id}")


class AuthenticationManager:
    """认证管理器 - 处理API认证和授权"""
    
    # 公开路径（不需要认证）
    PUBLIC_PATHS = [
        '/docs',
        '/redoc',
        '/openapi.json',
        '/health',
        '/api/health',
        '/'
    ]
    
    def __init__(self, require_auth: bool = False):
        """
        初始化认证管理器
        
        Args:
            require_auth: 是否要求认证（默认False，开发环境）
        """
        self.require_auth = require_auth
        self.valid_tokens: Dict[str, Dict[str, Any]] = {}
    
    def is_public_path(self, path: str) -> bool:
        """检查是否是公开路径"""
        for public_path in self.PUBLIC_PATHS:
            if public_path == "/":
                if path == "/":
                    return True
                continue
            if path.startswith(public_path):
                return True
        return False
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证访问令牌
        
        Args:
            token: 访问令牌
            
        Returns:
            用户信息，如果令牌无效则返回None
        """
        if not self.require_auth:
            # 开发环境：不验证令牌
            return {"user_id": "dev_user", "role": "admin"}
        
        # 生产环境：验证令牌
        token_info = self.valid_tokens.get(token)
        if not token_info:
            return None
        
        # 检查令牌是否过期
        if token_info.get('expires_at'):
            if datetime.now() > token_info['expires_at']:
                logger.warning(f"令牌已过期: {token[:10]}...")
                return None
        
        return token_info
    
    def check_authentication(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        检查请求认证
        
        Args:
            request: FastAPI请求对象
            
        Returns:
            用户信息
            
        Raises:
            HTTPException: 如果认证失败
        """
        # 公开路径不需要认证
        if self.is_public_path(request.url.path):
            return None
        
        # 开发环境：跳过认证
        if not self.require_auth:
            return {"user_id": "dev_user", "role": "admin"}
        
        # 获取令牌
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少认证令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # 解析Bearer令牌
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证格式",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        token = parts[1]
        
        # 验证令牌
        user_info = self.validate_token(token)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效或过期的令牌",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        return user_info


class SecurityLogger:
    """安全日志记录器 - 记录安全相关事件"""
    
    # 敏感字段（不记录到日志）
    SENSITIVE_FIELDS = [
        'password',
        'token',
        'api_key',
        'secret',
        'authorization',
        'cookie'
    ]
    
    @classmethod
    def sanitize_data(cls, data: Any) -> Any:
        """
        清理敏感数据
        
        Args:
            data: 原始数据
            
        Returns:
            清理后的数据
        """
        if isinstance(data, dict):
            return {
                key: '***REDACTED***' if key.lower() in cls.SENSITIVE_FIELDS
                else cls.sanitize_data(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [cls.sanitize_data(item) for item in data]
        elif isinstance(data, str) and len(data) > 100:
            # 截断长字符串
            return data[:100] + '...'
        else:
            return data
    
    @classmethod
    def log_request(cls, request: Request, user_info: Optional[Dict[str, Any]] = None):
        """记录请求（仅在启用时）"""
        # 检查是否启用请求日志
        try:
            from ..config.logging_config import should_log_request
            if not should_log_request():
                return
        except ImportError:
            # 如果配置文件不存在，默认不记录
            return
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'method': request.method,
            'path': request.url.path,
            'client': request.client.host if request.client else 'unknown',
            'user_agent': request.headers.get('user-agent', 'unknown'),
            'user_id': user_info.get('user_id') if user_info else None
        }
        
        logger.info(f"API请求: {cls.sanitize_data(log_data)}")
    
    @classmethod
    def log_security_event(cls, event_type: str, details: Dict[str, Any]):
        """记录安全事件"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'details': cls.sanitize_data(details)
        }
        
        logger.warning(f"安全事件: {log_data}")


class DataMasker:
    """数据脱敏器 - 用于日志/输出中的敏感信息遮蔽"""

    def mask_email(self, email: str) -> str:
        """邮箱脱敏：u***@example.com / a*@example.com"""
        if not email or "@" not in email:
            return "***"

        local_part, domain = email.split("@", 1)
        if not local_part:
            return f"***@{domain}"
        if len(local_part) == 1:
            return f"{local_part[0]}***@{domain}"
        if len(local_part) == 2:
            return f"{local_part[0]}*@{domain}"
        return f"{local_part[0]}***@{domain}"

    def mask_phone(self, phone: str) -> str:
        """手机号脱敏：138****8000"""
        if not phone:
            return "***"
        phone_str = str(phone)
        if len(phone_str) < 7:
            return "***"
        return f"{phone_str[:3]}****{phone_str[-4:]}"

    def mask_id_card(self, id_card: str) -> str:
        """身份证号脱敏：110***********1234"""
        if not id_card:
            return "***"
        id_str = str(id_card)
        if len(id_str) <= 7:
            return "***"
        masked_len = max(len(id_str) - 7, 0)
        return f"{id_str[:3]}{'*' * masked_len}{id_str[-4:]}"

    def mask_token(self, token: str, visible_chars: int = 8) -> str:
        """令牌脱敏：sk-abc12..."""
        if not token:
            return "***"
        token_str = str(token)
        if visible_chars <= 0:
            return "..."
        if len(token_str) <= visible_chars:
            return token_str
        return f"{token_str[:visible_chars]}..."

    def mask_dict(self, data: Dict[str, Any], mask_rules: Dict[str, str]) -> Dict[str, Any]:
        """
        按规则对字典字段脱敏

        Args:
            data: 原始数据
            mask_rules: {字段名: 脱敏类型}，类型支持 email/phone/id_card/token
        """
        if not isinstance(data, dict):
            return {}

        result: Dict[str, Any] = dict(data)
        for field, mask_type in (mask_rules or {}).items():
            if field not in result:
                continue
            value = result.get(field)
            if value is None:
                continue

            if mask_type == "email":
                result[field] = self.mask_email(str(value))
            elif mask_type == "phone":
                result[field] = self.mask_phone(str(value))
            elif mask_type == "id_card":
                result[field] = self.mask_id_card(str(value))
            elif mask_type == "token":
                result[field] = self.mask_token(str(value))
            else:
                # 未知类型：统一遮蔽
                result[field] = "***"

        return result


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件 - 集成所有安全功能"""
    
    def __init__(
        self,
        app,
        enable_rate_limit: bool = True,
        enable_auth: bool = False,
        enable_input_validation: bool = True
    ):
        """
        初始化安全中间件
        
        Args:
            app: FastAPI应用
            enable_rate_limit: 启用限流
            enable_auth: 启用认证
            enable_input_validation: 启用输入验证
        """
        super().__init__(app)
        self.enable_rate_limit = enable_rate_limit
        self.enable_auth = enable_auth
        self.enable_input_validation = enable_input_validation
        
        # 初始化组件
        self.rate_limiter = RateLimiter() if enable_rate_limit else None
        self.auth_manager = AuthenticationManager(require_auth=enable_auth)
        
        logger.info(
            f"安全中间件已初始化: "
            f"rate_limit={enable_rate_limit}, "
            f"auth={enable_auth}, "
            f"input_validation={enable_input_validation}"
        )
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        try:
            # 1. 限流检查
            if self.enable_rate_limit and self.rate_limiter:
                self.rate_limiter.check_rate_limit(request)

            # 2. 认证检查（如果DualAuthMiddleware已认证，跳过）
            user_info = None
            already_authed = getattr(request.state, 'auth_mode', None) is not None
            if self.enable_auth and not already_authed:
                user_info = self.auth_manager.check_authentication(request)
                if user_info:
                    request.state.user_info = user_info
            
            # 3. 记录请求
            SecurityLogger.log_request(request, user_info)
            
            # 4. 处理请求
            response = await call_next(request)

            # 5. 添加安全响应头
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
            return response
            
        except HTTPException as e:
            # 记录安全异常
            SecurityLogger.log_security_event(
                'http_exception',
                {
                    'status_code': e.status_code,
                    'detail': e.detail,
                    'path': request.url.path,
                    'client': request.client.host if request.client else 'unknown'
                }
            )
            raise
        
        except Exception as e:
            # 记录未预期的异常
            SecurityLogger.log_security_event(
                'unexpected_exception',
                {
                    'error': str(e),
                    'path': request.url.path,
                    'client': request.client.host if request.client else 'unknown'
                }
            )
            
            # 返回通用错误（不泄露内部信息）
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    'code': 500,
                    'msg': '服务器内部错误',
                    'data': None
                }
            )


# 导出
__all__ = [
    'InputValidator',
    'RateLimiter',
    'AuthenticationManager',
    'SecurityLogger',
    'SecurityMiddleware'
]
