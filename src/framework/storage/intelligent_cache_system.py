# -*- coding: utf-8 -*-
"""
智能缓存系统 v3.0 - 基于DAG模板的智能缓存管理

专为23个专业健身工具设计的智能缓存系统，支持多级缓存、TTL管理、基于DAG模板的预加载等功能。

核心特性：
1. 多级缓存架构 (Redis + Memory + Computation)
2. 智能TTL管理
3. 基于DAG模板的预加载机制（v3.0新增）
4. 缓存一致性验证（v3.0新增）
5. 缓存失效策略
6. 性能监控

版本: v3.0.0
日期: 2025-12-12
"""

import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import pickle

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """缓存级别"""
    L1_MEMORY = "l1_memory"    # 内存缓存
    L2_REDIS = "l2_redis"      # Redis缓存
    L3_COMPUTED = "l3_computed"  # 计算缓存


class CacheStrategy(Enum):
    """缓存策略"""
    TIME_BASED = "time_based"        # 基于时间
    ACCESS_BASED = "access_based"    # 基于访问
    SIZE_BASED = "size_based"        # 基于大小
    INTELLIGENT = "intelligent"      # 智能策略


@dataclass
class CacheConfig:
    """缓存配置"""
    enable_memory_cache: bool = True
    enable_redis_cache: bool = True
    memory_cache_size: int = 1000
    memory_cache_ttl: int = 3600  # 1小时
    redis_cache_ttl: int = 7200   # 2小时
    enable_preloading: bool = True
    preload_threshold: float = 0.7  # 预加载置信度阈值
    cleanup_interval: int = 300     # 清理间隔(秒)


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    data: Any
    level: CacheLevel
    created_at: float
    last_accessed: float
    access_count: int = 0
    ttl: int = 3600
    size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheStatistics:
    """缓存统计"""
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0
    preloads: int = 0
    evictions: int = 0
    total_size: int = 0
    average_access_time: float = 0.0


