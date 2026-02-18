"""
运行时配置管理模块

提供运行时配置的统一管理，支持：
- 从 YAML 配置文件加载
- 环境变量覆盖
- 配置验证
- 动态刷新

版本: v1.0.0
日期: 2025-12-28

Requirements: 7.1, 7.2, 7.3, 7.4
"""

import os
import yaml
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """配置验证错误"""
    pass


class UserLevel(Enum):
    """用户等级枚举"""
    FREE = "free"
    PAID = "paid"
    VIP = "vip"
    SYSTEM = "system"


@dataclass
class CacheConfig:
    """缓存配置"""
    # L1 内存缓存
    l1_enabled: bool = True
    l1_max_size: int = 1000
    l1_max_memory_mb: int = 100
    
    # L2 Redis 缓存
    l2_enabled: bool = True
    l2_host: str = "localhost"
    l2_port: int = 6379
    l2_db: int = 0
    l2_password: Optional[str] = None
    l2_max_connections: int = 50
    
    # 默认 TTL
    default_ttl: int = 300
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        if self.l1_max_size <= 0:
            errors.append("l1_max_size 必须大于 0")
        if self.l2_port <= 0 or self.l2_port > 65535:
            errors.append("l2_port 必须在 1-65535 范围内")
        if self.default_ttl < 0:
            errors.append("default_ttl 不能为负数")
        return errors


@dataclass
class ConnectionPoolConfig:
    """连接池配置"""
    # MySQL
    mysql_min_size: int = 10
    mysql_max_size: int = 50
    mysql_max_idle_time: int = 60
    mysql_acquire_timeout: int = 2
    
    # Neo4j
    neo4j_min_size: int = 5
    neo4j_max_size: int = 20
    neo4j_max_idle_time: int = 120
    neo4j_acquire_timeout: int = 2
    
    # HTTP
    http_min_size: int = 20
    http_max_size: int = 100
    http_keepalive_timeout: int = 30
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        if self.mysql_min_size > self.mysql_max_size:
            errors.append("mysql_min_size 不能大于 mysql_max_size")
        if self.neo4j_min_size > self.neo4j_max_size:
            errors.append("neo4j_min_size 不能大于 neo4j_max_size")
        if self.http_min_size > self.http_max_size:
            errors.append("http_min_size 不能大于 http_max_size")
        return errors


@dataclass
class LLMConfig:
    """LLM 配置"""
    # 主要后端
    primary_backend: str = "anthropic"

    # 降级后端
    fallback_backends: List[str] = field(default_factory=lambda: ["deepseek", "template"])
    
    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    timeout: int = 30
    
    # 流式配置
    streaming_enabled: bool = True
    streaming_chunk_size: int = 1024
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        if self.max_retries < 0:
            errors.append("max_retries 不能为负数")
        if self.timeout <= 0:
            errors.append("timeout 必须大于 0")
        if self.retry_delay < 0:
            errors.append("retry_delay 不能为负数")
        return errors


@dataclass
class ConcurrencyConfig:
    """并发配置"""
    max_concurrent: int = 100
    max_queue_size: int = 200
    timeout: int = 30
    
    # 用户分级限流
    free_max_concurrent: int = 10
    paid_max_concurrent: int = 50
    vip_max_concurrent: int = 100
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        if self.max_concurrent <= 0:
            errors.append("max_concurrent 必须大于 0")
        if self.max_queue_size < 0:
            errors.append("max_queue_size 不能为负数")
        return errors


