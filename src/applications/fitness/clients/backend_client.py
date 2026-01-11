# -*- coding: utf-8 -*-
"""
Backend API Client for Meta-Learning MCP

用于DAML-RAG Server调用yuzhen-backend内部API的HTTP客户端
支持：
- 用户档案获取
- 会员权限检查
- 自动重试机制
- 错误处理

作者: BUILD_BODY Team
版本: 1.0.0
"""

import os
import httpx
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# ============= 配置 =============

class BackendConfig:
    """后端API配置"""

    def __init__(self):
        # 从环境变量读取配置
        self.base_url = os.getenv('BACKEND_API_URL', 'http://host.docker.internal:8000')
        self.internal_token = os.getenv('INTERNAL_API_TOKEN', 'crewai-internal-secret-2025')
        self.timeout = float(os.getenv('BACKEND_API_TIMEOUT', '10.0'))
        self.max_retries = int(os.getenv('BACKEND_API_MAX_RETRIES', '3'))
        
        # 连接池配置
        self.pool_max_connections = int(os.getenv('BACKEND_POOL_MAX_CONNECTIONS', '100'))
        self.pool_max_keepalive = int(os.getenv('BACKEND_POOL_MAX_KEEPALIVE', '20'))
        self.pool_keepalive_expiry = float(os.getenv('BACKEND_POOL_KEEPALIVE_EXPIRY', '5.0'))
        
        # API特定超时配置（毫秒）
        self.membership_timeout_ms = int(os.getenv('BACKEND_MEMBERSHIP_TIMEOUT_MS', '2000'))  # 2秒
        self.user_profile_timeout_ms = int(os.getenv('BACKEND_USER_PROFILE_TIMEOUT_MS', '5000'))  # 5秒

        # 验证配置
        if not self.base_url:
            raise ValueError("BACKEND_API_URL environment variable is required")
        if not self.internal_token:
            raise ValueError("INTERNAL_API_TOKEN environment variable is required")

    def get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            'X-Internal-Token': self.internal_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }


# ============= 数据模型 =============

class MembershipTier(str, Enum):
    """会员等级"""
    FREE = "free"
    WARMHEART = "warmheart"      # 暖心会员
    ENERGY = "energy"            # 能量会员


class MembershipFeature(str, Enum):
    """会员功能"""
    AI_RECOMMENDATION = "ai_recommendation"    # AI推荐
    DATA_ANALYSIS = "data_analysis"            # 数据分析
    COACH_SERVICE = "coach_service"            # 教练服务


@dataclass
class UserProfile:
    """用户档案数据结构"""
    user_id: str
    basic_info: Dict[str, Any]
    nutrition_profile: Dict[str, Any]
    fitness_config: Dict[str, Any]
    fitness_goals: Dict[str, Any]
    strength_levels: Dict[str, Any]
    health_profile: Dict[str, Any]
    training_system: Dict[str, Any] = None  # ✅ 新增：训练系统字段
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.training_system is None:
            self.training_system = {}

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'UserProfile':
        """从API响应创建UserProfile对象"""
        return cls(
            user_id=data.get('user_id', ''),
            basic_info=data.get('basic_info', {}),
            nutrition_profile=data.get('nutrition_profile', {}),
            fitness_config=data.get('fitness_config', {}),
            fitness_goals=data.get('fitness_goals', {}),
            strength_levels=data.get('strength_levels', {}),
            health_profile=data.get('health_profile', {}),
            training_system=data.get('training_system', {}),  # ✅ 新增
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """将UserProfile对象转换为字典"""
        return {
            'user_id': self.user_id,
            'basic_info': self.basic_info,
            'nutrition_profile': self.nutrition_profile,
            'fitness_config': self.fitness_config,
            'fitness_goals': self.fitness_goals,
            'strength_levels': self.strength_levels,
            'health_profile': self.health_profile,
            'training_system': self.training_system,  # ✅ 新增
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }
    
    def get_volume_multiplier(self) -> float:
        """获取个性化容量系数（带边界检查）"""
        multiplier = self.training_system.get('personal_volume_multiplier', 1.0)
        return max(0.7, min(1.5, float(multiplier)))
    
    def get_user_type(self) -> str:
        """获取用户类型"""
        return self.training_system.get('user_type', 'other')
    
    def is_student(self) -> bool:
        """是否为大学生用户"""
        return self.get_user_type() == 'student'
    
    def is_worker(self) -> bool:
        """是否为上班族用户"""
        return self.get_user_type() == 'worker'

    def __iter__(self):
        """使UserProfile可迭代，支持dict()转换"""
        return iter(self.to_dict().items())

    def keys(self):
        """支持dict(obj)操作"""
        return self.to_dict().keys()

    def values(self):
        """支持dict(obj)操作"""
        return self.to_dict().values()

    def items(self):
        """支持dict(obj)操作"""
        return self.to_dict().items()

    def __getitem__(self, key):
        """支持obj[key]访问"""
        return self.to_dict()[key]

    def get(self, key, default=None):
        """支持dict.get()操作"""
        return self.to_dict().get(key, default)


@dataclass
class MembershipPermissions:
    """会员权限数据结构"""
    user_id: int
    tier: MembershipTier
    status: str
    permissions: Dict[str, bool]
    started_at: Optional[str] = None
    expired_at: Optional[str] = None

    def get(self, key: str, default=None):
        """支持字典式访问，兼容现有代码"""
        if key == 'tier':
            return self.tier.value if hasattr(self.tier, 'value') else str(self.tier)
        elif key == 'status':
            return self.status
        elif key == 'permissions':
            return self.permissions
        elif key == 'user_id':
            return self.user_id
        elif key == 'started_at':
            return self.started_at
        elif key == 'expired_at':
            return self.expired_at
        else:
            return default

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'user_id': self.user_id,
            'tier': self.tier.value if hasattr(self.tier, 'value') else str(self.tier),
            'status': self.status,
            'permissions': self.permissions,
            'started_at': self.started_at,
            'expired_at': self.expired_at
        }


# ============= 异常类 =============

class BackendAPIError(Exception):
    """后端API错误基类"""
    pass


class BackendAuthError(BackendAPIError):
    """认证错误（401）"""
    pass


class BackendNotFoundError(BackendAPIError):
    """资源未找到（404）"""
    pass


class BackendValidationError(BackendAPIError):
    """验证错误（400/422）"""
    pass


class BackendServerError(BackendAPIError):
    """服务器错误（500+）"""
    pass


# ============= HTTP客户端 =============

