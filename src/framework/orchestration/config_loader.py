# -*- coding: utf-8 -*-
"""
配置加载器 - Config Loader

加载和解析参数映射配置文件，支持配置验证和热重载。

核心功能：
1. 加载YAML配置文件
2. 解析配置结构
3. 验证配置完整性
4. 支持配置热重载（可选）
5. 提供配置查询接口

版本: v1.0.0
日期: 2025-12-22
"""

import logging
import os
import yaml
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ParamMappingRule:
    """参数映射规则"""
    source_task: str
    source_path: str
    target_param: str
    converter: Optional[str] = None
    converter_type: Optional[str] = None
    default_value: Optional[Any] = None
    description: Optional[str] = None


@dataclass
class ToolConfig:
    """工具配置"""
    tool_name: str
    param_mappings: List[ParamMappingRule]
    required_params: List[str]
    optional_params: List[str]


@dataclass
class RetryPolicy:
    """重试策略"""
    error_type: str
    should_retry: bool
    max_attempts: int
    delay: float = 1.0
    backoff: float = 1.0
    reason: Optional[str] = None


@dataclass
class CacheConfig:
    """缓存配置"""
    cache_type: str
    enabled: bool
    ttl: int
    key_prefix: str
    description: Optional[str] = None
    cacheable_tools: Optional[List[str]] = None
    non_cacheable_tools: Optional[List[str]] = None