@dataclass
class WorkflowConfig:
    """工作流配置"""
    global_timeout: int = 30
    
    # 步骤超时（秒）
    step_1_timeout: float = 0.5
    step_2_timeout: float = 0.2
    step_3_timeout: float = 0.3
    step_4_timeout: float = 0.5
    step_5_timeout: float = 0.1
    step_6_timeout: float = 1.0
    step_7_timeout: float = 5.0
    step_8_timeout: float = 3.0
    step_9_timeout: float = 1.0
    step_10_timeout: float = 20.0
    step_11_timeout: float = 0.5
    
    # 并行执行
    parallel_step_1_2: bool = True
    parallel_step_3_4: bool = True
    max_parallel_workers: int = 4
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        if self.global_timeout <= 0:
            errors.append("global_timeout 必须大于 0")
        return errors
    
    def get_step_timeout(self, step: int) -> float:
        """获取指定步骤的超时时间"""
        timeout_map = {
            1: self.step_1_timeout,
            2: self.step_2_timeout,
            3: self.step_3_timeout,
            4: self.step_4_timeout,
            5: self.step_5_timeout,
            6: self.step_6_timeout,
            7: self.step_7_timeout,
            8: self.step_8_timeout,
            9: self.step_9_timeout,
            10: self.step_10_timeout,
            11: self.step_11_timeout,
        }
        return timeout_map.get(step, 5.0)


@dataclass
class MonitoringConfig:
    """监控配置"""
    enabled: bool = True
    
    # Prometheus
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    prometheus_path: str = "/metrics"
    
    # 日志
    log_level: str = "INFO"
    log_format: str = "json"
    log_slow_queries: bool = True
    slow_query_threshold_ms: int = 1000
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_levels:
            errors.append(f"log_level 必须是 {valid_levels} 之一")
        if self.prometheus_port <= 0 or self.prometheus_port > 65535:
            errors.append("prometheus_port 必须在 1-65535 范围内")
        return errors


@dataclass
class PromptOptimizationConfig:
    """提示词优化配置"""
    max_prompt_chars: int = 32000
    max_single_cycle_bytes: int = 4000
    summarize_cycles_after: int = 1
    enable_summarization: bool = True
    log_prompt_length: bool = True
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        if self.max_prompt_chars <= 0:
            errors.append("max_prompt_chars 必须大于 0")
        return errors


