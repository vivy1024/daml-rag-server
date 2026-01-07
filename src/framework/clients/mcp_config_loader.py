"""
MCP配置加载器

从配置文件加载MCP服务器配置，支持环境变量替换和配置验证。

版本: v1.0.0
日期: 2025-12-09
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

# 使用TYPE_CHECKING避免循环导入
if TYPE_CHECKING:
    from .mcp_client_v2 import MCPProtocol, MCPServerConfig
else:
    # 运行时导入
    MCPProtocol = None
    MCPServerConfig = None

class ConfigStatus(Enum):
    """配置状态"""
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"

@dataclass
class ConfigValidationResult:
    """配置验证结果"""
    status: ConfigStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

class MCPConfigLoader:
    """
    MCP配置加载器

    负责从配置文件加载MCP服务器配置，支持：
    1. JSON配置文件读取
    2. 环境变量替换
    3. 配置验证
    4. 动态配置更新
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置加载器

        Args:
            config_path: 配置文件路径，默认使用项目根目录的config/mcp_registry.json
        """
        if config_path is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "mcp_registry.json"

        self.config_path = Path(config_path)
        self.config_data: Dict[str, Any] = {}
        self.loaded_servers: Dict[str, MCPServerConfig] = {}

    def load_config(self) -> Dict[str, "MCPServerConfig"]:
        """
        加载MCP配置

        Returns:
            Dict[str, MCPServerConfig]: 服务器配置字典
        """
        try:
            # 读取配置文件
            if not self.config_path.exists():
                raise FileNotFoundError(f"MCP配置文件不存在: {self.config_path}")

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)

            # 验证配置
            validation_result = self.validate_config()
            if validation_result.status == ConfigStatus.ERROR:
                raise ValueError(f"配置验证失败: {validation_result.message}")

            # 解析服务器配置
            self.loaded_servers = self._parse_server_configs()

            return self.loaded_servers

        except Exception as e:
            raise Exception(f"加载MCP配置失败: {str(e)}")

    def validate_config(self) -> ConfigValidationResult:
        """
        验证配置有效性

        Returns:
            ConfigValidationResult: 验证结果
        """
        try:
            # 检查必需字段
            if "version" not in self.config_data:
                return ConfigValidationResult(
                    ConfigStatus.ERROR,
                    "配置文件缺少version字段"
                )

            if "servers" not in self.config_data:
                return ConfigValidationResult(
                    ConfigStatus.ERROR,
                    "配置文件缺少servers字段"
                )

            servers = self.config_data["servers"]
            if not isinstance(servers, dict):
                return ConfigValidationResult(
                    ConfigStatus.ERROR,
                    "servers字段必须是对象类型"
                )

            # 验证每个服务器配置
            for server_name, server_config in servers.items():
                result = self._validate_server_config(server_name, server_config)
                if result.status == ConfigStatus.ERROR:
                    return result

            return ConfigValidationResult(
                ConfigStatus.VALID,
                "配置验证通过"
            )

        except Exception as e:
            return ConfigValidationResult(
                ConfigStatus.ERROR,
                f"配置验证异常: {str(e)}"
            )

    def _validate_server_config(self, server_name: str, server_config: Dict[str, Any]) -> ConfigValidationResult:
        """验证单个服务器配置"""
        # 检查必需字段
        required_fields = ["name", "version", "type", "tools"]
        for field in required_fields:
            if field not in server_config:
                return ConfigValidationResult(
                    ConfigStatus.ERROR,
                    f"服务器 {server_name} 缺少必需字段: {field}"
                )

        # 检查状态
        status = server_config.get("status", "active")
        if status == "deprecated":
            # 已废弃的服务器记录警告，但不阻止加载
            return ConfigValidationResult(
                ConfigStatus.WARNING,
                f"服务器 {server_name} 已废弃: {server_config.get('deprecation_reason', '')}",
                {"status": status}
            )

        # 验证协议类型
        server_type = server_config["type"]
        if server_type == "stdio":
            if "command" not in server_config:
                return ConfigValidationResult(
                    ConfigStatus.ERROR,
                    f"stdio类型服务器 {server_name} 缺少command字段"
                )
        elif server_type == "http":
            if "url" not in server_config:
                return ConfigValidationResult(
                    ConfigStatus.ERROR,
                    f"http类型服务器 {server_name} 缺少url字段"
                )
        else:
            return ConfigValidationResult(
                ConfigStatus.ERROR,
                f"不支持的服务器类型: {server_type}"
            )

        return ConfigValidationResult(
            ConfigStatus.VALID,
            f"服务器 {server_name} 配置有效"
        )

    def _parse_server_configs(self) -> Dict[str, "MCPServerConfig"]:
        """
        解析服务器配置

        Returns:
            Dict[str, MCPServerConfig]: 服务器配置字典
        """
        # 延迟导入避免循环依赖
        from .mcp_client_v2 import MCPProtocol, MCPServerConfig
        
        servers = {}
        servers_data = self.config_data.get("servers", {})

        for server_name, server_data in servers_data.items():
            # 跳过已废弃的服务器
            if server_data.get("status") == "deprecated":
                continue

            try:
                # 解析协议类型
                protocol_type = server_data["type"]
                if protocol_type == "stdio":
                    protocol = MCPProtocol.STDIO
                    endpoint = self._substitute_env_vars(server_data.get("command", ""))
                    args = [self._substitute_env_vars(arg) for arg in server_data.get("args", [])]
                elif protocol_type == "http":
                    protocol = MCPProtocol.HTTP
                    endpoint = self._substitute_env_vars(server_data.get("url", ""))
                    args = []
                else:
                    raise ValueError(f"不支持的协议类型: {protocol_type}")

                # 解析环境变量（支持${VAR_NAME}格式）
                env_vars = None
                if "env" in server_data:
                    env_vars = {}
                    for key, value in server_data["env"].items():
                        env_vars[key] = self._substitute_env_vars(value)

                # 创建服务器配置
                server_config = MCPServerConfig(
                    name=server_data["name"],
                    protocol=protocol,
                    endpoint=endpoint,
                    timeout=server_data.get("timeout", 30.0),
                    max_retries=server_data.get("max_retries", 3),
                    extra_args=args if args else None,
                    env=env_vars
                )

                # 添加到字典
                servers[server_name] = server_config

            except Exception as e:
                raise Exception(f"解析服务器 {server_name} 配置失败: {str(e)}")

        return servers

    def _substitute_env_vars(self, text: str) -> str:
        """
        替换环境变量

        Args:
            text: 包含环境变量的文本

        Returns:
            str: 替换后的文本
        """
        if not isinstance(text, str):
            return text

        # 替换 ${VAR_NAME} 格式的环境变量
        def replace_env_var(match):
            var_name = match.group(1)
            # 处理默认值 ${VAR_NAME:-default_value}
            if ":-" in var_name:
                var_name, default_value = var_name.split(":-", 1)
                return os.environ.get(var_name, default_value)
            else:
                return os.environ.get(var_name, match.group(0))

        # 查找 ${...} 格式的变量
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_env_var, text)

    def get_server_config(self, server_name: str) -> Optional["MCPServerConfig"]:
        """
        获取特定服务器配置

        Args:
            server_name: 服务器名称

        Returns:
            Optional[MCPServerConfig]: 服务器配置，如果不存在返回None
        """
        if not self.loaded_servers:
            self.load_config()

        return self.loaded_servers.get(server_name)

    def get_all_servers(self) -> Dict[str, "MCPServerConfig"]:
        """
        获取所有服务器配置

        Returns:
            Dict[str, MCPServerConfig]: 所有服务器配置
        """
        if not self.loaded_servers:
            self.load_config()

        return self.loaded_servers

    def get_active_servers(self) -> Dict[str, "MCPServerConfig"]:
        """
        获取活跃服务器配置（排除已废弃的）

        Returns:
            Dict[str, MCPServerConfig]: 活跃服务器配置
        """
        return self.loaded_servers

    def reload_config(self) -> Dict[str, "MCPServerConfig"]:
        """
        重新加载配置

        Returns:
            Dict[str, MCPServerConfig]: 重新加载的服务器配置
        """
        self.loaded_servers.clear()
        return self.load_config()

    def get_orchestration_config(self) -> Dict[str, Any]:
        """
        获取编排配置

        Returns:
            Dict[str, Any]: 编排配置
        """
        return self.config_data.get("orchestration_config", {})

    def get_migration_notes(self) -> Dict[str, Any]:
        """
        获取迁移说明

        Returns:
            Dict[str, Any]: 迁移说明
        """
        return self.config_data.get("migration_notes", {})


# 便捷函数
def load_mcp_config(config_path: Optional[str] = None) -> Dict[str, "MCPServerConfig"]:
    """
    加载MCP配置的便捷函数

    Args:
        config_path: 配置文件路径

    Returns:
        Dict[str, MCPServerConfig]: 服务器配置字典
    """
    loader = MCPConfigLoader(config_path)
    return loader.load_config()


def create_mcp_client_with_config() -> Dict[str, "MCPServerConfig"]:
    """
    使用配置文件创建MCP客户端配置

    Returns:
        Dict[str, MCPServerConfig]: MCP服务器配置
    """
    return load_mcp_config()


# 使用示例
if __name__ == "__main__":
    # 加载配置
    try:
        servers = load_mcp_config()
        print(f"✅ 成功加载 {len(servers)} 个MCP服务器配置:")

        for server_name, config in servers.items():
            print(f"  - {server_name}: {config.name} ({config.protocol.value})")

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
