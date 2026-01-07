#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAML-RAG 服务器启动脚本
解决Python模块导入问题

v2.1.0 更新：
- 添加自定义access log过滤器，过滤健康检查请求日志
- 减少日志膨胀，提高性能
"""

import sys
import os
import logging
from pathlib import Path

# 添加src目录到Python路径
app_path = Path(__file__).parent
if str(app_path) not in sys.path:
    sys.path.insert(0, str(app_path))


class HealthCheckFilter(logging.Filter):
    """
    过滤健康检查相关的access log
    
    这些请求每分钟会产生10-15条日志，一天约14,400-21,600条
    对于监控系统来说是正常的，但会导致日志膨胀
    """
    
    # 需要过滤的路径前缀
    FILTERED_PATHS = [
        '/api/health',
        '/health',
        '/api/health/',
        '/health/',
        '/api/health/metrics',
        '/api/health/metrics/prometheus',
        '/api/health/metrics/streaming',
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        返回True表示保留日志，False表示过滤掉
        """
        message = record.getMessage()
        
        # 检查是否是健康检查相关的请求
        for path in self.FILTERED_PATHS:
            if f'"{path}' in message or f' {path} ' in message:
                return False
        
        return True


def setup_logging():
    """配置日志过滤器"""
    # 获取uvicorn的access logger
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.addFilter(HealthCheckFilter())
    
    # 同时过滤uvicorn.error中的健康检查日志
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.addFilter(HealthCheckFilter())


# 导入并运行main
if __name__ == "__main__":
    from src.api.main import app
    import uvicorn

    print("🚀 Starting DAML-RAG server (v3.0 - 精简架构)...")
    print("📋 日志优化: 健康检查请求不记录access log")
    
    # 设置日志过滤器
    setup_logging()
    
    # 从环境变量读取端口（Zeabur等平台会自动设置PORT）
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))
    
    print(f"🌐 监听地址: {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )