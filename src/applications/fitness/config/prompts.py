"""
提示词配置管理模块

提供提示词的统一管理，支持：
- 从 YAML 配置文件加载提示词模板
- 热加载（配置文件修改后自动重新加载）
- 变量替换
- 提示词调试模式
- 默认模板回退

版本: v1.0.0
日期: 2025-12-28

Requirements: 6.1, 6.2, 6.3
"""

import os
import yaml
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """提示词模板数据类"""
    template_id: str
    prompt_template: str
    max_tokens: int = 2000
    temperature: float = 0.7
    stream: bool = False
    response_style: str = "balanced"
    tone: str = "professional"
    length_constraint: str = "适中"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "template_id": self.template_id,
            "prompt_template": self.prompt_template,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": self.stream,
            "response_style": self.response_style,
            "tone": self.tone,
            "length_constraint": self.length_constraint,
        }


class PromptConfigManager:
    """
    提示词配置管理器
    
    提供统一的提示词管理，支持：
    - 从 YAML 配置文件加载提示词模板
    - 热加载（配置文件修改后自动重新加载）
    - 变量替换
    - 提示词调试模式
    - 默认模板回退
    
    使用示例:
        manager = PromptConfigManager.get_instance()
        prompt = manager.get_prompt("complete_training_plan", query="制定训练计划")
        config = manager.get_config("complete_training_plan")
    """
    
    _instance: Optional["PromptConfigManager"] = None
    _lock = threading.Lock()
    
    # 默认配置文件路径
    DEFAULT_CONFIG_PATH = "config/llm_response_config.yaml"
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        enable_hot_reload: bool = True,
        debug_mode: bool = False
    ):
        """
        初始化提示词配置管理器
        
        Args:
            config_path: YAML配置文件路径（可选，默认使用 DEFAULT_CONFIG_PATH）
            enable_hot_reload: 是否启用热加载
            debug_mode: 是否启用调试模式（记录完整提示词到日志）
        """
        self.config_path = self._resolve_config_path(config_path)
        self.enable_hot_reload = enable_hot_reload
        self.debug_mode = debug_mode
        
        # 配置数据
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.default_template: Dict[str, Any] = {}
        self.streaming_config: Dict[str, Any] = {}
        
        # 热加载相关
        self._last_modified: float = 0
        self._hot_reload_thread: Optional[threading.Thread] = None
        self._stop_hot_reload = threading.Event()
        self._reload_callbacks: List[Callable[[], None]] = []
        
        # 加载配置
        self._load_config()
        
        # 启动热加载
        if enable_hot_reload:
            self._start_hot_reload()
    
    def _resolve_config_path(self, config_path: Optional[str]) -> Path:
        """
        解析配置文件路径
        
        Args:
            config_path: 用户提供的路径
            
        Returns:
            解析后的 Path 对象
        """
        if config_path:
            path = Path(config_path)
        else:
            # 尝试多个可能的路径
            possible_paths = [
                Path(self.DEFAULT_CONFIG_PATH),
                Path("daml-rag-server") / self.DEFAULT_CONFIG_PATH,
                Path(__file__).parent.parent.parent.parent.parent / "config" / "llm_response_config.yaml",
            ]
            
            for p in possible_paths:
                if p.exists():
                    path = p
                    break
            else:
                path = Path(self.DEFAULT_CONFIG_PATH)
        
        return path
    
    @classmethod
    def get_instance(
        cls,
        config_path: Optional[str] = None,
        enable_hot_reload: bool = True,
        debug_mode: bool = False
    ) -> "PromptConfigManager":
        """
        获取单例实例
        
        Args:
            config_path: YAML配置文件路径（仅首次调用时有效）
            enable_hot_reload: 是否启用热加载
            debug_mode: 是否启用调试模式
            
        Returns:
            PromptConfigManager 单例实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config_path, enable_hot_reload, debug_mode)
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例实例（主要用于测试）"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.stop_hot_reload()
                cls._instance = None
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if not self.config_path.exists():
                logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
                self._load_default_config()
                return
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                logger.warning("配置文件为空，使用默认配置")
                self._load_default_config()
                return
            
            # 加载模板配置
            self.templates = config.get("templates", {})
            self.default_template = config.get("default", self._get_default_template())
            self.streaming_config = config.get("streaming", {})
            
            # 记录最后修改时间
            self._last_modified = self.config_path.stat().st_mtime
            
            logger.info(f"✅ 提示词配置加载成功: {len(self.templates)} 个模板")
            
        except Exception as e:
            logger.error(f"加载提示词配置失败: {e}")
            self._load_default_config()
    
    def _load_default_config(self):
        """加载默认配置"""
        self.default_template = self._get_default_template()
        self.templates = {}
        self.streaming_config = {
            "enabled": True,
            "max_tokens": 8000,
            "timeout": 180.0,
        }
    
    def _get_default_template(self) -> Dict[str, Any]:
        """获取默认模板配置"""
        return {
            "max_tokens": 2000,
            "temperature": 0.7,
            "stream": False,
            "response_style": "balanced",
            "tone": "professional",
            "length_constraint": "适中",
            "prompt_template": """你是玉珍健身专业教练，擅长基于真实数据进行深度分析和个性化指导。