class BackendClient:
    """
    后端API客户端

    用于DAML-RAG Server调用yuzhen-backend的内部API

    使用示例:
    ```python
    client = BackendClient()

    # 获取用户档案（user_id应从认证系统动态获取）
    # profile = await client.get_user_profile(user_id)

    # 检查会员权限（user_id应从认证系统动态获取）
    # has_permission = await client.check_permission(
    #     user_id=user_id,
    #     feature=MembershipFeature.AI_RECOMMENDATION
    # )
    ```
    """

    def __init__(self, config: Optional[BackendConfig] = None, cache_manager=None):
        """
        初始化客户端

        Args:
            config: 后端配置（如果不提供，将从环境变量读取）
            cache_manager: 缓存管理器实例（可选）
        """
        self.config = config or BackendConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._is_warmed_up = False
        self.cache_manager = cache_manager
        
        # 连接池状态监控
        self._pool_stats = {
            'total_requests': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'warmup_time_ms': 0.0
        }

        logger.info(
            f"Backend client initialized: {self.config.base_url}",
            extra={
                'base_url': self.config.base_url,
                'timeout': self.config.timeout,
                'max_retries': self.config.max_retries,
                'pool_max_connections': self.config.pool_max_connections,
                'pool_max_keepalive': self.config.pool_max_keepalive,
                'cache_enabled': cache_manager is not None
            }
        )

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=self.config.get_headers(),
            timeout=self.config.timeout,
            limits=httpx.Limits(
                max_connections=self.config.pool_max_connections,
                max_keepalive_connections=self.config.pool_max_keepalive,
                keepalive_expiry=self.config.pool_keepalive_expiry
            )
        )
        # 预热连接池
        await self._warmup_connection_pool()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端（懒加载）"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=self.config.get_headers(),
                timeout=self.config.timeout,
                limits=httpx.Limits(
                    max_connections=self.config.pool_max_connections,
                    max_keepalive_connections=self.config.pool_max_keepalive,
                    keepalive_expiry=self.config.pool_keepalive_expiry
                )
            )
        return self._client
    
    async def _warmup_connection_pool(self):
        """
        预热连接池
        
        在启动时预创建连接，减少首次请求的延迟
        """
        if self._is_warmed_up:
            return
        
        import time
        start_time = time.time()
        
        try:
            logger.info("🔥 开始预热连接池...")
            
            # 发送健康检查请求来预热连接
            client = self._get_client()
            try:
                response = await client.get("/api/health", timeout=2.0)
                if response.is_success:
                    logger.info("✅ 连接池预热成功")
                else:
                    logger.warning(f"⚠️ 连接池预热响应异常: {response.status_code}")
            except httpx.TimeoutException:
                logger.warning("⚠️ 连接池预热超时，但连接已建立")
            except Exception as e:
                logger.warning(f"⚠️ 连接池预热失败: {e}")
            
            self._is_warmed_up = True
            warmup_time = (time.time() - start_time) * 1000
            self._pool_stats['warmup_time_ms'] = warmup_time
            
            logger.info(
                f"🔥 连接池预热完成: {warmup_time:.2f}ms",
                extra={'warmup_time_ms': warmup_time}
            )
            
        except Exception as e:
            logger.error(f"连接池预热异常: {e}")
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """
        获取连接池状态
        
        Returns:
            Dict[str, Any]: 连接池统计信息
        """
        return {
            'total_requests': self._pool_stats['total_requests'],
            'warmup_time_ms': self._pool_stats['warmup_time_ms'],
            'is_warmed_up': self._is_warmed_up,
            'config': {
                'max_connections': self.config.pool_max_connections,
                'max_keepalive': self.config.pool_max_keepalive,
                'keepalive_expiry': self.config.pool_keepalive_expiry
            }
        }

    def _handle_response_error(self, response: httpx.Response) -> None:
        """
        处理HTTP错误响应

        Raises:
            BackendAuthError: 401 认证错误
            BackendNotFoundError: 404 未找到
            BackendValidationError: 400/422 验证错误
            BackendServerError: 500+ 服务器错误
        """
        try:
            error_data = response.json()
            error_message = error_data.get('message', response.text)
        except Exception:
            error_message = response.text

        # 根据状态码抛出不同异常
        if response.status_code == 401:
            raise BackendAuthError(f"认证失败: {error_message}")
        elif response.status_code == 404:
            raise BackendNotFoundError(f"资源未找到: {error_message}")
        elif response.status_code in (400, 422):
            raise BackendValidationError(f"验证失败: {error_message}")
        elif response.status_code >= 500:
            raise BackendServerError(f"服务器错误: {error_message}")
        else:
            raise BackendAPIError(f"API错误 ({response.status_code}): {error_message}")

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        发送HTTP请求（带重试机制）

        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            endpoint: API端点
            **kwargs: 传递给httpx.request的参数

        Returns:
            API响应的data字段

        Raises:
            BackendAPIError: API错误
        """
        client = self._get_client()
        
        # 更新请求统计
        self._pool_stats['total_requests'] += 1

        for attempt in range(self.config.max_retries):
            try:
                logger.debug(
                    f"Backend API request: {method} {endpoint} (attempt {attempt + 1})",
                    extra={
                        'method': method,
                        'endpoint': endpoint,
                        'attempt': attempt + 1,
                    }
                )

                response = await client.request(method, endpoint, **kwargs)

                # 检查HTTP错误
                if not response.is_success:
                    self._handle_response_error(response)

                # 解析响应
                result = response.json()

                # 支持两种格式：
                # 格式1（新）：{code: 200, msg: "...", data: {...}}
                # 格式2（旧）：{success: true, message: "...", data: {...}}
                
                # 检查新格式（code字段）
                if 'code' in result:
                    if result.get('code') != 200:
                        error_msg = result.get('msg', 'Unknown error')
                        raise BackendAPIError(f"API业务错误: {error_msg}")
                # 检查旧格式（success字段）
                elif not result.get('success', False):
                    error_msg = result.get('message', 'Unknown error')
                    raise BackendAPIError(f"API业务错误: {error_msg}")

                logger.info(
                    f"Backend API success: {method} {endpoint}",
                    extra={
                        'method': method,
                        'endpoint': endpoint,
                        'status': response.status_code,
                    }
                )

                return result.get('data', {})

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                # 网络错误，可以重试
                if attempt < self.config.max_retries - 1:
                    logger.warning(
                        f"Backend API network error, retrying: {e}",
                        extra={
                            'method': method,
                            'endpoint': endpoint,
                            'attempt': attempt + 1,
                            'error': str(e),
                        }
                    )
                    continue
                else:
                    logger.error(
                        f"Backend API failed after {self.config.max_retries} retries",
                        extra={
                            'method': method,
                            'endpoint': endpoint,
                            'error': str(e),
                        }
                    )
                    raise BackendAPIError(f"网络错误: {e}")

            except BackendAPIError:
                # API错误，不重试
                raise

            except Exception as e:
                logger.error(
                    f"Backend API unexpected error: {e}",
                    extra={
                        'method': method,
                        'endpoint': endpoint,
                        'error': str(e),
                    },
                    exc_info=True
                )
                raise BackendAPIError(f"未知错误: {e}")

        # 不应该到达这里
        raise BackendAPIError("请求失败")

    # ============= 用户档案API =============

    async def get_user_profile(self, user_id: int, timeout: float = 5.0) -> Dict[str, Any]:
        """
        获取用户档案（带超时控制和降级机制，集成缓存）

        Args:
            user_id: 用户ID
            timeout: 超时时间（秒），默认5秒

        Returns:
            Dict[str, Any]: 用户档案字典（JSON可序列化）

        Raises:
            BackendNotFoundError: 用户不存在
            BackendAPIError: 其他API错误

        Example:
            ```python
            # user_id应从认证系统动态获取（如session、JWT token等）
            profile = await client.get_user_profile(user_id, timeout=5.0)
            print(f"用户年龄: {profile['basic_info']['age']}")
            print(f"健身目标: {profile['fitness_goals']['primary_goal']}")
            ```
        """
        user_id_str = str(user_id)
        
        # 1. 尝试从缓存获取
        if self.cache_manager:
            try:
                cached_profile = await self.cache_manager.get_user_profile(user_id_str)
                if cached_profile is not None:
                    is_fallback = cached_profile.get('_fallback', False)
                    if is_fallback:
                        logger.info(
                            f"✅ 用户档案缓存命中（降级数据）: user_id={user_id}",
                            extra={'user_id': user_id, 'cache_hit': True, 'is_fallback': True}
                        )
                    else:
                        logger.info(
                            f"✅ 用户档案缓存命中: user_id={user_id}",
                            extra={'user_id': user_id, 'cache_hit': True}
                        )
                    return cached_profile
                else:
                    logger.debug(
                        f"❌ 用户档案缓存未命中: user_id={user_id}",
                        extra={'user_id': user_id, 'cache_hit': False}
                    )
            except Exception as e:
                logger.warning(f"缓存查询失败，将从API获取: {e}")
        
        # 2. 缓存未命中，从API获取
        endpoint = f"/api/internal/user-profile/{user_id}"
        
        try:
            # 使用自定义超时
            original_timeout = self.config.timeout
            self.config.timeout = timeout
            
            data = await self._request("GET", endpoint)
            
            # 恢复原始超时
            self.config.timeout = original_timeout
            
            # 3. 写入缓存
            if self.cache_manager and data:
                try:
                    await self.cache_manager.set_user_profile(user_id_str, data)
                    logger.debug(
                        f"💾 用户档案已缓存: user_id={user_id}",
                        extra={'user_id': user_id}
                    )
                except Exception as e:
                    logger.warning(f"缓存写入失败: {e}")
            
            return data
            
        except httpx.TimeoutException:
            # 超时降级：返回空档案，允许工作流继续
            logger.warning(
                f"用户档案加载超时（{timeout}秒），使用降级策略: user_id={user_id}"
            )
            fallback_profile = self._get_fallback_profile(user_id)
            
            # 缓存降级档案
            if self.cache_manager:
                try:
                    await self.cache_manager.set_user_profile(user_id_str, fallback_profile)
                except Exception as e:
                    logger.warning(f"降级档案缓存失败: {e}")
            
            return fallback_profile
            
        except BackendNotFoundError:
            # 用户不存在：返回空档案
            logger.info(f"用户档案不存在，使用降级策略: user_id={user_id}")
            fallback_profile = self._get_fallback_profile(user_id)
            
            # 缓存降级档案
            if self.cache_manager:
                try:
                    await self.cache_manager.set_user_profile(user_id_str, fallback_profile)
                except Exception as e:
                    logger.warning(f"降级档案缓存失败: {e}")
            
            return fallback_profile
            
        except Exception as e:
            # 其他错误：记录日志并返回降级档案
            logger.error(
                f"用户档案加载失败，使用降级策略: user_id={user_id}, error={str(e)}"
            )
            fallback_profile = self._get_fallback_profile(user_id)
            
            # 缓存降级档案
            if self.cache_manager:
                try:
                    await self.cache_manager.set_user_profile(user_id_str, fallback_profile)
                except Exception as e:
                    logger.warning(f"降级档案缓存失败: {e}")
            
            return fallback_profile
    
    def _get_fallback_profile(self, user_id: int) -> Dict[str, Any]:
        """
        获取降级用户档案（当加载失败时使用）
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 降级用户档案
        """
        return {
            'user_id': str(user_id),
            'basic_info': {
                'age': 25,
                'gender': 'unknown',
                'height': 170,
                'weight': 65,
                'body_type': None,
                'user_type': 'other',
            },
            'nutrition_profile': {
                'daily_calories': 2000,
                'protein_g': 100,
                'carbs_g': 250,
                'fat_g': 65
            },
            'fitness_config': {
                'training_experience': 'beginner',
                'training_frequency': 3,
                'session_duration': 60,
                'preferred_training_time': None,
                'preferred_rest_pattern': None,
            },
            'fitness_goals': {
                'primary_goal': 'general_fitness',
                'target_weight': 65
            },
            'strength_levels': {},
            'health_profile': {
                'injuries': [],
                'medical_conditions': []
            },
            'training_system': {
                'preferred_training_time': None,
                'body_type': None,
                'user_type': 'other',
                'campus_name': None,
                'personal_volume_multiplier': 1.0,
                'personal_recovery_factor': 1.0,
                'last_volume_adjusted_at': None,
                'consecutive_training_weeks': 0,
            },
            'created_at': None,
            'updated_at': None,
            '_fallback': True  # 标记为降级档案
        }

    # ============= 会员权限API =============

    async def check_permission(
        self,
        user_id: int,
        feature: MembershipFeature
    ) -> bool:
        """
        检查用户是否有指定功能的权限

        Args:
            user_id: 用户ID
            feature: 功能名称（ai_recommendation, data_analysis, coach_service）

        Returns:
            bool: 是否有权限

        Example:
            ```python
            # user_id应从认证系统动态获取
            has_ai = await client.check_permission(
                user_id=user_id,
                feature=MembershipFeature.AI_RECOMMENDATION
            )
            if has_ai:
                # 提供AI推荐功能
                pass
            ```
        """
        endpoint = "/api/internal/membership/check-permission"
        
        # 使用配置的会员权限超时（2000ms）
        timeout = self.config.membership_timeout_ms / 1000.0
        original_timeout = self.config.timeout
        self.config.timeout = timeout
        
        try:
            data = await self._request(
                "POST",
                endpoint,
                json={
                    'user_id': user_id,
                    'feature': feature.value,
                }
            )
            return data.get('has_permission', False)
        finally:
            # 恢复原始超时
            self.config.timeout = original_timeout

    async def get_user_permissions(
        self,
        user_id: int,
        feature: Optional[MembershipFeature] = None
    ) -> Dict[str, Any]:
        """
        获取用户的完整权限信息（包括会员等级）

        Args:
            user_id: 用户ID
            feature: 可选，指定要检查的功能

        Returns:
            Dict包含: user_id, feature, has_permission, membership_tier, permissions

        Example:
            ```python
            # user_id应从认证系统动态获取
            perms = await client.get_user_permissions(user_id)
            print(f"会员等级: {perms['membership_tier']}")
            print(f"AI推荐: {perms['permissions']['ai_recommendation']}")
            ```
        """
        endpoint = "/api/internal/membership/check-permission"

        request_data = {'user_id': user_id}
        if feature:
            request_data['feature'] = feature.value
        else:
            # 如果不指定feature，默认查询ai_recommendation
            request_data['feature'] = MembershipFeature.AI_RECOMMENDATION.value

        # 使用配置的会员权限超时（2000ms）
        timeout = self.config.membership_timeout_ms / 1000.0
        original_timeout = self.config.timeout
        self.config.timeout = timeout
        
        try:
            data = await self._request("POST", endpoint, json=request_data)
            return data
        finally:
            # 恢复原始超时
            self.config.timeout = original_timeout

    async def get_user_membership(self, user_id: int) -> MembershipPermissions:
        """
        获取用户完整会员信息

        Args:
            user_id: 用户ID

        Returns:
            MembershipPermissions对象

        Example:
            ```python
            # user_id应从认证系统动态获取
            membership = await client.get_user_membership(user_id)
            print(f"会员等级: {membership.tier}")
            print(f"到期时间: {membership.expired_at}")
            ```
        """
        endpoint = f"/api/internal/membership/user/{user_id}"
        
        # 使用配置的会员权限超时（2000ms）
        timeout = self.config.membership_timeout_ms / 1000.0
        original_timeout = self.config.timeout
        self.config.timeout = timeout
        
        try:
            data = await self._request("GET", endpoint)

            return MembershipPermissions(
                user_id=user_id,
                tier=MembershipTier(data.get('tier', 'free')),
                status=data.get('status', 'active'),
                permissions=data.get('permissions', {}),
                started_at=data.get('started_at'),
                expired_at=data.get('expired_at'),
            )
        finally:
            # 恢复原始超时
            self.config.timeout = original_timeout
    
    async def get_membership_permissions_cached(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户会员权限（集成缓存）
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 会员权限数据
            
        Example:
            ```python
            # user_id应从认证系统动态获取
            membership = await client.get_membership_permissions_cached(user_id)
            print(f"会员等级: {membership['tier']}")
            print(f"权限: {membership['permissions']}")
            ```
        """
        user_id_str = str(user_id)
        
        # 1. 尝试从缓存获取
        if self.cache_manager:
            try:
                cached_membership = await self.cache_manager.get_membership_permissions(user_id_str)
                if cached_membership is not None:
                    is_fallback = cached_membership.get('_fallback', False)
                    if is_fallback:
                        logger.info(
                            f"✅ 会员权限缓存命中（降级数据）: user_id={user_id}",
                            extra={'user_id': user_id, 'cache_hit': True, 'is_fallback': True}
                        )
                    else:
                        logger.info(
                            f"✅ 会员权限缓存命中: user_id={user_id}",
                            extra={'user_id': user_id, 'cache_hit': True}
                        )
                    return cached_membership
                else:
                    logger.debug(
                        f"❌ 会员权限缓存未命中: user_id={user_id}",
                        extra={'user_id': user_id, 'cache_hit': False}
                    )
            except Exception as e:
                logger.warning(f"缓存查询失败，将从API获取: {e}")
        
        # 2. 缓存未命中，从API获取
        try:
            membership = await self.get_user_membership(user_id)
            membership_dict = membership.to_dict()
            
            # 3. 写入缓存
            if self.cache_manager and membership_dict:
                try:
                    await self.cache_manager.set_membership_permissions(user_id_str, membership_dict)
                    logger.debug(
                        f"💾 会员权限已缓存: user_id={user_id}",
                        extra={'user_id': user_id}
                    )
                except Exception as e:
                    logger.warning(f"缓存写入失败: {e}")
            
            return membership_dict
            
        except Exception as e:
            # 错误降级：返回默认权限
            logger.error(
                f"会员权限加载失败，使用降级策略: user_id={user_id}, error={str(e)}"
            )
            fallback_membership = self._get_fallback_membership(user_id)
            
            # 缓存降级数据
            if self.cache_manager:
                try:
                    await self.cache_manager.set_membership_permissions(user_id_str, fallback_membership)
                except Exception as e:
                    logger.warning(f"降级权限缓存失败: {e}")
            
            return fallback_membership
    
    def _get_fallback_membership(self, user_id: int) -> Dict[str, Any]:
        """
        获取降级会员权限（当加载失败时使用）
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 降级会员权限
        """
        return {
            'user_id': user_id,
            'tier': 'free',
            'status': 'active',
            'permissions': {
                'ai_recommendation': False,
                'data_analysis': False,
                'coach_service': False
            },
            'started_at': None,
            'expired_at': None,
            '_fallback': True  # 标记为降级数据
        }

    # ============= 用量统计API（会员自动化控制） =============
    # Requirements: 7.3, 7.4

    async def get_permissions(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户权限信息（用于PermissionChecker）
        
        Requirements: 7.3
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 权限信息，包含tier和permissions
            
        Example:
            ```python
            permissions = await client.get_permissions(user_id=1)
            print(f"会员等级: {permissions['tier']}")
            print(f"权限: {permissions['permissions']}")
            ```
        """
        endpoint = f"/api/internal/membership/user/{user_id}"
        
        # 使用配置的会员权限超时（2000ms）
        timeout = self.config.membership_timeout_ms / 1000.0
        original_timeout = self.config.timeout
        self.config.timeout = timeout
        
        try:
            data = await self._request("GET", endpoint)
            
            result = {
                'user_id': user_id,
                'tier': data.get('tier', 'free'),
                'status': data.get('status', 'active'),
                'permissions': data.get('permissions', {}),
                'started_at': data.get('started_at'),
                'expired_at': data.get('expired_at'),
            }
            
            logger.info(
                f"✅ 获取用户权限成功: user_id={user_id}, tier={result['tier']}",
                extra={'user_id': user_id, 'tier': result['tier']}
            )
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ 获取用户权限失败，使用降级数据: user_id={user_id}, error={e}")
            return self._get_fallback_membership(user_id)
        finally:
            # 恢复原始超时
            self.config.timeout = original_timeout

    async def check_usage(self, user_id: int, mode: str = "dag") -> Dict[str, Any]:
        """
        检查用户用量（用于PermissionChecker）
        
        Requirements: 7.3
        
        Args:
            user_id: 用户ID
            mode: 查询模式（dag或agent）
            
        Returns:
            Dict[str, Any]: 用量信息
            
        Example:
            ```python
            usage = await client.check_usage(user_id=1, mode="dag")
            if usage['can_execute']:
                print(f"可以执行，剩余{usage['dag_remaining']}次")
            else:
                print(f"已达上限: {usage['message']}")
            ```
        """
        endpoint = "/api/usage/check"
        
        try:
            data = await self._request(
                "POST",
                endpoint,
                json={
                    'user_id': user_id,
                    'mode': mode
                }
            )
            
            result = {
                'can_execute': data.get('can_execute', True),
                'dag_used': data.get('dag_used', 0),
                'dag_limit': data.get('dag_limit', -1),
                'dag_remaining': data.get('dag_remaining', -1),
                'agent_used': data.get('agent_used', 0),
                'agent_limit': data.get('agent_limit', -1),
                'agent_remaining': data.get('agent_remaining', -1),
                'dag_credits': data.get('dag_credits', 0),
                'agent_credits': data.get('agent_credits', 0),
                'message': data.get('message', ''),
            }
            
            logger.debug(
                f"✅ 用量检查成功: user_id={user_id}, mode={mode}, "
                f"can_execute={result['can_execute']}",
                extra={'user_id': user_id, 'mode': mode, 'usage': result}
            )
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ 用量检查失败，允许执行: user_id={user_id}, mode={mode}, error={e}")
            # 用量检查失败时，返回允许执行（避免阻塞用户）
            return {
                'can_execute': True,
                'dag_used': 0,
                'dag_limit': -1,
                'dag_remaining': -1,
                'agent_used': 0,
                'agent_limit': -1,
                'agent_remaining': -1,
                'dag_credits': 0,
                'agent_credits': 0,
                'message': '用量检查失败，暂时允许执行',
            }

    async def increment_usage(self, user_id: int, mode: str = "dag") -> Dict[str, Any]:
        """
        增加用量计数（用于PermissionChecker）
        
        Requirements: 7.4
        
        在查询完成后调用，增加用户的用量计数。
        
        Args:
            user_id: 用户ID
            mode: 查询模式（dag或agent）
            
        Returns:
            Dict[str, Any]: 更新后的用量信息
            
        Example:
            ```python
            result = await client.increment_usage(user_id=1, mode="dag")
            print(f"今日已使用: {result['dag_used']}次")
            ```
        """
        endpoint = "/api/usage/increment"
        
        try:
            data = await self._request(
                "POST",
                endpoint,
                json={
                    'user_id': user_id,
                    'mode': mode
                }
            )
            
            result = {
                'success': data.get('success', True),
                'dag_used': data.get('dag_used', 0),
                'dag_remaining': data.get('dag_remaining', -1),
                'agent_used': data.get('agent_used', 0),
                'agent_remaining': data.get('agent_remaining', -1),
            }
            
            logger.info(
                f"✅ 用量增加成功: user_id={user_id}, mode={mode}, "
                f"dag_used={result['dag_used']}, agent_used={result['agent_used']}",
                extra={'user_id': user_id, 'mode': mode, 'usage': result}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 用量增加失败: user_id={user_id}, mode={mode}, error={e}")
            # 用量增加失败不影响用户体验，只记录日志
            return {
                'success': False,
                'error': str(e),
                'dag_used': 0,
                'dag_remaining': -1,
                'agent_used': 0,
                'agent_remaining': -1,
            }

    async def get_today_usage(self, user_id: int) -> Dict[str, Any]:
        """
        获取用户今日用量统计
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 今日用量统计
            
        Example:
            ```python
            usage = await client.get_today_usage(user_id=1)
            print(f"今日DAG: {usage['dag_used']}/{usage['dag_limit']}")
            print(f"今日Agent: {usage['agent_used']}/{usage['agent_limit']}")
            ```
        """
        endpoint = "/api/usage/today"
        
        try:
            data = await self._request(
                "GET",
                endpoint,
                params={'user_id': user_id}
            )
            
            result = {
                'dag_used': data.get('dag_used', 0),
                'dag_limit': data.get('dag_limit', -1),
                'dag_remaining': data.get('dag_remaining', -1),
                'agent_used': data.get('agent_used', 0),
                'agent_limit': data.get('agent_limit', -1),
                'agent_remaining': data.get('agent_remaining', -1),
                'dag_credits': data.get('dag_credits', 0),
                'agent_credits': data.get('agent_credits', 0),
                'reset_time': data.get('reset_time'),
            }
            
            logger.debug(
                f"✅ 获取今日用量成功: user_id={user_id}",
                extra={'user_id': user_id, 'usage': result}
            )
            
            return result
            
        except Exception as e:
            logger.warning(f"⚠️ 获取今日用量失败: user_id={user_id}, error={e}")
            return {
                'dag_used': 0,
                'dag_limit': -1,
                'dag_remaining': -1,
                'agent_used': 0,
                'agent_limit': -1,
                'agent_remaining': -1,
                'dag_credits': 0,
                'agent_credits': 0,
                'reset_time': None,
            }

    # ============= 训练日志API =============

    async def get_training_logs(
        self,
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        mesocycle_id: Optional[str] = None,
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取用户训练日志列表
        
        Args:
            user_id: 用户ID
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            mesocycle_id: 中周期ID（可选）
            per_page: 每页数量，默认100
            
        Returns:
            List[Dict]: 训练日志列表
            
        Example:
            ```python
            logs = await client.get_training_logs(
                user_id=1,
                start_date="2025-12-01",
                end_date="2025-12-26"
            )
            for log in logs:
                print(f"日期: {log['session_date']}, 完成率: {log['completion_rate']}")
            ```
        """
        endpoint = f"/api/internal/training-logs/{user_id}"
        
        params = {'per_page': per_page}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        if mesocycle_id:
            params['mesocycle_id'] = mesocycle_id
        
        try:
            data = await self._request("GET", endpoint, params=params)
            
            # 返回rows字段（分页数据）
            logs = data.get('rows', [])
            
            logger.info(
                f"获取训练日志成功: user_id={user_id}, count={len(logs)}",
                extra={
                    'user_id': user_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'logs_count': len(logs)
                }
            )
            
            return logs
            
        except BackendNotFoundError:
            logger.info(f"用户训练日志不存在: user_id={user_id}")
            return []
        except Exception as e:
            logger.error(f"获取训练日志失败: user_id={user_id}, error={e}")
            return []

    async def get_training_log_stats(
        self,
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取用户训练统计
        
        Args:
            user_id: 用户ID
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            Dict: 训练统计数据
            
        Example:
            ```python
            stats = await client.get_training_log_stats(user_id=1)
            print(f"总训练次数: {stats['total_sessions']}")
            print(f"平均完成率: {stats['avg_completion_rate']}")
            ```
        """
        endpoint = f"/api/internal/training-logs/{user_id}/stats"
        
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        try:
            data = await self._request("GET", endpoint, params=params)
            
            logger.info(
                f"获取训练统计成功: user_id={user_id}",
                extra={'user_id': user_id, 'stats': data}
            )
            
            return data
            
        except Exception as e:
            logger.error(f"获取训练统计失败: user_id={user_id}, error={e}")
            return {
                'total_sessions': 0,
                'avg_completion_rate': 0.0,
                'avg_rpe': 0.0,
                'total_exercises': 0,
                'total_sets': 0
            }

    # ============= 个人最佳记录API =============

    async def get_personal_bests(
        self,
        user_id: int,
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """
        获取用户所有个人最佳记录
        
        Args:
            user_id: 用户ID
            per_page: 每页数量，默认100
            
        Returns:
            List[Dict]: 个人最佳记录列表
            
        Example:
            ```python
            pbs = await client.get_personal_bests(user_id=1)
            for pb in pbs:
                print(f"动作: {pb['exercise_name']}, 最佳: {pb['best_weight']}kg x {pb['best_reps']}")
            ```
        """
        endpoint = f"/api/internal/personal-bests/{user_id}"
        
        try:
            data = await self._request("GET", endpoint, params={'per_page': per_page})
            
            # 返回rows字段（分页数据）
            records = data.get('rows', [])
            
            logger.info(
                f"获取个人最佳记录成功: user_id={user_id}, count={len(records)}",
                extra={'user_id': user_id, 'records_count': len(records)}
            )
            
            return records
            
        except BackendNotFoundError:
            logger.info(f"用户个人最佳记录不存在: user_id={user_id}")
            return []
        except Exception as e:
            logger.error(f"获取个人最佳记录失败: user_id={user_id}, error={e}")
            return []

    async def get_personal_best(
        self,
        user_id: int,
        exercise_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取用户特定动作的个人最佳记录
        
        Args:
            user_id: 用户ID
            exercise_id: 动作ID
            
        Returns:
            Dict: 个人最佳记录，如果不存在返回None
            
        Example:
            ```python
            pb = await client.get_personal_best(user_id=1, exercise_id="squat")
            if pb:
                print(f"深蹲最佳: {pb['best_weight']}kg x {pb['best_reps']}")
            ```
        """
        endpoint = f"/api/internal/personal-bests/{user_id}/{exercise_id}"
        
        try:
            data = await self._request("GET", endpoint)
            
            logger.info(
                f"获取个人最佳记录成功: user_id={user_id}, exercise_id={exercise_id}",
                extra={'user_id': user_id, 'exercise_id': exercise_id}
            )
            
            return data
            
        except BackendNotFoundError:
            logger.info(f"个人最佳记录不存在: user_id={user_id}, exercise_id={exercise_id}")
            return None
        except Exception as e:
            logger.error(f"获取个人最佳记录失败: user_id={user_id}, exercise_id={exercise_id}, error={e}")
            return None

    async def update_personal_best(
        self,
        user_id: int,
        exercise_id: str,
        weight: float,
        reps: int,
        exercise_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新个人最佳记录
        
        Args:
            user_id: 用户ID
            exercise_id: 动作ID
            weight: 重量(kg)
            reps: 次数
            exercise_name: 动作名称（可选）
            
        Returns:
            Dict: 更新结果，包含is_new_record字段
            
        Example:
            ```python
            result = await client.update_personal_best(
                user_id=1,
                exercise_id="squat",
                weight=120,
                reps=5,
                exercise_name="深蹲"
            )
            if result['is_new_record']:
                print("恭喜！打破个人记录！")
            ```
        """
        endpoint = f"/api/internal/personal-bests/{user_id}/update"
        
        payload = {
            'exercise_id': exercise_id,
            'weight': weight,
            'reps': reps
        }
        if exercise_name:
            payload['exercise_name'] = exercise_name
        
        try:
            data = await self._request("POST", endpoint, json=payload)
            
            is_new_record = data.get('is_new_record', False)
            logger.info(
                f"更新个人最佳记录: user_id={user_id}, exercise_id={exercise_id}, "
                f"is_new_record={is_new_record}",
                extra={
                    'user_id': user_id,
                    'exercise_id': exercise_id,
                    'weight': weight,
                    'reps': reps,
                    'is_new_record': is_new_record
                }
            )
            
            return data
            
        except Exception as e:
            logger.error(
                f"更新个人最佳记录失败: user_id={user_id}, exercise_id={exercise_id}, error={e}"
            )
            raise BackendAPIError(f"更新个人最佳记录失败: {e}")

    async def get_strength_leaderboard(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取用户力量排行榜（按估算1RM排序）
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制，默认20
            
        Returns:
            List[Dict]: 力量排行榜
            
        Example:
            ```python
            leaderboard = await client.get_strength_leaderboard(user_id=1)
            for i, pb in enumerate(leaderboard, 1):
                print(f"{i}. {pb['exercise_name']}: {pb['estimated_1rm']}kg")
            ```
        """
        endpoint = f"/api/internal/personal-bests/{user_id}/leaderboard"
        
        try:
            data = await self._request("GET", endpoint, params={'limit': limit})
            
            leaderboard = data.get('leaderboard', [])
            
            logger.info(
                f"获取力量排行榜成功: user_id={user_id}, count={len(leaderboard)}",
                extra={'user_id': user_id, 'leaderboard_count': len(leaderboard)}
            )
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"获取力量排行榜失败: user_id={user_id}, error={e}")
            return []

    # ============= 对话记录API =============

    async def save_chat_session(
        self,
        session_id: str,
        user_id: Optional[int],
        user_query: str,
        llm_response: str,
        model_used: str,
        tools_used: List[str],
        metadata: Dict[str, Any],
        qdrant_point_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        保存对话记录到MySQL数据库
        
        Args:
            session_id: 会话UUID
            user_id: 用户ID（匿名用户为None）
            user_query: 用户问题
            llm_response: AI回答
            model_used: 使用的模型
            tools_used: 调用的工具列表
            metadata: 元数据
            qdrant_point_id: Qdrant向量点ID（可选）
            
        Returns:
            Dict包含保存的记录ID等信息
            
        Example:
            ```python
            result = await client.save_chat_session(
                session_id="uuid-xxx",
                user_id=1,
                user_query="如何增肌？",
                llm_response="推荐以下训练计划...",
                model_used="deepseek-chat",
                tools_used=["get_user_profile", "create_training_plan"],
                metadata={"few_shot_count": 3, "orchestrator_used": True},
                qdrant_point_id="qdrant-uuid-xxx"
            )
            print(f"记录ID: {result['id']}")
            ```
        """
        endpoint = "/api/internal/chat/save-session"
        
        data = await self._request(
            "POST",
            endpoint,
            json={
                'session_id': session_id,
                'user_id': user_id,
                'user_query': user_query,
                'llm_response': llm_response,
                'model_used': model_used,
                'tools_used': tools_used,
                'metadata': metadata,
                'qdrant_point_id': qdrant_point_id,
            }
        )
        
        return data

    async def update_chat_feedback(
        self,
        session_id: str,
        reward: float,
        feedback_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新对话反馈（用户评分）
        
        Args:
            session_id: 会话UUID
            reward: 用户评分 (1-5)
            feedback_text: 可选的文字反馈
            
        Returns:
            Dict包含更新结果
            
        Example:
            ```python
            result = await client.update_chat_feedback(
                session_id="uuid-xxx",
                reward=4.5,
                feedback_text="很有帮助！"
            )
            print(f"Feedback updated: {result['success']}")
            ```
        """
        endpoint = "/api/internal/chat/update-feedback"
        
        data = await self._request(
            "POST",
            endpoint,
            json={
                'session_id': session_id,
                'reward': reward,
                'feedback_text': feedback_text
            }
        )
        
        return data

    async def search_similar_conversations(
        self,
        query: str,
        user_id: Optional[int] = None,
        limit: int = 10,
        min_rating: float = 4.0,
        only_fewshot_eligible: bool = True,
        training_effect_filter: Optional[str] = None,
        days_back: int = 90
    ) -> Dict[str, Any]:
        """
        搜索相似的历史对话（Few-Shot降级策略）

        @requirements 4.6 - 检索器不可用时降级到后端API

        Args:
            query: 查询文本
            user_id: 用户ID（可选，用于个性化搜索）
            limit: 返回结果数量限制
            min_rating: 最低用户评分
            only_fewshot_eligible: 只返回符合Few-Shot条件的案例
            training_effect_filter: 训练效果过滤（excellent/good/fair/poor）
            days_back: 搜索最近多少天的对话

        Returns:
            Dict[str, Any]: 搜索结果，包含对话列表

        Example:
            ```python
            result = await client.search_similar_conversations(
                query="如何增肌",
                user_id=123,
                limit=5,
                min_rating=4.0,
                only_fewshot_eligible=True
            )
            conversations = result.get("conversations", [])
            ```
        """
        try:
            client = self._get_client()
            
            # 使用POST请求，参数放在body中
            payload = {
                "query": query,
                "limit": limit,
                "min_rating": min_rating,
                "only_fewshot_eligible": only_fewshot_eligible
            }

            if user_id is not None:
                payload["user_id"] = user_id
            
            if training_effect_filter is not None:
                payload["training_effect_filter"] = training_effect_filter

            # 调用后端的相似对话搜索API
            response = await client.post(
                "/api/internal/chat/search-similar",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            
            # 处理响应格式
            if data.get("code") == 200:
                result_data = data.get("data", {})
                conversations = result_data.get("conversations", [])
            else:
                conversations = []
                logger.warning(f"Search similar conversations returned non-200: {data.get('msg')}")

            logger.info(
                f"Similar conversations search completed: query='{query[:50]}...', "
                f"results={len(conversations)}, method={result_data.get('search_method', 'unknown')}",
                extra={
                    'query': query[:100],
                    'user_id': user_id,
                    'result_count': len(conversations),
                    'only_fewshot_eligible': only_fewshot_eligible
                }
            )

            return {
                "conversations": conversations,
                "total": len(conversations),
                "search_method": result_data.get("search_method", "keyword_fallback"),
                "filters_applied": result_data.get("filters_applied", {})
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Similar conversations search API not found (404)")
                return {"conversations": [], "total": 0, "search_method": "error"}
            else:
                logger.error(f"HTTP error in similar conversations search: {e}")
                raise BackendAPIError(f"相似对话搜索失败: {e.response.status_code}")

        except Exception as e:
            logger.error(f"Similar conversations search failed: {e}")
            raise BackendConnectionError(f"相似对话搜索连接失败: {str(e)}")

    # ============= 用户档案更新API =============

    async def update_volume_multiplier(
        self,
        user_id: int,
        new_multiplier: float,
        adjustment: float,
        reason: str
    ) -> Dict[str, Any]:
        """
        更新用户的容量系数
        
        Args:
            user_id: 用户ID
            new_multiplier: 新的容量系数（0.7-1.5）
            adjustment: 调整值
            reason: 调整原因
            
        Returns:
            Dict: 更新结果
            
        Example:
            ```python
            result = await client.update_volume_multiplier(
                user_id=1,
                new_multiplier=1.1,
                adjustment=0.1,
                reason="训练表现优秀，增加容量"
            )
            print(f"更新成功: {result['success']}")
            ```
        """
        endpoint = f"/api/internal/user-profile/{user_id}/volume-multiplier"
        
        payload = {
            'new_multiplier': new_multiplier,
            'adjustment': adjustment,
            'reason': reason
        }
        
        try:
            data = await self._request("PUT", endpoint, json=payload)
            
            logger.info(
                f"更新容量系数成功: user_id={user_id}, "
                f"new_multiplier={new_multiplier}, adjustment={adjustment:+.2f}",
                extra={
                    'user_id': user_id,
                    'new_multiplier': new_multiplier,
                    'adjustment': adjustment,
                    'reason': reason
                }
            )
            
            # 清除用户档案缓存
            if self.cache_manager:
                try:
                    await self.cache_manager.invalidate_user_profile(str(user_id))
                    logger.debug(f"已清除用户档案缓存: user_id={user_id}")
                except Exception as e:
                    logger.warning(f"清除缓存失败: {e}")
            
            return data
            
        except Exception as e:
            logger.error(
                f"更新容量系数失败: user_id={user_id}, error={e}"
            )
            raise BackendAPIError(f"更新容量系数失败: {e}")

    # ============= 三轨评分API =============

    async def submit_three_track_rating(
        self,
        session_id: str,
        personalization_scores: Dict[str, float],
        personalization_grade: str,
        fewshot_eligible: bool,
        eligibility_reason: str,
        overall_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        提交三轨评分（个性化感知评分部分）
        
        Args:
            session_id: 会话ID
            personalization_scores: 个性化感知评分
            personalization_grade: 个性化等级 (S/A/B/C/D)
            fewshot_eligible: 是否符合Few-Shot条件
            eligibility_reason: 资格判断原因
            overall_score: 综合评分
            
        Returns:
            Dict: 提交结果
            
        Example:
            ```python
            result = await client.submit_three_track_rating(
                session_id="uuid-xxx",
                personalization_scores={
                    'profile_utilization_rate': 85.0,
                    'goal_alignment': 80.0,
                    'uniqueness': 75.0,
                    'dynamic_adjustment': 70.0
                },
                personalization_grade="A",
                fewshot_eligible=True,
                eligibility_reason="三轨评分均达标"
            )
            ```
        """
        endpoint = "/api/internal/chat/update-personalization"
        
        try:
            data = await self._request(
                "POST",
                endpoint,
                json={
                    'session_id': session_id,
                    'profile_utilization_rate': personalization_scores.get('profile_utilization_rate', 0),
                    'goal_alignment': personalization_scores.get('goal_alignment', 0),
                    'uniqueness': personalization_scores.get('uniqueness', 0),
                    'dynamic_adjustment': personalization_scores.get('dynamic_adjustment', 0),
                    'personalization_grade': personalization_grade,
                    'fewshot_eligible': fewshot_eligible,
                    'overall_score': overall_score,
                    'eligibility_reason': eligibility_reason
                }
            )
            
            logger.info(
                f"三轨评分提交成功: session_id={session_id}, "
                f"grade={personalization_grade}, eligible={fewshot_eligible}",
                extra={
                    'session_id': session_id,
                    'personalization_grade': personalization_grade,
                    'fewshot_eligible': fewshot_eligible
                }
            )
            
            return data
            
        except Exception as e:
            logger.error(f"三轨评分提交失败: session_id={session_id}, error={e}")
            # 不抛出异常，允许工作流继续
            return {'success': False, 'error': str(e)}

    async def get_user_session_count(self, user_id: int) -> int:
        """
        获取用户会话数量（用于冷启动判断）
        
        Args:
            user_id: 用户ID
            
        Returns:
            int: 会话数量
        """
        endpoint = f"/api/internal/chat/session-count/{user_id}"
        
        try:
            data = await self._request("GET", endpoint)
            return data.get('count', 0)
        except Exception as e:
            logger.warning(f"获取用户会话数量失败: user_id={user_id}, error={e}")
            return 0

    async def check_fewshot_eligibility(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        检查会话Few-Shot资格
        
        Args:
            session_id: 会话ID
            
        Returns:
            Dict: 资格检查结果
        """
        endpoint = f"/api/internal/chat/fewshot-eligibility/{session_id}"
        
        try:
            data = await self._request("GET", endpoint)
            return data
        except Exception as e:
            logger.warning(f"检查Few-Shot资格失败: session_id={session_id}, error={e}")
            return {'eligible': False, 'reason': str(e)}

    # ============= 健康检查 =============

    async def health_check(self) -> Dict[str, Any]:
        """
        检查后端健康状态

        Returns:
            健康状态信息

        Example:
            ```python
            health = await client.health_check()
            if health['status'] == 'healthy':
                print("Backend is healthy")
            ```
        """
        try:
            client = self._get_client()
            response = await client.get("/api/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Backend health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }

    async def get_active_user_ids(self, limit: int = 20) -> List[int]:
        """
        获取活跃用户ID列表（用于预热缓存）
        
        从后端数据库获取实际存在的用户ID，避免预热不存在的用户。
        
        Args:
            limit: 返回的最大用户数量，默认20
            
        Returns:
            List[int]: 用户ID列表
            
        Example:
            ```python
            user_ids = await client.get_active_user_ids(limit=10)
            # [13, 14, 15, ...]
            ```
        """
        try:
            # 尝试调用后端API获取活跃用户列表
            # 如果后端没有这个API，则降级到获取users表的ID
            client = self._get_client()
            
            try:
                # 方案1：调用专门的活跃用户API
                response = await client.get(
                    "/api/internal/users/active",
                    params={"limit": limit},
                    timeout=3.0
                )
                if response.is_success:
                    data = response.json()
                    user_ids = data.get('data', [])
                    if user_ids:
                        return [int(uid) for uid in user_ids[:limit]]
            except Exception:
                pass  # API不存在，尝试其他方案
            
            try:
                # 方案2：获取最近登录的用户
                response = await client.get(
                    "/api/internal/users/recent",
                    params={"limit": limit},
                    timeout=3.0
                )
                if response.is_success:
                    data = response.json()
                    users = data.get('data', [])
                    if users:
                        return [int(u.get('id', u)) for u in users[:limit] if u]
            except Exception:
                pass  # API不存在，尝试其他方案
            
            # 方案3：返回空列表，让系统按需加载
            logger.info("ℹ️ 后端暂无活跃用户API，将按需加载用户档案")
            return []
            
        except Exception as e:
            logger.warning(f"⚠️ 获取活跃用户ID失败: {e}")
            return []

    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    # ============= 对话持久化API =============
    
    async def save_conversation_message(
        self,
        user_id: str,
        topic_id: str,
        message: Dict[str, Any],
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        保存对话消息到后端
        
        Args:
            user_id: 用户ID
            topic_id: 话题ID
            message: 消息数据字典，包含role和content
            session_id: 会话ID（可选）
            
        Returns:
            Dict: 保存结果
            
        Example:
            ```python
            result = await client.save_conversation_message(
                user_id="18",
                topic_id="topic-uuid",
                message={
                    "role": "user",
                    "content": "帮我制定训练计划",
                    "timestamp": "2026-01-02T20:00:00"
                }
            )
            ```
        """
        endpoint = "/api/internal/chat/save-message"
        
        try:
            # 后端API期望role和content在顶层
            request_data = {
                'user_id': user_id,
                'topic_id': topic_id,
                'role': message.get('role', 'user'),
                'content': message.get('content', ''),
            }
            
            # 添加可选的session_id
            if session_id:
                request_data['session_id'] = session_id
            elif message.get('session_id'):
                request_data['session_id'] = message.get('session_id')
            
            data = await self._request(
                "POST",
                endpoint,
                json=request_data
            )
            
            logger.debug(
                f"对话消息保存成功: user_id={user_id}, topic_id={topic_id}",
                extra={'user_id': user_id, 'topic_id': topic_id}
            )
            
            return data
            
        except Exception as e:
            logger.warning(f"对话消息保存失败: user_id={user_id}, topic_id={topic_id}, error={e}")
            # 不抛出异常，允许工作流继续
            return {'success': False, 'error': str(e)}
    
    async def save_conversation_topic(
        self,
        user_id: str,
        topic: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        保存对话话题到后端
        
        Args:
            user_id: 用户ID
            topic: 话题数据字典
            
        Returns:
            Dict: 保存结果
            
        Example:
            ```python
            result = await client.save_conversation_topic(
                user_id="18",
                topic={
                    "topic_id": "topic-uuid",
                    "title": "训练计划咨询",
                    "created_at": "2026-01-02T20:00:00"
                }
            )
            ```
        """
        endpoint = "/api/internal/chat/save-topic"
        
        try:
            data = await self._request(
                "POST",
                endpoint,
                json={
                    'user_id': user_id,
                    'topic': topic
                }
            )
            
            logger.debug(
                f"对话话题保存成功: user_id={user_id}, topic_id={topic.get('topic_id')}",
                extra={'user_id': user_id, 'topic_id': topic.get('topic_id')}
            )
            
            return data
            
        except Exception as e:
            logger.warning(f"对话话题保存失败: user_id={user_id}, error={e}")
            # 不抛出异常，允许工作流继续
            return {'success': False, 'error': str(e)}
    
    async def clear_conversation_topic(
        self,
        user_id: str,
        topic_id: str
    ) -> Dict[str, Any]:
        """
        从后端清除对话话题
        
        Args:
            user_id: 用户ID
            topic_id: 话题ID
            
        Returns:
            Dict: 清除结果
        """
        endpoint = f"/api/internal/chat/clear-topic/{topic_id}"
        
        try:
            data = await self._request(
                "DELETE",
                endpoint,
                params={'user_id': user_id}
            )
            
            logger.debug(
                f"对话话题清除成功: user_id={user_id}, topic_id={topic_id}",
                extra={'user_id': user_id, 'topic_id': topic_id}
            )
            
            return data
            
        except Exception as e:
            logger.warning(f"对话话题清除失败: user_id={user_id}, topic_id={topic_id}, error={e}")
            return {'success': False, 'error': str(e)}
    
    def log_cache_statistics(self):
        """记录缓存命中率统计"""
        if self.cache_manager:
            stats = self.cache_manager.get_statistics()
            logger.info(
                f"📊 缓存统计: "
                f"总请求={stats['total_requests']}, "
                f"命中率={stats['hit_rate']}%, "
                f"用户档案命中率={stats['user_profile_hit_rate']}%, "
                f"会员权限命中率={stats['membership_hit_rate']}%, "
                f"平均响应时间={stats['avg_response_time_ms']}ms",
                extra=stats
            )
            return stats
        else:
            logger.warning("缓存管理器未初始化，无法获取统计信息")
            return None


# ============= 便捷函数 =============

async def create_backend_client() -> BackendClient:
    """
    创建BackendClient实例（便捷函数）

    Returns:
        BackendClient实例

    Example:
        ```python
        async with create_backend_client() as client:
            profile = await client.get_user_profile(1)
        ```
    """
    return BackendClient()


# ============= 示例用法 =============

async def example_usage():
    """示例：如何使用BackendClient"""

    # 方式1: 使用上下文管理器（推荐）
    async with BackendClient() as client:
        # 获取用户档案（user_id应从认证系统动态获取）
        # user_id = request.session.get('user_id') 或从JWT token解析
        # profile = await client.get_user_profile(user_id)
        # print(f"用户ID: {profile.user_id}")
        # print(f"健身目标: {profile.fitness_goals['primary_goal']}")

        # 检查AI推荐权限
        # has_ai = await client.check_permission(
        #     user_id=user_id,
        #     feature=MembershipFeature.AI_RECOMMENDATION
        # )

        # if has_ai:
        #     print("✅ 用户有AI推荐权限")
        # else:
        #     print("❌ 用户没有AI推荐权限")

        # 获取完整会员信息
        # membership = await client.get_user_membership(user_id)
        # print(f"会员等级: {membership.tier}")
        # print(f"权限列表: {membership.permissions}")

        # 方式2: 手动管理（需要手动关闭）
           client = BackendClient()
    try:
        profile = await client.get_user_profile(user_id=1)
        print(profile)
    finally:
        await client.close()


if __name__ == "__main__":
    import asyncio

    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 运行示例
    asyncio.run(example_usage())