@dataclass
class RuntimeConfig:
    """
    运行时配置
    
    整合所有运行时配置，支持：
    - 从 YAML 文件加载
    - 环境变量覆盖
    - 配置验证
    """
    # 子配置
    cache: CacheConfig = field(default_factory=CacheConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    concurrency: ConcurrencyConfig = field(default_factory=ConcurrencyConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    prompt_optimization: PromptOptimizationConfig = field(default_factory=PromptOptimizationConfig)
    
    # 环境
    environment: str = "development"
    
    def validate(self) -> bool:
        """
        验证所有配置
        
        Returns:
            验证是否通过
            
        Raises:
            ConfigValidationError: 配置验证失败
        """
        all_errors = []
        
        # 验证各子配置
        all_errors.extend(self.cache.validate())
        all_errors.extend(self.connection_pool.validate())
        all_errors.extend(self.llm.validate())
        all_errors.extend(self.concurrency.validate())
        all_errors.extend(self.workflow.validate())
        all_errors.extend(self.monitoring.validate())
        all_errors.extend(self.prompt_optimization.validate())
        
        if all_errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"  - {e}" for e in all_errors)
            logger.error(error_msg)
            raise ConfigValidationError(error_msg)
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_yaml(
        cls,
        path: str = "config/performance_optimization.yaml"
    ) -> "RuntimeConfig":
        """
        从 YAML 文件加载配置
        
        Args:
            path: YAML 配置文件路径
            
        Returns:
            RuntimeConfig 实例
        """
        config = cls()
        
        # 尝试多个可能的路径
        possible_paths = [
            Path(path),
            Path("daml-rag-server") / path,
            Path(__file__).parent.parent.parent.parent.parent / "config" / "performance_optimization.yaml",
        ]
        
        config_path = None
        for p in possible_paths:
            if p.exists():
                config_path = p
                break
        
        if config_path is None:
            logger.warning(f"配置文件不存在: {path}，使用默认配置")
            return config
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
            
            if yaml_config:
                config._load_from_dict(yaml_config)
            
            logger.info(f"✅ 运行时配置加载成功: {config_path}")
            
        except Exception as e:
            logger.error(f"加载运行时配置失败: {e}，使用默认配置")
        
        # 应用环境变量覆盖
        config._apply_env_overrides()
        
        return config
    
    def _load_from_dict(self, config: Dict[str, Any]):
        """从字典加载配置"""
        # 缓存配置
        cache_config = config.get("cache", {})
        if cache_config:
            self.cache.l1_enabled = cache_config.get("l1_enabled", self.cache.l1_enabled)
            self.cache.l1_max_size = cache_config.get("l1_max_size", self.cache.l1_max_size)
            self.cache.l2_enabled = cache_config.get("l2_enabled", self.cache.l2_enabled)
            self.cache.l2_host = cache_config.get("l2_host", self.cache.l2_host)
            self.cache.l2_port = cache_config.get("l2_port", self.cache.l2_port)
            self.cache.default_ttl = cache_config.get("default_ttl", self.cache.default_ttl)
        
        # 连接池配置
        pool_config = config.get("connection_pool", {})
        if pool_config:
            mysql = pool_config.get("mysql", {})
            self.connection_pool.mysql_min_size = mysql.get("min_size", self.connection_pool.mysql_min_size)
            self.connection_pool.mysql_max_size = mysql.get("max_size", self.connection_pool.mysql_max_size)
            
            neo4j = pool_config.get("neo4j", {})
            self.connection_pool.neo4j_min_size = neo4j.get("min_size", self.connection_pool.neo4j_min_size)
            self.connection_pool.neo4j_max_size = neo4j.get("max_size", self.connection_pool.neo4j_max_size)
            
            http = pool_config.get("http", {})
            self.connection_pool.http_min_size = http.get("min_size", self.connection_pool.http_min_size)
            self.connection_pool.http_max_size = http.get("max_size", self.connection_pool.http_max_size)
        
        # LLM 配置
        llm_config = config.get("llm_fallback", {})
        if llm_config:
            self.llm.primary_backend = llm_config.get("primary_backend", self.llm.primary_backend)
            self.llm.fallback_backends = llm_config.get("fallback_backends", self.llm.fallback_backends)
            self.llm.max_retries = llm_config.get("max_retries", self.llm.max_retries)
            self.llm.timeout = llm_config.get("timeout", self.llm.timeout)
            
            streaming = llm_config.get("streaming", {})
            self.llm.streaming_enabled = streaming.get("enabled", self.llm.streaming_enabled)
            self.llm.streaming_chunk_size = streaming.get("chunk_size", self.llm.streaming_chunk_size)
        
        # 并发配置
        concurrency_config = config.get("concurrency", {})
        if concurrency_config:
            self.concurrency.max_concurrent = concurrency_config.get("max_concurrent", self.concurrency.max_concurrent)
            self.concurrency.max_queue_size = concurrency_config.get("max_queue_size", self.concurrency.max_queue_size)
            self.concurrency.timeout = concurrency_config.get("timeout", self.concurrency.timeout)
            
            user_limits = concurrency_config.get("user_limits", {})
            if "free" in user_limits:
                self.concurrency.free_max_concurrent = user_limits["free"].get("max_concurrent", self.concurrency.free_max_concurrent)
            if "paid" in user_limits:
                self.concurrency.paid_max_concurrent = user_limits["paid"].get("max_concurrent", self.concurrency.paid_max_concurrent)
            if "vip" in user_limits:
                self.concurrency.vip_max_concurrent = user_limits["vip"].get("max_concurrent", self.concurrency.vip_max_concurrent)
        
        # 工作流配置
        workflow_config = config.get("workflow", {})
        if workflow_config:
            self.workflow.global_timeout = workflow_config.get("global_timeout", self.workflow.global_timeout)
            
            step_timeouts = workflow_config.get("step_timeouts", {})
            if step_timeouts:
                self.workflow.step_1_timeout = step_timeouts.get("step_1_user_profile", self.workflow.step_1_timeout)
                self.workflow.step_2_timeout = step_timeouts.get("step_2_session_init", self.workflow.step_2_timeout)
                self.workflow.step_3_timeout = step_timeouts.get("step_3_membership", self.workflow.step_3_timeout)
                self.workflow.step_4_timeout = step_timeouts.get("step_4_bge_classification", self.workflow.step_4_timeout)
                self.workflow.step_5_timeout = step_timeouts.get("step_5_model_selection", self.workflow.step_5_timeout)
                self.workflow.step_6_timeout = step_timeouts.get("step_6_few_shot", self.workflow.step_6_timeout)
                self.workflow.step_7_timeout = step_timeouts.get("step_7_dag_orchestration", self.workflow.step_7_timeout)
                self.workflow.step_8_timeout = step_timeouts.get("step_8_retrieval", self.workflow.step_8_timeout)
                self.workflow.step_9_timeout = step_timeouts.get("step_9_tool_summary", self.workflow.step_9_timeout)
                self.workflow.step_10_timeout = step_timeouts.get("step_10_llm_analysis", self.workflow.step_10_timeout)
                self.workflow.step_11_timeout = step_timeouts.get("step_11_record", self.workflow.step_11_timeout)
            
            parallel = workflow_config.get("parallel_execution", {})
            if parallel:
                self.workflow.parallel_step_1_2 = parallel.get("step_1_2_parallel", self.workflow.parallel_step_1_2)
                self.workflow.parallel_step_3_4 = parallel.get("step_3_4_parallel", self.workflow.parallel_step_3_4)
                self.workflow.max_parallel_workers = parallel.get("max_parallel_workers", self.workflow.max_parallel_workers)
        
        # 监控配置
        monitoring_config = config.get("monitoring", {})
        if monitoring_config:
            self.monitoring.enabled = monitoring_config.get("enabled", self.monitoring.enabled)
            
            prometheus = monitoring_config.get("prometheus", {})
            if prometheus:
                self.monitoring.prometheus_enabled = prometheus.get("enabled", self.monitoring.prometheus_enabled)
                self.monitoring.prometheus_port = prometheus.get("port", self.monitoring.prometheus_port)
                self.monitoring.prometheus_path = prometheus.get("path", self.monitoring.prometheus_path)
            
            logging_config = monitoring_config.get("logging", {})
            if logging_config:
                self.monitoring.log_level = logging_config.get("level", self.monitoring.log_level)
                self.monitoring.log_format = logging_config.get("format", self.monitoring.log_format)
                
                perf_log = logging_config.get("performance_log", {})
                if perf_log:
                    self.monitoring.log_slow_queries = perf_log.get("log_slow_queries", self.monitoring.log_slow_queries)
                    self.monitoring.slow_query_threshold_ms = perf_log.get("slow_query_threshold_ms", self.monitoring.slow_query_threshold_ms)
        
        # 提示词优化配置
        prompt_config = config.get("prompt_optimization", {})
        if prompt_config:
            self.prompt_optimization.max_prompt_chars = prompt_config.get("max_prompt_chars", self.prompt_optimization.max_prompt_chars)
            self.prompt_optimization.max_single_cycle_bytes = prompt_config.get("max_single_cycle_bytes", self.prompt_optimization.max_single_cycle_bytes)
            self.prompt_optimization.summarize_cycles_after = prompt_config.get("summarize_cycles_after", self.prompt_optimization.summarize_cycles_after)
            self.prompt_optimization.enable_summarization = prompt_config.get("enable_summarization", self.prompt_optimization.enable_summarization)
            self.prompt_optimization.log_prompt_length = prompt_config.get("log_prompt_length", self.prompt_optimization.log_prompt_length)
    
    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        # 环境
        self.environment = os.getenv("ENVIRONMENT", self.environment)
        
        # 缓存
        if os.getenv("CACHE_L1_ENABLED"):
            self.cache.l1_enabled = os.getenv("CACHE_L1_ENABLED", "").lower() == "true"
        if os.getenv("CACHE_L2_ENABLED"):
            self.cache.l2_enabled = os.getenv("CACHE_L2_ENABLED", "").lower() == "true"
        if os.getenv("REDIS_HOST"):
            self.cache.l2_host = os.getenv("REDIS_HOST", self.cache.l2_host)
        if os.getenv("REDIS_PORT"):
            self.cache.l2_port = int(os.getenv("REDIS_PORT", str(self.cache.l2_port)))
        if os.getenv("REDIS_PASSWORD"):
            self.cache.l2_password = os.getenv("REDIS_PASSWORD")
        
        # LLM
        if os.getenv("LLM_PRIMARY_BACKEND"):
            self.llm.primary_backend = os.getenv("LLM_PRIMARY_BACKEND", self.llm.primary_backend)
        if os.getenv("LLM_TIMEOUT"):
            self.llm.timeout = int(os.getenv("LLM_TIMEOUT", str(self.llm.timeout)))
        if os.getenv("LLM_MAX_RETRIES"):
            self.llm.max_retries = int(os.getenv("LLM_MAX_RETRIES", str(self.llm.max_retries)))
        
        # 并发
        if os.getenv("MAX_CONCURRENT"):
            self.concurrency.max_concurrent = int(os.getenv("MAX_CONCURRENT", str(self.concurrency.max_concurrent)))
        
        # 工作流
        if os.getenv("WORKFLOW_TIMEOUT"):
            self.workflow.global_timeout = int(os.getenv("WORKFLOW_TIMEOUT", str(self.workflow.global_timeout)))
        
        # 监控
        if os.getenv("MONITORING_ENABLED"):
            self.monitoring.enabled = os.getenv("MONITORING_ENABLED", "").lower() == "true"
        if os.getenv("LOG_LEVEL"):
            self.monitoring.log_level = os.getenv("LOG_LEVEL", self.monitoring.log_level)
        
        # 提示词优化
        if os.getenv("MAX_PROMPT_CHARS"):
            self.prompt_optimization.max_prompt_chars = int(os.getenv("MAX_PROMPT_CHARS", str(self.prompt_optimization.max_prompt_chars)))


class RuntimeConfigManager:
    """
    运行时配置管理器
    
    提供配置的单例管理和动态刷新功能
    """
    
    _instance: Optional["RuntimeConfigManager"] = None
    _lock = threading.Lock()
    
    DEFAULT_CONFIG_PATH = "config/performance_optimization.yaml"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: YAML 配置文件路径
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config: RuntimeConfig = RuntimeConfig.from_yaml(self.config_path)
        self._last_modified: float = 0
        
        # 验证配置
        try:
            self.config.validate()
        except ConfigValidationError as e:
            logger.warning(f"配置验证失败，使用默认值: {e}")
    
    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> "RuntimeConfigManager":
        """
        获取单例实例
        
        Args:
            config_path: YAML 配置文件路径（仅首次调用时有效）
            
        Returns:
            RuntimeConfigManager 单例实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config_path)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例实例（主要用于测试）"""
        with cls._lock:
            cls._instance = None
    
    def reload(self):
        """重新加载配置"""
        self.config = RuntimeConfig.from_yaml(self.config_path)
        try:
            self.config.validate()
            logger.info("✅ 运行时配置已重新加载")
        except ConfigValidationError as e:
            logger.warning(f"配置验证失败: {e}")
    
    def get_config(self) -> RuntimeConfig:
        """获取当前配置"""
        return self.config
    
    def get_cache_config(self) -> CacheConfig:
        """获取缓存配置"""
        return self.config.cache
    
    def get_llm_config(self) -> LLMConfig:
        """获取 LLM 配置"""
        return self.config.llm
    
    def get_workflow_config(self) -> WorkflowConfig:
        """获取工作流配置"""
        return self.config.workflow
    
    def get_concurrency_config(self) -> ConcurrencyConfig:
        """获取并发配置"""
        return self.config.concurrency
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """获取监控配置"""
        return self.config.monitoring


# ============================================================================
# 便捷函数
# ============================================================================

def get_runtime_config() -> RuntimeConfig:
    """
    获取运行时配置
    
    Returns:
        RuntimeConfig 实例
    """
    manager = RuntimeConfigManager.get_instance()
    return manager.get_config()


def get_runtime_config_manager(config_path: Optional[str] = None) -> RuntimeConfigManager:
    """
    获取运行时配置管理器
    
    Args:
        config_path: YAML 配置文件路径
        
    Returns:
        RuntimeConfigManager 实例
    """
    return RuntimeConfigManager.get_instance(config_path)


def reload_runtime_config():
    """重新加载运行时配置"""
    manager = RuntimeConfigManager.get_instance()
    manager.reload()