用户查询: {query}

用户档案: {user_profile}

请提供专业的分析和建议。"""
        }
    
    def _start_hot_reload(self):
        """启动热加载监控线程"""
        if self._hot_reload_thread is not None:
            return
        
        self._stop_hot_reload.clear()
        self._hot_reload_thread = threading.Thread(
            target=self._hot_reload_loop,
            daemon=True,
            name="PromptConfigHotReload"
        )
        self._hot_reload_thread.start()
        logger.debug("提示词配置热加载已启动")
    
    def _hot_reload_loop(self):
        """热加载监控循环"""
        check_interval = 5  # 每5秒检查一次
        
        while not self._stop_hot_reload.is_set():
            try:
                if self.config_path.exists():
                    current_mtime = self.config_path.stat().st_mtime
                    if current_mtime > self._last_modified:
                        logger.info("检测到配置文件变更，重新加载...")
                        self._load_config()
                        self._notify_reload_callbacks()
            except Exception as e:
                logger.error(f"热加载检查失败: {e}")
            
            self._stop_hot_reload.wait(check_interval)
    
    def stop_hot_reload(self):
        """停止热加载"""
        if self._hot_reload_thread is not None:
            self._stop_hot_reload.set()
            self._hot_reload_thread.join(timeout=2)
            self._hot_reload_thread = None
            logger.debug("提示词配置热加载已停止")
    
    def register_reload_callback(self, callback: Callable[[], None]):
        """
        注册配置重新加载回调
        
        Args:
            callback: 配置重新加载时调用的函数
        """
        self._reload_callbacks.append(callback)
    
    def _notify_reload_callbacks(self):
        """通知所有注册的回调"""
        for callback in self._reload_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"执行重新加载回调失败: {e}")
    
    def reload(self):
        """手动重新加载配置"""
        self._load_config()
        self._notify_reload_callbacks()
        logger.info("✅ 提示词配置已手动重新加载")
    
    def get_prompt(
        self,
        template_id: str,
        **variables
    ) -> str:
        """
        获取提示词（支持变量替换）
        
        Args:
            template_id: 模板ID
            **variables: 变量替换参数
            
        Returns:
            替换变量后的提示词
        """
        template = self.templates.get(template_id, self.default_template)
        prompt_template = template.get("prompt_template", "")
        
        if not prompt_template:
            prompt_template = self.default_template.get("prompt_template", "")
        
        # 变量替换
        prompt = self._replace_variables(prompt_template, variables)
        
        # 调试模式：记录完整提示词
        if self.debug_mode:
            logger.debug(f"[提示词调试] 模板: {template_id}")
            logger.debug(f"[提示词调试] 变量: {list(variables.keys())}")
            logger.debug(f"[提示词调试] 完整提示词:\n{prompt[:500]}...")
        
        return prompt
    
    def _replace_variables(
        self,
        template: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        替换模板中的变量
        
        支持两种格式：
        - {variable_name}: 标准格式
        - {{variable_name}}: 双括号格式（用于嵌套模板）
        
        Args:
            template: 模板字符串
            variables: 变量字典
            
        Returns:
            替换后的字符串
        """
        result = template
        
        for key, value in variables.items():
            # 处理不同类型的值
            if value is None:
                str_value = "无"
            elif isinstance(value, dict):
                str_value = self._format_dict(value)
            elif isinstance(value, list):
                str_value = self._format_list(value)
            else:
                str_value = str(value)
            
            # 替换 {key} 格式
            result = result.replace(f"{{{key}}}", str_value)
            
            # 替换 {{key}} 格式（双括号）
            result = result.replace(f"{{{{{key}}}}}", str_value)
        
        return result
    
    def _format_dict(self, d: Dict[str, Any], indent: int = 0) -> str:
        """格式化字典为可读字符串"""
        if not d:
            return "无"
        
        lines = []
        prefix = "  " * indent
        for key, value in d.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._format_dict(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}: {self._format_list(value)}")
            else:
                lines.append(f"{prefix}{key}: {value}")
        
        return "\n".join(lines)
    
    def _format_list(self, lst: List[Any]) -> str:
        """格式化列表为可读字符串"""
        if not lst:
            return "无"
        
        if len(lst) <= 5:
            return ", ".join(str(item) for item in lst)
        else:
            return ", ".join(str(item) for item in lst[:5]) + f"... (共{len(lst)}项)"
    
    def get_config(self, template_id: str) -> Dict[str, Any]:
        """
        获取模板完整配置
        
        Args:
            template_id: 模板ID
            
        Returns:
            模板配置字典
        """
        template = self.templates.get(template_id, self.default_template)
        
        # 合并默认配置
        config = self.default_template.copy()
        config.update(template)
        config["template_id"] = template_id
        
        return config
    
    def get_max_tokens(self, template_id: str) -> int:
        """
        获取模板的最大token数
        
        Args:
            template_id: 模板ID
            
        Returns:
            最大token数
        """
        config = self.get_config(template_id)
        return config.get("max_tokens", 2000)
    
    def get_temperature(self, template_id: str) -> float:
        """
        获取模板的温度参数
        
        Args:
            template_id: 模板ID
            
        Returns:
            温度参数
        """
        config = self.get_config(template_id)
        return config.get("temperature", 0.7)
    
    def is_streaming_enabled(self, template_id: str) -> bool:
        """
        检查模板是否启用流式输出
        
        Args:
            template_id: 模板ID
            
        Returns:
            是否启用流式输出
        """
        config = self.get_config(template_id)
        return config.get("stream", False)
    
    def get_streaming_config(self) -> Dict[str, Any]:
        """
        获取流式输出全局配置
        
        Returns:
            流式输出配置字典
        """
        return self.streaming_config.copy()
    
    def get_response_hint(self, template_id: str) -> str:
        """
        获取响应提示（基于模板配置生成）
        
        Args:
            template_id: 模板ID
            
        Returns:
            响应提示字符串
        """
        config = self.get_config(template_id)
        
        hints = []
        
        # 响应风格
        style = config.get("response_style", "balanced")
        style_hints = {
            "concise": "简洁明了",
            "comprehensive": "全面详细",
            "detailed": "详细说明",
            "analytical": "数据驱动分析",
            "balanced": "平衡适中",
        }
        hints.append(f"风格: {style_hints.get(style, style)}")
        
        # 语气
        tone = config.get("tone", "professional")
        tone_hints = {
            "professional": "专业严谨",
            "friendly": "友好亲切",
            "cautious": "谨慎保守",
        }
        hints.append(f"语气: {tone_hints.get(tone, tone)}")
        
        # 长度约束
        length = config.get("length_constraint", "适中")
        hints.append(f"长度: {length}")
        
        return "，".join(hints)
    
    def list_templates(self) -> List[str]:
        """
        列出所有可用的模板ID
        
        Returns:
            模板ID列表
        """
        return list(self.templates.keys())
    
    def has_template(self, template_id: str) -> bool:
        """
        检查模板是否存在
        
        Args:
            template_id: 模板ID
            
        Returns:
            模板是否存在
        """
        return template_id in self.templates
    
    def set_debug_mode(self, enabled: bool):
        """
        设置调试模式
        
        Args:
            enabled: 是否启用调试模式
        """
        self.debug_mode = enabled
        logger.info(f"提示词调试模式: {'启用' if enabled else '禁用'}")
    
    def get_structured_data_markers(self) -> Dict[str, str]:
        """
        获取结构化数据标记配置
        
        Returns:
            结构化数据标记字典
        """
        return self.streaming_config.get("structured_data_markers", {})
    
    def get_structured_data_instruction(self) -> str:
        """
        获取结构化数据嵌入说明
        
        Returns:
            结构化数据嵌入说明字符串
        """
        return self.streaming_config.get("structured_data_instruction", "")


# ============================================================================
# 便捷函数
# ============================================================================

def get_prompt_config_manager(
    config_path: Optional[str] = None,
    enable_hot_reload: bool = True,
    debug_mode: bool = False
) -> PromptConfigManager:
    """
    获取提示词配置管理器实例
    
    Args:
        config_path: YAML配置文件路径（可选）
        enable_hot_reload: 是否启用热加载
        debug_mode: 是否启用调试模式
        
    Returns:
        PromptConfigManager 实例
    """
    return PromptConfigManager.get_instance(config_path, enable_hot_reload, debug_mode)


def get_prompt(template_id: str, **variables) -> str:
    """
    便捷函数：获取提示词
    
    Args:
        template_id: 模板ID
        **variables: 变量替换参数
        
    Returns:
        替换变量后的提示词
    """
    manager = PromptConfigManager.get_instance()
    return manager.get_prompt(template_id, **variables)


def get_prompt_config(template_id: str) -> Dict[str, Any]:
    """
    便捷函数：获取模板配置
    
    Args:
        template_id: 模板ID
        
    Returns:
        模板配置字典
    """
    manager = PromptConfigManager.get_instance()
    return manager.get_config(template_id)
