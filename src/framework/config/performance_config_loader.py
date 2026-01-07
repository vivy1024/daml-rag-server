# -*- coding: utf-8 -*-
"""
性能优化配置加载器

加载和管理性能优化相关的配置。

版本: v1.0.0
日期: 2025-12-21
作者: 薛小川
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class PerformanceConfigLoader:
    """性能优化配置加载器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径（可选）
        """
        if config_path is None:
            # 默认配置文件路径
            base_dir = Path(__file__).parent.parent.parent.parent
            config_path = base_dir / "config" / "performance_optimization.yaml"
        
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        
        # 加载配置
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
                self.config = self._get_default_config()
                return
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            logger.info(f"✅ 性能优化配置加载成功: {self.config_path}")
            
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}，使用默认配置")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "cache": {
                "l1_enabled": True,
                "l1_max_size": 1000,
                "l1_max_memory_mb": 100,
                "l2_enabled": True,
                "l2_host": "localhost",
                "l2_port": 6379,
                "l2_db": 0,
                "l2_password": None,
                "default_ttl": 300,
                "warmup_enabled": True,
                "warmup_batch_size": 10,
                "stats_enabled": True
            },
            "connection_pool": {
                "mysql": {
                    "min_size": 10,
                    "max_size": 50,
                    "max_idle_time": 60,
                    "max_lifetime": 3600,
                    "acquire_timeout": 2,
                    "health_check_interval": 30
                },
                "neo4j": {
                    "min_size": 5,
                    "max_size": 20,
                    "max_idle_time": 120,
                    "max_lifetime": 3600,
                    "acquire_timeout": 2,
                    "health_check_interval": 30
                },
                "http": {
                    "min_size": 20,
                    "max_size": 100,
                    "max_idle_time": 30,
                    "max_lifetime": 1800,
                    "acquire_timeout": 2,
                    "health_check_interval": 30
                }
            },
            "llm_fallback": {
                "primary_backend": "deepseek",
                "fallback_backends": ["ollama", "template"],
                "max_retries": 3,
                "timeout": 30,
                "health_check_interval": 60
            },
            "concurrency": {
                "max_concurrent": 100,
                "max_queue_size": 200,
                "timeout": 30,
                "user_limits": {
                    "free": {
                        "max_concurrent": 10,
                        "max_queue_size": 20,
                        "timeout": 30
                    },
                    "paid": {
                        "max_concurrent": 50,
                        "max_queue_size": 100,
                        "timeout": 60
                    },
                    "vip": {
                        "max_concurrent": 100,
                        "max_queue_size": 200,
                        "timeout": 120
                    }
                }
            },
            "monitoring": {
                "enabled": True,
                "prometheus_port": 9090,
                "export_interval": 10,
                "alert_threshold_ms": 1000,
                "error_rate_threshold": 0.05,
                "cpu_threshold": 0.7,
                "memory_threshold": 0.8
            },
            "bge_classification": {
                "max_query_length": 1000,
                "cache_enabled": True,
                "cache_ttl": 1800,
                "fallback_enabled": True,
                "fallback_method": "rule_engine",
                "target_time_ms": 500
            },
            "user_profile": {
                "cache_enabled": True,
                "cache_ttl": 3600,
                "cache_level": "l2_redis",
                "timeout_ms": 500,
                "fallback_enabled": True,
                "fallback_value": {}
            },
            "membership": {
                "cache_enabled": True,
                "cache_ttl": 600,
                "cache_level": "l1_memory",
                "timeout_ms": 300,
                "fallback_enabled": True,
                "fallback_value": "free"
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键（支持点号分隔的路径，如 "cache.l1_enabled"）
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置"""
        return self.config.get("cache", {})
    
    def get_connection_pool_config(self, pool_name: str) -> Dict[str, Any]:
        """获取连接池配置"""
        return self.config.get("connection_pool", {}).get(pool_name, {})
    
    def get_llm_fallback_config(self) -> Dict[str, Any]:
        """获取LLM降级配置"""
        return self.config.get("llm_fallback", {})
    
    def get_concurrency_config(self) -> Dict[str, Any]:
        """获取并发限流配置"""
        return self.config.get("concurrency", {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """获取监控配置"""
        return self.config.get("monitoring", {})
    
    def get_bge_config(self) -> Dict[str, Any]:
        """获取BGE分类配置"""
        return self.config.get("bge_classification", {})
    
    def get_user_profile_config(self) -> Dict[str, Any]:
        """获取用户档案配置"""
        return self.config.get("user_profile", {})
    
    def get_membership_config(self) -> Dict[str, Any]:
        """获取会员权限配置"""
        return self.config.get("membership", {})
    
    def reload(self):
        """重新加载配置"""
        self._load_config()
        logger.info("配置已重新加载")


# 全局配置实例
_config_loader: Optional[PerformanceConfigLoader] = None


def get_performance_config() -> PerformanceConfigLoader:
    """获取全局配置实例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = PerformanceConfigLoader()
    return _config_loader


# 导出
__all__ = [
    "PerformanceConfigLoader",
    "get_performance_config"
]