class IntelligentCacheSystem:
    """智能缓存系统"""

    def __init__(self, redis_client=None, config: CacheConfig = None):
        self.redis = redis_client
        self.config = config or CacheConfig()
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.access_patterns: Dict[str, List[float]] = defaultdict(list)
        self.cache_stats = CacheStatistics()
        self.tool_specific_configs = self._initialize_tool_configs()
        self.cleanup_task = None

        # 启动清理任务
        if self.config.enable_memory_cache:
            self._start_cleanup_task()

    def _initialize_tool_configs(self) -> Dict[str, Dict[str, Any]]:
        """初始化工具特定配置"""
        return {
            # 基础工具 - 长缓存
            "get_user_profile": {
                "ttl": 3600,      # 1小时
                "preload": True,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L2_REDIS  # 用户档案重要，放在Redis
            },
            "tdee_calculator": {
                "ttl": 1800,      # 30分钟
                "preload": True,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "chinese_food_analyzer": {
                "ttl": 7200,      # 2小时
                "preload": False,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "weight_calculator": {
                "ttl": 3600,      # 1小时
                "preload": True,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "rpe_recommender": {
                "ttl": 1800,      # 30分钟
                "preload": True,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L1_MEMORY
            },

            # 安全工具 - 短缓存
            "contraindications_checker": {
                "ttl": 300,       # 5分钟
                "preload": False,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "injury_risk_assessor": {
                "ttl": 300,       # 5分钟
                "preload": False,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "advanced_safety_monitor": {
                "ttl": 300,       # 5分钟
                "preload": False,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L1_MEMORY
            },

            # 动作工具 - 中等缓存
            "intelligent_exercise_selector": {
                "ttl": 600,       # 10分钟
                "preload": True,
                "strategy": CacheStrategy.ACCESS_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "exercise_alternative_finder": {
                "ttl": 600,       # 10分钟
                "preload": False,
                "strategy": CacheStrategy.ACCESS_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "safe_exercise_modifier": {
                "ttl": 600,       # 10分钟
                "preload": False,
                "strategy": CacheStrategy.ACCESS_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "movement_pattern_balancer": {
                "ttl": 600,       # 10分钟
                "preload": False,
                "strategy": CacheStrategy.ACCESS_BASED,
                "level": CacheLevel.L1_MEMORY
            },

            # 训练规划工具 - 无缓存
            "professional_program_designer": {
                "ttl": 0,         # 不缓存
                "preload": False,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L3_COMPUTED
            },
            "periodized_program_designer": {
                "ttl": 0,         # 不缓存
                "preload": False,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L3_COMPUTED
            },
            "training_split_designer": {
                "ttl": 0,         # 不缓存
                "preload": False,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L3_COMPUTED
            },
            "muscle_group_volume_calculator": {
                "ttl": 600,       # 10分钟
                "preload": False,
                "strategy": CacheStrategy.ACCESS_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "intelligent_weight_calculator": {
                "ttl": 300,       # 5分钟
                "preload": False,
                "strategy": CacheStrategy.ACCESS_BASED,
                "level": CacheLevel.L1_MEMORY
            },

            # 营养工具 - 中等缓存
            "nutrition_intake_analyzer": {
                "ttl": 1800,      # 30分钟
                "preload": True,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "exercise_nutrition_optimization": {
                "ttl": 600,       # 10分钟
                "preload": False,
                "strategy": CacheStrategy.ACCESS_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "muscle_recovery_nutrition": {
                "ttl": 600,       # 10分钟
                "preload": False,
                "strategy": CacheStrategy.ACCESS_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "nutrition_timing": {
                "ttl": 600,       # 10分钟
                "preload": False,
                "strategy": CacheStrategy.ACCESS_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "meal_plan_designer": {
                "ttl": 0,         # 不缓存
                "preload": False,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L3_COMPUTED
            },

            # 分析工具 - 长缓存
            "training_analytics_dashboard": {
                "ttl": 3600,      # 1小时
                "preload": False,
                "strategy": CacheStrategy.ACCESS_BASED,
                "level": CacheLevel.L1_MEMORY
            },
            "evidence_based_recommender": {
                "ttl": 3600,      # 1小时
                "preload": True,
                "strategy": CacheStrategy.ACCESS_BASED,
                "level": CacheLevel.L1_MEMORY
            },

            # 辅助工具
            "assess_strength_level": {
                "ttl": 7200,      # 2小时
                "preload": True,
                "strategy": CacheStrategy.TIME_BASED,
                "level": CacheLevel.L1_MEMORY
            }
        }

    async def get(self, tool_name: str, params: Dict[str, Any], user_id: str) -> Optional[Any]:
        """获取缓存数据"""
        cache_key = self._generate_cache_key(tool_name, params, user_id)
        start_time = time.time()

        try:
            # 1. 尝试L1内存缓存
            if self.config.enable_memory_cache and tool_name in self.tool_specific_configs:
                tool_config = self.tool_specific_configs[tool_name]
                if tool_config.get("level") == CacheLevel.L1_MEMORY:
                    result = await self._get_from_memory(cache_key)
                    if result is not None:
                        self._update_access_pattern(cache_key, start_time)
                        self.cache_stats.hits += 1
                        logger.debug(f"💾 L1缓存命中: {tool_name}")
                        return result

            # 2. 尝试L2 Redis缓存
            if self.config.enable_redis_cache and self.redis and tool_name in self.tool_specific_configs:
                tool_config = self.tool_specific_configs[tool_name]
                if tool_config.get("level") == CacheLevel.L2_REDIS:
                    result = await self._get_from_redis(cache_key)
                    if result is not None:
                        # 回填L1缓存
                        if self.config.enable_memory_cache:
                            await self._put_to_memory(cache_key, result, tool_config.get("ttl", 3600))
                        self._update_access_pattern(cache_key, start_time)
                        self.cache_stats.hits += 1
                        logger.debug(f"💾 L2缓存命中: {tool_name}")
                        return result
            
            # 3. 如果Redis不可用，尝试从内存缓存获取（降级策略）
            if tool_name in self.tool_specific_configs:
                tool_config = self.tool_specific_configs[tool_name]
                if tool_config.get("level") == CacheLevel.L2_REDIS and not self.redis:
                    # Redis不可用，尝试从内存缓存获取
                    if self.config.enable_memory_cache:
                        result = await self._get_from_memory(cache_key)
                        if result is not None:
                            self._update_access_pattern(cache_key, start_time)
                            self.cache_stats.hits += 1
                            logger.debug(f"💾 L1缓存命中(Redis降级): {tool_name}")
                            return result

            # 缓存未命中
            self.cache_stats.misses += 1
            logger.debug(f"❌ 缓存未命中: {tool_name}")
            return None

        except Exception as e:
            logger.error(f"缓存获取异常: {tool_name}, {e}")
            return None

    async def put(self, tool_name: str, params: Dict[str, Any], user_id: str, data: Any):
        """存储缓存数据"""
        if tool_name not in self.tool_specific_configs:
            return

        cache_key = self._generate_cache_key(tool_name, params, user_id)
        tool_config = self.tool_specific_configs[tool_name]
        ttl = tool_config.get("ttl", 3600)

        try:
            # 存储到L1内存缓存
            if self.config.enable_memory_cache and tool_config.get("level") == CacheLevel.L1_MEMORY:
                await self._put_to_memory(cache_key, data, ttl)

            # 存储到L2 Redis缓存
            if self.config.enable_redis_cache and self.redis and tool_config.get("level") == CacheLevel.L2_REDIS:
                await self._put_to_redis(cache_key, data, ttl)
            
            # 如果Redis不可用，降级到内存缓存
            if tool_config.get("level") == CacheLevel.L2_REDIS and not self.redis:
                if self.config.enable_memory_cache:
                    await self._put_to_memory(cache_key, data, ttl)
                    logger.debug(f"✅ 缓存存储成功(Redis降级到内存): {tool_name}")
                    return

            logger.debug(f"✅ 缓存存储成功: {tool_name}")

        except Exception as e:
            logger.error(f"缓存存储异常: {tool_name}, {e}")

    async def _get_from_memory(self, cache_key: str) -> Optional[Any]:
        """从内存缓存获取"""
        if cache_key not in self.memory_cache:
            return None

        entry = self.memory_cache[cache_key]

        # 检查TTL
        if time.time() - entry.created_at > entry.ttl:
            del self.memory_cache[cache_key]
            return None

        # 更新访问信息
        entry.last_accessed = time.time()
        entry.access_count += 1

        return entry.data

    async def _put_to_memory(self, cache_key: str, data: Any, ttl: int):
        """存储到内存缓存"""
        # 检查缓存大小限制
        if len(self.memory_cache) >= self.config.memory_cache_size:
            await self._evict_from_memory()

        entry = CacheEntry(
            key=cache_key,
            data=data,
            level=CacheLevel.L1_MEMORY,
            created_at=time.time(),
            last_accessed=time.time(),
            ttl=ttl,
            size=self._calculate_size(data)
        )

        self.memory_cache[cache_key] = entry
        self.cache_stats.total_size += entry.size

    async def _get_from_redis(self, cache_key: str) -> Optional[Any]:
        """从Redis缓存获取"""
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                return pickle.loads(cached_data)
        except Exception as e:
            logger.warning(f"Redis获取失败: {e}")
        return None

    async def _put_to_redis(self, cache_key: str, data: Any, ttl: int):
        """存储到Redis缓存"""
        try:
            serialized_data = pickle.dumps(data)
            await self.redis.setex(cache_key, ttl, serialized_data)
        except Exception as e:
            logger.warning(f"Redis存储失败: {e}")

    async def _evict_from_memory(self):
        """从内存缓存淘汰"""
        if not self.memory_cache:
            return

        # 使用LRU策略淘汰
        oldest_key = min(self.memory_cache.keys(), key=lambda k: self.memory_cache[k].last_accessed)
        evicted_entry = self.memory_cache.pop(oldest_key)
        self.cache_stats.total_size -= evicted_entry.size
        self.cache_stats.evictions += 1

        logger.debug(f"🗑️ LRU淘汰: {oldest_key}")

    def _generate_cache_key(self, tool_name: str, params: Dict[str, Any], user_id: str) -> str:
        """生成缓存键"""
        # 提取关键参数
        key_params = self._extract_key_params(tool_name, params)
        key_data = {
            "tool": tool_name,
            "user_id": user_id,
            "params": key_params
        }

        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return f"fitness_cache:{hashlib.md5(key_str.encode()).hexdigest()}"

    def _extract_key_params(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """提取关键参数"""
        key_params = {}

        if tool_name == "get_user_profile":
            key_params = {"user_id": params.get("user_id")}
        elif tool_name == "tdee_calculator":
            key_params = {
                "weight": params.get("weight"),
                "height": params.get("height"),
                "age": params.get("age"),
                "gender": params.get("gender"),
                "activity_level": params.get("activity_level")
            }
        elif tool_name == "intelligent_exercise_selector":
            key_params = {
                "muscle_group": params.get("muscle_group"),
                "training_goal": params.get("training_goal"),
                "difficulty_level": params.get("difficulty_level"),
                "available_equipment": params.get("available_equipment", [])
            }
        elif tool_name == "meal_plan_designer":
            key_params = {
                "user_id": params.get("user_id"),
                "dietary_preferences": params.get("dietary_preferences", []),
                "meals_per_day": params.get("meals_per_day")
            }
        else:
            # 默认：使用所有参数
            key_params = params

        return key_params

    def _calculate_size(self, data: Any) -> int:
        """计算数据大小"""
        try:
            return len(pickle.dumps(data))
        except:
            return 0

    def _update_access_pattern(self, cache_key: str, access_time: float):
        """更新访问模式"""
        self.access_patterns[cache_key].append(access_time)
        # 保留最近100次访问记录
        if len(self.access_patterns[cache_key]) > 100:
            self.access_patterns[cache_key] = self.access_patterns[cache_key][-100:]

    def _start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.config.cleanup_interval)
                    await self._cleanup_expired_entries()
                except Exception as e:
                    logger.error(f"缓存清理异常: {e}")

        # 只在有运行中的事件循环时启动清理任务
        try:
            loop = asyncio.get_running_loop()
            self.cleanup_task = asyncio.create_task(cleanup_loop())
        except RuntimeError:
            # 没有运行中的事件循环，稍后手动启动
            self.cleanup_task = None
            logger.debug("缓存清理任务将在事件循环可用时启动")

    async def _cleanup_expired_entries(self):
        """清理过期条目"""
        current_time = time.time()
        expired_keys = []

        for cache_key, entry in self.memory_cache.items():
            if current_time - entry.created_at > entry.ttl:
                expired_keys.append(cache_key)

        for key in expired_keys:
            entry = self.memory_cache.pop(key)
            self.cache_stats.total_size -= entry.size
            self.cache_stats.evictions += 1

        if expired_keys:
            logger.debug(f"🧹 清理过期缓存: {len(expired_keys)}个条目")

    async def preload_likely_data(
        self,
        intent_result: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """预加载可能需要的数据（兼容旧接口）"""
        preloaded_data = {}
        confidence = intent_result.get("confidence", 0.0)

        if confidence < self.config.preload_threshold:
            return preloaded_data

        logger.info(f"🚀 开始预加载数据，置信度: {confidence:.2f}")

        # 基于意图预加载
        required_tools = intent_result.get("required_tools", [])
        optional_tools = intent_result.get("optional_tools", [])

        # 优先预加载高置信度的必需工具
        for tool_name in required_tools:
            if tool_name in self.tool_specific_configs:
                tool_config = self.tool_specific_configs[tool_name]
                if tool_config.get("preload", False):
                    try:
                        # 构建预加载参数
                        preload_params = self._build_preload_params(tool_name, user_profile)
                        preloaded_result = await self._execute_preload(tool_name, preload_params, user_profile)

                        if preloaded_result:
                            preloaded_data[tool_name] = preloaded_result
                            self.cache_stats.preloads += 1
                            logger.debug(f"✅ 预加载成功: {tool_name}")

                    except Exception as e:
                        logger.warning(f"预加载失败: {tool_name}, {e}")

        return preloaded_data

    async def preload_from_dag_template(
        self,
        template,
        user_profile: Dict[str, Any],
        user_id: str,
        execute_func: callable = None
    ) -> Dict[str, Any]:
        """
        基于DAG模板的智能预加载（v3.0新增）
        
        根据DAG模板的工具链，智能预加载可能需要的数据。
        
        Args:
            template: DAG模板对象
            user_profile: 用户档案
            user_id: 用户ID
            execute_func: 工具执行函数（可选）
            
        Returns:
            Dict[str, Any]: 预加载的数据
        """
        preloaded_data = {}
        
        if not self.config.enable_preloading:
            return preloaded_data
        
        logger.info(f"🚀 基于DAG模板预加载: {template.name}")
        
        # 1. 识别可预加载的工具
        preloadable_tools = self._identify_preloadable_tools(template)
        
        if not preloadable_tools:
            logger.debug("没有可预加载的工具")
            return preloaded_data
        
        logger.info(f"📦 识别到 {len(preloadable_tools)} 个可预加载工具")
        
        # 2. 按优先级排序（基础工具优先）
        sorted_tools = self._sort_tools_by_priority(preloadable_tools, template)
        
        # 3. 并行预加载（无依赖的工具）
        preload_tasks = []
        for tool_name in sorted_tools:
            # 检查是否已在缓存中
            tool_params = self._build_preload_params(tool_name, user_profile)
            cache_key = self._generate_cache_key(tool_name, tool_params, user_id)
            
            # 如果已缓存，跳过
            cached_result = await self.get(tool_name, tool_params, user_id)
            if cached_result is not None:
                preloaded_data[tool_name] = cached_result
                logger.debug(f"✅ 使用已缓存数据: {tool_name}")
                continue
            
            # 如果提供了执行函数，创建预加载任务
            if execute_func:
                task = self._create_preload_task(
                    tool_name,
                    tool_params,
                    user_id,
                    execute_func
                )
                preload_tasks.append(task)
        
        # 4. 执行预加载任务
        if preload_tasks:
            logger.info(f"⚡ 并行执行 {len(preload_tasks)} 个预加载任务")
            results = await asyncio.gather(*preload_tasks, return_exceptions=True)
            
            # 处理结果
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"预加载任务失败: {result}")
                elif result:
                    tool_name, data = result
                    preloaded_data[tool_name] = data
                    self.cache_stats.preloads += 1
                    logger.debug(f"✅ 预加载成功: {tool_name}")
        
        logger.info(f"✅ DAG模板预加载完成: {len(preloaded_data)} 个工具")
        return preloaded_data
    
    def _identify_preloadable_tools(self, template) -> List[str]:
        """识别可预加载的工具"""
        preloadable = []
        
        # 检查必需工具
        for tool_name in template.required_tools:
            # 转换工具名格式
            registry_tool_name = tool_name.replace('-', '_')
            
            if registry_tool_name in self.tool_specific_configs:
                tool_config = self.tool_specific_configs[registry_tool_name]
                if tool_config.get("preload", False) and tool_config.get("ttl", 0) > 0:
                    preloadable.append(registry_tool_name)
        
        # 检查可选工具（选择性预加载）
        for tool_name in template.optional_tools[:2]:  # 只预加载前2个可选工具
            registry_tool_name = tool_name.replace('-', '_')
            
            if registry_tool_name in self.tool_specific_configs:
                tool_config = self.tool_specific_configs[registry_tool_name]
                if tool_config.get("preload", False) and tool_config.get("ttl", 0) > 0:
                    preloadable.append(registry_tool_name)
        
        return preloadable
    
    def _sort_tools_by_priority(self, tools: List[str], template) -> List[str]:
        """按优先级排序工具"""
        # 定义优先级顺序
        priority_order = {
            "get_user_profile": 1,
            "tdee_calculator": 2,
            "assess_strength_level": 3,
            "rpe_recommender": 4,
            "weight_calculator": 5,
            "intelligent_exercise_selector": 6,
            "nutrition_intake_analyzer": 7,
            "evidence_based_recommender": 8
        }
        
        return sorted(tools, key=lambda t: priority_order.get(t, 99))
    
    async def _create_preload_task(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_id: str,
        execute_func: callable
    ):
        """创建预加载任务"""
        try:
            # 执行工具
            result = await execute_func(tool_name, params)
            
            # 存储到缓存
            await self.put(tool_name, params, user_id, result)
            
            return (tool_name, result)
        except Exception as e:
            logger.warning(f"预加载任务失败: {tool_name}, {e}")
            return None
    
    async def validate_cache_consistency(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_id: str,
        fresh_result: Any
    ) -> Dict[str, Any]:
        """
        验证缓存一致性（v3.0新增）
        
        比较缓存结果和新鲜结果，检测数据漂移。
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            user_id: 用户ID
            fresh_result: 新鲜的执行结果
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        cache_key = self._generate_cache_key(tool_name, params, user_id)
        cached_result = await self.get(tool_name, params, user_id)
        
        validation_result = {
            "tool_name": tool_name,
            "has_cached": cached_result is not None,
            "is_consistent": False,
            "drift_detected": False,
            "differences": [],
            "recommendation": "use_fresh"
        }
        
        if cached_result is None:
            validation_result["recommendation"] = "use_fresh"
            return validation_result
        
        # 比较结果
        try:
            is_consistent, differences = self._compare_results(
                cached_result,
                fresh_result,
                tool_name
            )
            
            validation_result["is_consistent"] = is_consistent
            validation_result["differences"] = differences
            
            if is_consistent:
                validation_result["recommendation"] = "use_cached"
            else:
                validation_result["drift_detected"] = True
                validation_result["recommendation"] = "use_fresh_and_update_cache"
                
                # 更新缓存
                await self.put(tool_name, params, user_id, fresh_result)
                logger.warning(
                    f"⚠️ 检测到缓存漂移: {tool_name}, "
                    f"差异数: {len(differences)}"
                )
        
        except Exception as e:
            logger.error(f"缓存一致性验证失败: {tool_name}, {e}")
            validation_result["recommendation"] = "use_fresh"
        
        return validation_result
    
    def _compare_results(
        self,
        cached: Any,
        fresh: Any,
        tool_name: str
    ) -> Tuple[bool, List[str]]:
        """比较两个结果"""
        differences = []
        
        # 如果类型不同，直接判定不一致
        if type(cached) != type(fresh):
            differences.append(f"类型不同: {type(cached)} vs {type(fresh)}")
            return False, differences
        
        # 字典类型比较
        if isinstance(cached, dict) and isinstance(fresh, dict):
            return self._compare_dicts(cached, fresh, tool_name)
        
        # 列表类型比较
        elif isinstance(cached, list) and isinstance(fresh, list):
            return self._compare_lists(cached, fresh, tool_name)
        
        # 基本类型比较
        else:
            if cached != fresh:
                differences.append(f"值不同: {cached} vs {fresh}")
                return False, differences
            return True, []
    
    def _compare_dicts(
        self,
        cached: Dict,
        fresh: Dict,
        tool_name: str
    ) -> Tuple[bool, List[str]]:
        """比较字典"""
        differences = []
        
        # 检查键集合
        cached_keys = set(cached.keys())
        fresh_keys = set(fresh.keys())
        
        if cached_keys != fresh_keys:
            missing_in_fresh = cached_keys - fresh_keys
            missing_in_cached = fresh_keys - cached_keys
            
            if missing_in_fresh:
                differences.append(f"新结果缺少键: {missing_in_fresh}")
            if missing_in_cached:
                differences.append(f"缓存缺少键: {missing_in_cached}")
        
        # 比较共同键的值
        common_keys = cached_keys & fresh_keys
        for key in common_keys:
            # 跳过时间戳字段
            if key in ['created_at', 'updated_at', 'timestamp', 'last_modified']:
                continue
            
            cached_val = cached[key]
            fresh_val = fresh[key]
            
            # 数值类型：允许小误差
            if isinstance(cached_val, (int, float)) and isinstance(fresh_val, (int, float)):
                if abs(cached_val - fresh_val) > 0.01:  # 1%误差
                    differences.append(f"键 '{key}' 值差异: {cached_val} vs {fresh_val}")
            
            # 其他类型：精确比较
            elif cached_val != fresh_val:
                differences.append(f"键 '{key}' 值不同")
        
        is_consistent = len(differences) == 0
        return is_consistent, differences
    
    def _compare_lists(
        self,
        cached: List,
        fresh: List,
        tool_name: str
    ) -> Tuple[bool, List[str]]:
        """比较列表"""
        differences = []
        
        # 长度比较
        if len(cached) != len(fresh):
            differences.append(f"列表长度不同: {len(cached)} vs {len(fresh)}")
            return False, differences
        
        # 元素比较（简化版）
        for i, (c_item, f_item) in enumerate(zip(cached, fresh)):
            if c_item != f_item:
                differences.append(f"索引 {i} 元素不同")
        
        is_consistent = len(differences) == 0
        return is_consistent, differences

    def _build_preload_params(self, tool_name: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """构建预加载参数"""
        base_params = {"user_profile": user_profile, "user_id": user_profile.get("user_id")}

        if tool_name == "tdee_calculator":
            base_params.update({
                "weight": user_profile.get("weight"),
                "height": user_profile.get("height"),
                "age": user_profile.get("age"),
                "gender": user_profile.get("gender"),
                "activity_level": user_profile.get("activity_level", "moderate")
            })
        elif tool_name == "intelligent_exercise_selector":
            base_params.update({
                "muscle_group": user_profile.get("target_muscle_groups", ["胸部"])[0],
                "training_goal": user_profile.get("fitness_goals", ["增肌"])[0],
                "available_equipment": user_profile.get("available_equipment", ["哑铃"]),
                "difficulty_level": user_profile.get("fitness_level", "beginner")
            })
        elif tool_name == "evidence_based_recommender":
            base_params.update({
                "query": f"针对{user_profile.get('fitness_goals', ['健身'])[0]}的建议",
                "preference": "balanced"
            })

        return base_params

    async def _execute_preload(self, tool_name: str, params: Dict[str, Any], user_id: str) -> Optional[Any]:
        """执行预加载"""
        # 这里应该调用实际的工具执行逻辑
        # 暂时返回None，表示需要实际实现
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self.cache_stats.hits + self.cache_stats.misses
        if total_requests > 0:
            self.cache_stats.hit_rate = (self.cache_stats.hits / total_requests) * 100

        return {
            "stats": {
                "hits": self.cache_stats.hits,
                "misses": self.cache_stats.misses,
                "hit_rate": self.cache_stats.hit_rate,
                "preloads": self.cache_stats.preloads,
                "evictions": self.cache_stats.evictions,
                "total_size": self.cache_stats.total_size,
                "memory_cache_size": len(self.memory_cache)
            },
            "tool_configs": {
                tool: {
                    "ttl": config.get("ttl"),
                    "preload": config.get("preload"),
                    "level": config.get("level").value if config.get("level") else None
                }
                for tool, config in self.tool_specific_configs.items()
            },
            "access_patterns": {
                key: {
                    "access_count": len(pattern),
                    "last_access": pattern[-1] if pattern else None
                }
                for key, pattern in self.access_patterns.items()
            }
        }

    async def clear_cache(self, tool_name: Optional[str] = None):
        """清理缓存"""
        if tool_name:
            # 清理特定工具的缓存
            keys_to_remove = [
                key for key in self.memory_cache.keys()
                if key.endswith(f":{tool_name}")
            ]
            for key in keys_to_remove:
                entry = self.memory_cache.pop(key)
                self.cache_stats.total_size -= entry.size
        else:
            # 清理所有缓存
            self.memory_cache.clear()
            if self.redis:
                await self.redis.flushdb()

        logger.info(f"🧹 缓存清理完成: {tool_name or '全部'}")

    async def shutdown(self):
        """关闭缓存系统"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("🔄 缓存系统已关闭")


class SmartCacheManager:
    """智能缓存管理器（v3.0增强）"""

    def __init__(self, cache_system: IntelligentCacheSystem):
        self.cache_system = cache_system
        self.user_patterns = defaultdict(dict)
        self.preload_history = defaultdict(list)  # v3.0新增：预加载历史

    async def get_tool_result(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_id: str,
        execute_func: callable
    ) -> Any:
        """智能获取工具结果（带缓存）"""
        # 尝试从缓存获取
        cached_result = await self.cache_system.get(tool_name, params, user_id)
        if cached_result is not None:
            return cached_result

        # 缓存未命中，执行工具
        logger.info(f"⚡ 执行工具: {tool_name}")
        result = await execute_func(params)

        # 存储到缓存
        await self.cache_system.put(tool_name, params, user_id, result)

        return result

    async def preload_user_context(
        self,
        intent_result: Dict[str, Any],
        user_profile: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """预加载用户上下文（兼容旧接口）"""
        return await self.cache_system.preload_likely_data(intent_result, user_profile)

    async def preload_from_template(
        self,
        template,
        user_profile: Dict[str, Any],
        user_id: str,
        execute_func: callable = None
    ) -> Dict[str, Any]:
        """
        基于DAG模板预加载（v3.0新增）
        
        Args:
            template: DAG模板对象
            user_profile: 用户档案
            user_id: 用户ID
            execute_func: 工具执行函数
            
        Returns:
            Dict[str, Any]: 预加载的数据
        """
        start_time = time.time()
        
        # 调用缓存系统的预加载方法
        preloaded_data = await self.cache_system.preload_from_dag_template(
            template=template,
            user_profile=user_profile,
            user_id=user_id,
            execute_func=execute_func
        )
        
        # 记录预加载历史
        preload_record = {
            "timestamp": start_time,
            "template_id": template.template_id,
            "template_name": template.name,
            "tools_preloaded": list(preloaded_data.keys()),
            "preload_count": len(preloaded_data),
            "duration": time.time() - start_time
        }
        self.preload_history[user_id].append(preload_record)
        
        # 保留最近10条记录
        if len(self.preload_history[user_id]) > 10:
            self.preload_history[user_id] = self.preload_history[user_id][-10:]
        
        logger.info(
            f"✅ 模板预加载完成: {template.name}, "
            f"工具数: {len(preloaded_data)}, "
            f"耗时: {preload_record['duration']:.2f}s"
        )
        
        return preloaded_data

    async def validate_and_refresh_cache(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_id: str,
        fresh_result: Any
    ) -> Dict[str, Any]:
        """
        验证并刷新缓存（v3.0新增）
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            user_id: 用户ID
            fresh_result: 新鲜的执行结果
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        validation_result = await self.cache_system.validate_cache_consistency(
            tool_name=tool_name,
            params=params,
            user_id=user_id,
            fresh_result=fresh_result
        )
        
        # 如果检测到漂移，记录日志
        if validation_result.get("drift_detected"):
            logger.warning(
                f"⚠️ 缓存漂移: {tool_name}, "
                f"差异: {len(validation_result.get('differences', []))}"
            )
        
        return validation_result

    def update_user_pattern(self, user_id: str, tool_name: str, usage_count: int = 1):
        """更新用户使用模式"""
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = {}

        if tool_name not in self.user_patterns[user_id]:
            self.user_patterns[user_id][tool_name] = 0

        self.user_patterns[user_id][tool_name] += usage_count

    def get_user_pattern(self, user_id: str) -> Dict[str, int]:
        """获取用户使用模式"""
        return self.user_patterns.get(user_id, {})

    def get_preload_history(self, user_id: str) -> List[Dict[str, Any]]:
        """获取预加载历史（v3.0新增）"""
        return self.preload_history.get(user_id, [])

    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计（v3.0增强）"""
        base_stats = self.cache_system.get_statistics()
        
        # 添加预加载统计
        total_preloads = sum(
            len(history) for history in self.preload_history.values()
        )
        
        base_stats["preload_statistics"] = {
            "total_preload_sessions": total_preloads,
            "users_with_preload": len(self.preload_history),
            "average_tools_per_preload": (
                sum(
                    record["preload_count"]
                    for history in self.preload_history.values()
                    for record in history
                ) / total_preloads if total_preloads > 0 else 0
            )
        }
        
        return base_stats
