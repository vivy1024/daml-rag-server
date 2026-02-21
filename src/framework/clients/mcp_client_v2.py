"""
MCP客户端 v2.0

基于配置文件的MCP客户端，支持从配置文件动态加载服务器配置，
替代硬编码方式。

主要特性:
1. 动态配置加载 - 从JSON配置文件读取
2. 环境变量替换 - 支持 ${VAR_NAME} 和 ${VAR_NAME:-default} 格式
3. 配置验证 - 启动时验证配置有效性
4. 自动重载 - 支持热重载配置
5. 优雅降级 - 配置失败时提供备用方案

版本: v2.0.0
日期: 2025-12-09
"""

import asyncio
import json
import subprocess
import logging
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .base_client import BaseClient, ClientConfig, ClientStatus
from .mcp_config_loader import MCPConfigLoader, ConfigStatus

logger = logging.getLogger(__name__)

class MCPProtocol(Enum):
    """MCP协议类型"""
    STDIO = "stdio"
    HTTP = "http"


@dataclass
class MCPServerConfig:
    """MCP服务器配置"""
    name: str
    protocol: MCPProtocol
    endpoint: str  # 对于stdio是路径，对于http是URL
    timeout: float = 30.0
    max_retries: int = 3
    extra_args: Optional[list] = None
    env: Optional[Dict[str, str]] = None


@dataclass
class MCPClientConfig(ClientConfig):
    """MCP客户端配置"""
    config_path: Optional[str] = None
    auto_reload: bool = False
    fallback_servers: Dict[str, MCPServerConfig] = None

    def __post_init__(self):
        if self.fallback_servers is None:
            self.fallback_servers = {}