class ConfigLoader:
    """
    配置加载器
    
    加载和管理参数映射配置文件。
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        self.logger = logger
        
        # 确定配置文件路径
        if config_path is None:
            # 默认路径：相对于当前文件的位置
            current_dir = Path(__file__).parent.parent.parent.parent
            config_path = current_dir / "config" / "parameter_mapping_config.yaml"
        
        self.config_path = Path(config_path)
        self.config_data: Dict[str, Any] = {}
        self.tool_configs: Dict[str, ToolConfig] = {}
        self.retry_policies: Dict[str, RetryPolicy] = {}
        self.cache_configs: Dict[str, CacheConfig] = {}
        self.converters: Dict[str, Dict[str, Dict[str, str]]] = {}
        
        # 加载配置
        self.load_config()
    
    def load_config(self) -> bool:
        """
        加载配置文件
        
        Returns:
            bool: 是否加载成功
        """
        try:
            if not self.config_path.exists():
                self.logger.error(f"❌ 配置文件不存在: {self.config_path}")
                return False
            
            self.logger.info(f"📂 加载配置文件: {self.config_path}")
            
            # 读取YAML文件
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f)
            
            # 解析配置
            self._parse_tool_configs()
            self._parse_retry_policies()
            self._parse_cache_configs()
            self._parse_converters()
            
            # 验证配置
            if self.validate_config():
                self.logger.info(f"✅ 配置加载成功: {len(self.tool_configs)} 个工具配置")
                return True
            else:
                self.logger.error("❌ 配置验证失败")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 加载配置文件失败: {e}", exc_info=True)
            return False
    
    def _parse_tool_configs(self):
        """解析工具配置"""
        tools_config = self.config_data.get('tools', {})
        
        for tool_name, tool_data in tools_config.items():
            try:
                # 解析参数映射规则
                param_mappings = []
                for mapping_data in tool_data.get('param_mappings', []):
                    mapping = ParamMappingRule(
                        source_task=mapping_data['source_task'],
                        source_path=mapping_data['source_path'],
                        target_param=mapping_data['target_param'],
                        converter=mapping_data.get('converter'),
                        converter_type=mapping_data.get('converter_type'),
                        default_value=mapping_data.get('default_value'),
                        description=mapping_data.get('description')
                    )
                    param_mappings.append(mapping)
                
                # 创建工具配置
                tool_config = ToolConfig(
                    tool_name=tool_name,
                    param_mappings=param_mappings,
                    required_params=tool_data.get('required_params', []),
                    optional_params=tool_data.get('optional_params', [])
                )
                
                self.tool_configs[tool_name] = tool_config
                self.logger.debug(f"  ✅ 解析工具配置: {tool_name} ({len(param_mappings)} 个映射规则)")
                
            except Exception as e:
                self.logger.error(f"  ❌ 解析工具配置失败: {tool_name}, 错误: {e}")
    
    def _parse_retry_policies(self):
        """解析重试策略"""
        retry_config = self.config_data.get('retry_policies', {})
        
        for error_type, policy_data in retry_config.items():
            try:
                policy = RetryPolicy(
                    error_type=error_type,
                    should_retry=policy_data.get('should_retry', False),
                    max_attempts=policy_data.get('max_attempts', 1),
                    delay=policy_data.get('delay', 1.0),
                    backoff=policy_data.get('backoff', 1.0),
                    reason=policy_data.get('reason')
                )
                
                self.retry_policies[error_type] = policy
                self.logger.debug(f"  ✅ 解析重试策略: {error_type}")
                
            except Exception as e:
                self.logger.error(f"  ❌ 解析重试策略失败: {error_type}, 错误: {e}")
    
    def _parse_cache_configs(self):
        """解析缓存配置"""
        cache_config = self.config_data.get('cache_config', {})
        
        for cache_type, cache_data in cache_config.items():
            try:
                config = CacheConfig(
                    cache_type=cache_type,
                    enabled=cache_data.get('enabled', True),
                    ttl=cache_data.get('ttl', 300),
                    key_prefix=cache_data.get('key_prefix', ''),
                    description=cache_data.get('description'),
                    cacheable_tools=cache_data.get('cacheable_tools'),
                    non_cacheable_tools=cache_data.get('non_cacheable_tools')
                )
                
                self.cache_configs[cache_type] = config
                self.logger.debug(f"  ✅ 解析缓存配置: {cache_type}")
                
            except Exception as e:
                self.logger.error(f"  ❌ 解析缓存配置失败: {cache_type}, 错误: {e}")
    
    def _parse_converters(self):
        """解析转换器配置"""
        converters_config = self.config_data.get('converters', {})
        
        for converter_name, converter_data in converters_config.items():
            try:
                self.converters[converter_name] = converter_data
                
                # 统计映射数量
                total_mappings = sum(len(mappings) for mappings in converter_data.values())
                self.logger.debug(f"  ✅ 解析转换器: {converter_name} ({total_mappings} 个映射)")
                
            except Exception as e:
                self.logger.error(f"  ❌ 解析转换器失败: {converter_name}, 错误: {e}")
    
    def validate_config(self) -> bool:
        """
        验证配置完整性
        
        Returns:
            bool: 配置是否有效
        """
        is_valid = True
        
        # 验证工具配置
        for tool_name, tool_config in self.tool_configs.items():
            # 检查必需参数是否在映射规则中
            mapped_params = {mapping.target_param for mapping in tool_config.param_mappings}
            
            for required_param in tool_config.required_params:
                if required_param not in mapped_params:
                    self.logger.warning(
                        f"⚠️ 工具 {tool_name} 的必需参数 {required_param} 没有映射规则"
                    )
            
            # 检查转换器是否存在
            for mapping in tool_config.param_mappings:
                if mapping.converter and mapping.converter_type:
                    converter = self.converters.get(mapping.converter, {})
                    if mapping.converter_type not in converter:
                        self.logger.warning(
                            f"⚠️ 工具 {tool_name} 的转换器类型 {mapping.converter_type} 不存在"
                        )
                        is_valid = False
        
        # 验证重试策略
        if 'default' not in self.retry_policies:
            self.logger.warning("⚠️ 缺少默认重试策略")
        
        return is_valid
    
    def get_tool_config(self, tool_name: str) -> Optional[ToolConfig]:
        """
        获取工具配置
        
        Args:
            tool_name: 工具名称
            
        Returns:
            ToolConfig: 工具配置，如果不存在则返回None
        """
        return self.tool_configs.get(tool_name)
    
    def get_retry_policy(self, error_type: str) -> Optional[RetryPolicy]:
        """
        获取重试策略
        
        Args:
            error_type: 错误类型
            
        Returns:
            RetryPolicy: 重试策略，如果不存在则返回默认策略
        """
        policy = self.retry_policies.get(error_type)
        if policy is None:
            policy = self.retry_policies.get('default')
        return policy
    
    def get_cache_config(self, cache_type: str) -> Optional[CacheConfig]:
        """
        获取缓存配置
        
        Args:
            cache_type: 缓存类型
            
        Returns:
            CacheConfig: 缓存配置，如果不存在则返回None
        """
        return self.cache_configs.get(cache_type)
    
    def get_converter_mapping(
        self,
        converter_name: str,
        converter_type: str
    ) -> Optional[Dict[str, str]]:
        """
        获取转换器映射表
        
        Args:
            converter_name: 转换器名称（如"chinese_to_enum"）
            converter_type: 转换器类型（如"training_goal"）
            
        Returns:
            Dict[str, str]: 映射表，如果不存在则返回None
        """
        converter = self.converters.get(converter_name, {})
        return converter.get(converter_type)
    
    def is_tool_cacheable(self, tool_name: str) -> bool:
        """
        检查工具是否可缓存
        
        Args:
            tool_name: 工具名称
            
        Returns:
            bool: 是否可缓存
        """
        mcp_cache_config = self.cache_configs.get('mcp_tool_result')
        if not mcp_cache_config or not mcp_cache_config.enabled:
            return False
        
        # 检查是否在不可缓存列表中
        if mcp_cache_config.non_cacheable_tools:
            if tool_name in mcp_cache_config.non_cacheable_tools:
                return False
        
        # 检查是否在可缓存列表中
        if mcp_cache_config.cacheable_tools:
            return tool_name in mcp_cache_config.cacheable_tools
        
        # 默认可缓存
        return True
    
    def get_validation_config(self) -> Dict[str, Any]:
        """
        获取验证配置
        
        Returns:
            Dict[str, Any]: 验证配置
        """
        return self.config_data.get('validation_config', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        获取日志配置
        
        Returns:
            Dict[str, Any]: 日志配置
        """
        return self.config_data.get('logging_config', {})
    
    def reload_config(self) -> bool:
        """
        重新加载配置文件（热重载）
        
        Returns:
            bool: 是否重载成功
        """
        self.logger.info("🔄 重新加载配置文件...")
        
        # 清空现有配置
        self.config_data = {}
        self.tool_configs = {}
        self.retry_policies = {}
        self.cache_configs = {}
        self.converters = {}
        
        # 重新加载
        return self.load_config()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要
        
        Returns:
            Dict[str, Any]: 配置摘要信息
        """
        return {
            "config_path": str(self.config_path),
            "tools_count": len(self.tool_configs),
            "retry_policies_count": len(self.retry_policies),
            "cache_configs_count": len(self.cache_configs),
            "converters_count": len(self.converters),
            "total_param_mappings": sum(
                len(config.param_mappings) for config in self.tool_configs.values()
            )
        }


# 全局配置加载器实例（单例模式）
_config_loader_instance: Optional[ConfigLoader] = None


def get_config_loader(config_path: Optional[str] = None) -> ConfigLoader:
    """
    获取配置加载器实例（单例模式）
    
    Args:
        config_path: 配置文件路径，仅在首次调用时有效
        
    Returns:
        ConfigLoader: 配置加载器实例
    """
    global _config_loader_instance
    
    if _config_loader_instance is None:
        _config_loader_instance = ConfigLoader(config_path)
    
    return _config_loader_instance


def reload_config() -> bool:
    """
    重新加载配置（热重载）
    
    Returns:
        bool: 是否重载成功
    """
    global _config_loader_instance
    
    if _config_loader_instance is None:
        logger.warning("⚠️ 配置加载器未初始化，无法重载")
        return False
    
    return _config_loader_instance.reload_config()
