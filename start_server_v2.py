#!/usr/bin/env python3
"""
DAML-RAG v2 MCP Server 启动脚本

启动方式：
  python start_server_v2.py

通信协议：MCP over stdio（stdin/stdout JSON-RPC）
调用方：YuzhenFork Agent（通过 subprocess）
"""

import sys
import os
import asyncio
import logging

# 确保 /app 在 path 中
app_path = os.path.dirname(os.path.abspath(__file__))
if app_path not in sys.path:
    sys.path.insert(0, app_path)

# 配置日志（输出到 stderr，不干扰 stdio 通信）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger("daml-rag-v2")


async def main():
    """启动 MCP v2 服务器"""
    logger.info("Starting DAML-RAG v2 MCP Server...")

    from src_v2.server import main as server_main
    await server_main()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception(f"Server crashed: {e}")
        sys.exit(1)
