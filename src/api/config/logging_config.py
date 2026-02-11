# -*- coding: utf-8 -*-
"""
日志配置 - Logging Configuration

统一管理日志级别和输出格式

版本: v1.2.0
创建日期: 2025-12-22
更新日期: 2025-12-30
"""

import logging
import os
from pathlib import Path
from typing import Dict
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

# 环境变量控制
LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING').upper()  # 默认WARNING，只输出警告和错误
ENABLE_REQUEST_LOGGING = os.getenv('ENABLE_REQUEST_LOGGING', 'false').lower() == 'true'
ENABLE_FILE_LOGGING = os.getenv('ENABLE_FILE_LOGGING', 'true').lower() == 'true'  # 默认启用文件日志

# 日志目录
LOG_DIR = Path('/app/logs')
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志文件基础路径（不带日期后缀，由TimedRotatingFileHandler自动管理）
LOG_FILE_BASE = LOG_DIR / 'daml-rag.log'
ERROR_LOG_FILE_BASE = LOG_DIR / 'daml-rag-error.log'

# 兼容旧代码的变量（动态获取当前日期的文件名）
def get_current_log_file():
    """获取当前日期的日志文件路径"""
    return LOG_DIR / f'daml-rag-{datetime.now().strftime("%Y%m%d")}.log'

def get_current_error_log_file():
    """获取当前日期的错误日志文件路径"""
    return LOG_DIR / f'daml-rag-error-{datetime.now().strftime("%Y%m%d")}.log'

# 保持向后兼容
LOG_FILE = get_current_log_file()
ERROR_LOG_FILE = get_current_error_log_file()

# 日志级别映射
LOG_LEVELS: Dict[str, int] = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# 获取实际日志级别
ACTUAL_LOG_LEVEL = LOG_LEVELS.get(LOG_LEVEL, logging.WARNING)


def configure_logging():
    """配置全局日志"""
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(ACTUAL_LOG_LEVEL)
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    
    # 1. 控制台处理器（始终启用）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(ACTUAL_LOG_LEVEL)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 2. 文件处理器（可选）- 使用TimedRotatingFileHandler按天轮转
    if ENABLE_FILE_LOGGING:
        # 所有日志文件（INFO及以上）- 按天轮转，保留30天
        file_handler = TimedRotatingFileHandler(
            LOG_FILE_BASE,
            when='midnight',  # 每天午夜轮转
            interval=1,
            backupCount=30,  # 保留30天
            encoding='utf-8'
        )
        # 设置日志文件名后缀格式为 YYYYMMDD
        file_handler.suffix = '-%Y%m%d.log'
        file_handler.namer = lambda name: name.replace('.log-', '-').replace('.log', '')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        # 错误日志文件（ERROR及以上）- 按天轮转，保留30天
        error_handler = TimedRotatingFileHandler(
            ERROR_LOG_FILE_BASE,
            when='midnight',  # 每天午夜轮转
            interval=1,
            backupCount=30,  # 保留30天
            encoding='utf-8'
        )
        error_handler.suffix = '-%Y%m%d.log'
        error_handler.namer = lambda name: name.replace('.log-', '-').replace('.log', '')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
        
        # 获取当前实际写入的文件名
        current_log = get_current_log_file()
        current_error_log = get_current_error_log_file()
        print(f"✅ 文件日志已启用（按天轮转）:")
        print(f"   - 所有日志: {current_log}")
        print(f"   - 错误日志: {current_error_log}")
        print(f"   - 保留天数: 30天")
    
    # 3. 审计日志处理器 - 独立文件，记录认证和权限相关事件
    if ENABLE_FILE_LOGGING:
        audit_log_base = LOG_DIR / 'audit.log'
        audit_handler = TimedRotatingFileHandler(
            audit_log_base,
            when='midnight',
            interval=1,
            backupCount=90,  # 审计日志保留90天
            encoding='utf-8'
        )
        audit_handler.suffix = '-%Y%m%d.log'
        audit_handler.namer = lambda name: name.replace('.log-', '-').replace('.log', '')
        audit_handler.setLevel(logging.WARNING)
        audit_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        audit_handler.setFormatter(logging.Formatter(audit_format))

        # 为 audit.* logger 添加独立handler
        for audit_name in ['audit.auth', 'audit.permission']:
            audit_logger = logging.getLogger(audit_name)
            audit_logger.addHandler(audit_handler)
            audit_logger.setLevel(logging.WARNING)
            # 同时输出到控制台和主日志
            audit_logger.propagate = True

        print(f"   - 审计日志: {LOG_DIR / 'audit-YYYYMMDD.log'} (保留90天)")

    # 设置uvicorn日志级别（减少访问日志）
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.WARNING)
    
    # 设置FastAPI日志级别
    logging.getLogger('fastapi').setLevel(logging.WARNING)
    
    # 设置httpx日志级别（减少HTTP请求日志）
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    # 设置httpcore日志级别
    logging.getLogger('httpcore').setLevel(logging.WARNING)


def should_log_request() -> bool:
    """是否应该记录请求日志"""
    return ENABLE_REQUEST_LOGGING


def get_log_files() -> Dict[str, Path]:
    """获取日志文件路径（返回当前日期的文件）"""
    return {
        'all': get_current_log_file(),
        'error': get_current_error_log_file()
    }


# 导出
__all__ = [
    'configure_logging',
    'should_log_request',
    'get_log_files',
    'get_current_log_file',
    'get_current_error_log_file',
    'ACTUAL_LOG_LEVEL',
    'ENABLE_REQUEST_LOGGING',
    'ENABLE_FILE_LOGGING',
    'LOG_DIR',
    'LOG_FILE',
    'ERROR_LOG_FILE',
    'LOG_FILE_BASE',
    'ERROR_LOG_FILE_BASE'
]