class ConfigurableMCPClient(BaseClient):
    """
    可配置的MCP客户端 v2.0

    支持从配置文件动态加载MCP服务器配置，
    提供更好的灵活性和可维护性。

    主要特性:
    1. 配置文件驱动 - 替代硬编码
    2. 环境变量支持 - ${VAR_NAME} 格式
    3. 配置验证 - 确保配置有效性
    4. 优雅降级 - 配置失败时的备用方案
    5. 热重载 - 支持动态配置更新
    """

    def __init__(self, config: Optional[MCPClientConfig] = None):
        """
        初始化可配置MCP客户端

        Args:
            config: MCP客户端配置
        """
        self.mcp_config = config or MCPClientConfig()
        super().__init__(self.mcp_config)

        # 配置加载器
        self.config_loader = MCPConfigLoader(self.mcp_config.config_path)

        # 服务器配置
        self.servers: Dict[str, MCPServerConfig] = {}
        self.config_load_status = False

        # 加载配置
        self._load_configuration()

    def _load_configuration(self):
        """加载MCP配置"""
        try:
            # 尝试从配置文件加载
            self.servers = self.config_loader.load_config()
            self.config_load_status = True

            self.logger.info(
                f"✅ 从配置文件加载MCP配置成功，"
                f"发现 {len(self.servers)} 个服务器"
            )

            # 记录服务器信息
            for server_name, server_config in self.servers.items():
                self.logger.info(
                    f"  📋 服务器: {server_name} - "
                    f"{server_config.name} ({server_config.protocol.value})"
                )

        except Exception as e:
            self.logger.warning(
                f"⚠️ 配置文件加载失败: {str(e)}，使用备用配置"
            )

            # 使用备用配置
            self.servers = self._get_fallback_servers()
            self.config_load_status = False

            self.logger.info(
                f"✅ 使用备用配置，加载 {len(self.servers)} 个服务器"
            )

    def _get_fallback_servers(self) -> Dict[str, MCPServerConfig]:
        """
        获取备用服务器配置

        Returns:
            Dict[str, MCPServerConfig]: 备用服务器配置
        """
        # 使用配置中的备用服务器，如果没有则返回空字典
        # 移除硬编码路径，完全依赖配置文件
        if self.mcp_config.fallback_servers:
            return self.mcp_config.fallback_servers.copy()
        
        # 如果没有配置备用服务器，返回空字典
        # 这样可以强制用户正确配置mcp_registry.json
        self.logger.warning(
            "⚠️ 没有配置备用服务器，请确保mcp_registry.json配置正确"
        )
        return {}

    async def connect(self) -> bool:
        """
        建立MCP连接

        Returns:
            bool: 连接是否成功
        """
        try:
            self.status = ClientStatus.CONNECTING

            # 验证服务器配置
            validation_result = self.config_loader.validate_config()
            if validation_result.status == ConfigStatus.ERROR:
                self.logger.warning(f"⚠️ 配置验证失败: {validation_result.message}")
            elif validation_result.status == ConfigStatus.WARNING:
                self.logger.warning(f"⚠️ 配置警告: {validation_result.message}")

            # 检查服务器配置有效性
            valid_servers = 0
            for server_name, server_config in self.servers.items():
                if await self._check_server_connectivity(server_config):
                    valid_servers += 1
                    self.logger.info(f"✅ 服务器 {server_name} 配置有效")
                else:
                    self.logger.warning(f"⚠️ 服务器 {server_name} 配置无效")

            if valid_servers == 0:
                self.status = ClientStatus.ERROR
                self.logger.error("❌ 没有有效的MCP服务器配置")
                return False

            self.status = ClientStatus.CONNECTED
            self.logger.info(
                f"✅ MCP客户端已连接，"
                f"{valid_servers}/{len(self.servers)} 个服务器配置有效"
            )
            return True

        except Exception as e:
            self.status = ClientStatus.ERROR
            self.logger.error(f"❌ MCP客户端连接失败: {str(e)}")
            return False

    async def _check_server_connectivity(self, server_config: MCPServerConfig) -> bool:
        """
        检查服务器连接性

        Args:
            server_config: 服务器配置

        Returns:
            bool: 服务器是否可用
        """
        try:
            if server_config.protocol == MCPProtocol.STDIO:
                # 对于stdio服务器，检查脚本文件是否存在
                # endpoint是命令（如"node"），extra_args包含脚本路径
                if server_config.extra_args and len(server_config.extra_args) > 0:
                    script_path = server_config.extra_args[0]
                    script_file = Path(script_path)
                    
                    if not script_file.exists():
                        self.logger.warning(
                            f"⚠️ MCP服务器脚本不存在: {script_path}\n"
                            f"   请确保MCP服务已正确构建"
                        )
                        return False
                    
                    self.logger.info(f"✅ 脚本文件存在: {script_path}")
                    return True
                else:
                    # 如果没有extra_args，假设endpoint本身是可执行文件
                    self.logger.info(f"✅ stdio服务器配置正确: {server_config.endpoint}")
                    return True
                    
            elif server_config.protocol == MCPProtocol.HTTP:
                # 对于HTTP服务器，尝试健康检查
                import httpx
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(f"{server_config.endpoint}/health")
                        return response.status_code == 200
                except (httpx.HTTPError, ConnectionError, OSError, TimeoutError):
                    return False
            return False
        except Exception as e:
            self.logger.warning(f"⚠️ 检查服务器连接性失败: {str(e)}")
            return False

    async def disconnect(self):
        """断开MCP连接"""
        # MCP客户端主要是临时进程连接，不需要特殊的断开处理
        self.status = ClientStatus.DISCONNECTED
        self.logger.info("🔌 MCP客户端已断开连接")

    async def request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        重写request方法以支持MCP特定的请求格式

        Args:
            request_data: 包含server_name、tool_name、arguments的字典

        Returns:
            Dict[str, Any]: 工具执行结果
        """
        if self.status != ClientStatus.CONNECTED:
            raise RuntimeError(f"客户端未连接，当前状态: {self.status.value}")

        return await self._execute_request_with_retry(request_data)

    async def _execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行MCP请求

        Args:
            request: 请求数据，包含server_name、tool_name、arguments等

        Returns:
            Dict[str, Any]: 工具执行结果
        """
        server_name = request["server_name"]
        tool_name = request["tool_name"]
        arguments = request.get("arguments", {})

        # 获取服务器配置
        if server_name not in self.servers:
            raise ValueError(f"未配置的MCP服务器: {server_name}")

        server_config = self.servers[server_name]

        # 构建MCP请求
        mcp_request = {
            "jsonrpc": "2.0",
            "id": f"req_{self._get_current_timestamp()}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        # 执行MCP调用
        if server_config.protocol == MCPProtocol.STDIO:
            return await self._execute_stdio_call(server_config, mcp_request)
        elif server_config.protocol == MCPProtocol.HTTP:
            return await self._execute_http_call(server_config, mcp_request)
        else:
            raise ValueError(f"不支持的MCP协议: {server_config.protocol}")

    async def _execute_stdio_call(self, server_config: MCPServerConfig, request: Dict) -> Dict[str, Any]:
        """执行stdio协议调用"""
        try:
            # 构建命令
            cmd = [server_config.endpoint]
            if server_config.extra_args:
                cmd.extend(server_config.extra_args)

            # 准备环境变量（从配置中获取并合并到当前环境）
            import os
            env = os.environ.copy()
            if hasattr(server_config, 'env') and server_config.env:
                env.update(server_config.env)

            # 执行子进程
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            try:
                # 步骤1: 发送initialize请求（MCP协议握手）
                init_request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "daml-rag-client",
                            "version": "2.0.0"
                        }
                    }
                }
                
                process.stdin.write((json.dumps(init_request) + "\n").encode())
                await process.stdin.drain()
                
                # 读取initialize响应（跳过非JSON行）
                init_response = None
                for _ in range(20):  # 最多尝试20行
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
                    line_str = line.decode().strip()
                    if line_str.startswith("{"):
                        try:
                            init_response = json.loads(line_str)
                            break
                        except json.JSONDecodeError:
                            continue
                
                if not init_response:
                    raise Exception("未收到MCP初始化响应")
                
                if "error" in init_response:
                    raise Exception(f"MCP初始化失败: {init_response['error']}")
                
                # 步骤2: 发送initialized通知
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {}
                }
                
                process.stdin.write((json.dumps(initialized_notification) + "\n").encode())
                await process.stdin.drain()
                
                # 步骤3: 发送实际的工具调用请求
                process.stdin.write((json.dumps(request) + "\n").encode())
                await process.stdin.drain()
                
                # 关闭stdin，让进程知道没有更多输入
                process.stdin.close()
                
                # 读取工具调用响应（跳过非JSON行）
                response = None
                for _ in range(10):  # 最多尝试10行
                    line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=server_config.timeout
                    )
                    line_str = line.decode().strip()
                    if line_str.startswith("{"):
                        try:
                            response = json.loads(line_str)
                            # 确保这是我们的响应（id匹配）
                            if response.get("id") == request.get("id"):
                                break
                        except json.JSONDecodeError:
                            continue
                
                # 等待进程结束
                try:
                    await asyncio.wait_for(process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                
                if not response:
                    raise Exception("未收到MCP工具调用响应")
                
                if "error" in response:
                    raise Exception(f"MCP工具错误: {response['error']}")

                if "result" in response:
                    return response["result"]
                else:
                    raise Exception("MCP响应格式错误")
                    
            except asyncio.TimeoutError:
                # 超时时杀死进程
                process.kill()
                await process.wait()
                raise Exception(f"MCP调用超时: {server_config.name}")
            except Exception as e:
                # 确保进程被清理
                if process.returncode is None:
                    process.kill()
                    await process.wait()
                raise

        except json.JSONDecodeError as e:
            raise Exception(f"MCP响应解析失败: {e}")
        except Exception as e:
            raise Exception(f"MCP通信异常: {e}")

    async def _execute_http_call(self, server_config: MCPServerConfig, request: Dict) -> Dict[str, Any]:
        """执行HTTP协议调用"""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=server_config.timeout) as client:
                response = await client.post(
                    f"{server_config.endpoint}/tools/call",
                    json=request,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()

                result = response.json()
                if "error" in result:
                    raise Exception(f"MCP工具错误: {result['error']}")

                if "data" in result:
                    return result["data"]
                elif "result" in result:
                    return result["result"]
                else:
                    return result

        except Exception as e:
            raise Exception(f"MCP HTTP调用失败: {e}")

    async def call_tool(self, server_name: str, tool_name: str,
                        arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用MCP工具

        Args:
            server_name: MCP服务器名称
            tool_name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        return await self.request({
            "server_name": server_name,
            "tool_name": tool_name,
            "arguments": arguments
        })

    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """
        列出服务器的所有工具

        Args:
            server_name: MCP服务器名称

        Returns:
            工具列表
        """
        if server_name not in self.servers:
            raise ValueError(f"未配置的MCP服务器: {server_name}")

        server_config = self.servers[server_name]

        request = {
            "jsonrpc": "2.0",
            "id": f"list_tools_{self._get_current_timestamp()}",
            "method": "tools/list",
            "params": {}
        }

        if server_config.protocol == MCPProtocol.STDIO:
            result = await self._execute_stdio_call(server_config, request)
        else:
            result = await self._execute_http_call(server_config, request)

        return result.get("tools", [])

    def get_server_config(self, server_name: str) -> Optional[MCPServerConfig]:
        """
        获取服务器配置

        Args:
            server_name: 服务器名称

        Returns:
            Optional[MCPServerConfig]: 服务器配置
        """
        return self.servers.get(server_name)

    def get_all_servers(self) -> Dict[str, MCPServerConfig]:
        """
        获取所有服务器配置

        Returns:
            Dict[str, MCPServerConfig]: 服务器配置字典
        """
        return self.servers.copy()

    def reload_configuration(self) -> bool:
        """
        重新加载配置

        Returns:
            bool: 重新加载是否成功
        """
        try:
            old_servers = self.servers.copy()
            self._load_configuration()

            # 检查配置是否有变化
            if set(self.servers.keys()) == set(old_servers.keys()):
                self.logger.info("🔄 MCP配置重新加载成功，配置无变化")
            else:
                self.logger.info("🔄 MCP配置重新加载成功，配置已更新")

            return True

        except Exception as e:
            self.logger.error(f"🔄 MCP配置重新加载失败: {str(e)}")
            return False

    def get_config_status(self) -> Dict[str, Any]:
        """
        获取配置状态

        Returns:
            Dict[str, Any]: 配置状态信息
        """
        return {
            "config_loaded": self.config_load_status,
            "config_path": str(self.config_loader.config_path),
            "servers_count": len(self.servers),
            "active_servers": list(self.servers.keys()),
            "validation_result": self.config_loader.validate_config().__dict__
        }


# 便捷工厂函数
def create_configurable_mcp_client(
    config_path: Optional[str] = None,
    auto_reload: bool = False
) -> ConfigurableMCPClient:
    """
    创建可配置MCP客户端

    Args:
        config_path: 配置文件路径
        auto_reload: 是否自动重载配置

    Returns:
        ConfigurableMCPClient: 可配置MCP客户端
    """
    config = MCPClientConfig(
        config_path=config_path,
        auto_reload=auto_reload
    )
    return ConfigurableMCPClient(config)


# 兼容性函数 - 与旧版本API兼容
def create_mcp_client() -> ConfigurableMCPClient:
    """
    创建默认配置的MCP客户端 (兼容v1.0)

    Returns:
        ConfigurableMCPClient: MCP客户端实例
    """
    return create_configurable_mcp_client()


# 使用示例
async def example_usage():
    """使用示例"""
    try:
        # 创建客户端
        client = create_configurable_mcp_client()

        # 连接
        await client.connect()

        # 获取配置状态
        status = client.get_config_status()
        print(f"配置状态: {status}")

        # 列出所有服务器
        servers = client.get_all_servers()
        print(f"可用服务器: {list(servers.keys())}")

        # 调用工具
        # result = await client.call_tool(
        #     "user-profile-stdio",
        #     "get_user_profile",
        #     {"user_id": "test_user"}
        # )
        # print(f"工具调用结果: {result}")

    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
