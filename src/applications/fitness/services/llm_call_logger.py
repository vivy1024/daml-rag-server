"""
大模型调用日志记录服务

记录所有LLM调用，保留至少6个月，用于合规审计。

版本: v1.0.0
创建日期: 2025-12-31
Requirements: 16.7
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import hashlib
import gzip
import shutil

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """LLM提供商"""
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"
    MOONSHOT = "moonshot"
    QWEN = "qwen"
    UNKNOWN = "unknown"


class CallStatus(Enum):
    """调用状态"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"


@dataclass
class LLMCallLog:
    """LLM调用日志记录"""
    # 基本信息
    call_id: str                          # 调用唯一ID
    timestamp: str                        # 调用时间（ISO格式）
    provider: str                         # LLM提供商
    model: str                            # 模型名称
    
    # 用户信息（脱敏）
    user_id: Optional[str] = None         # 用户ID（可选）
    session_id: Optional[str] = None      # 会话ID（可选）
    
    # 请求信息
    input_tokens: int = 0                 # 输入token数
    input_hash: str = ""                  # 输入内容哈希（用于去重）
    system_prompt_length: int = 0         # 系统提示词长度
    few_shot_count: int = 0               # Few-Shot示例数量
    tool_results_count: int = 0           # 工具结果数量
    
    # 响应信息
    output_tokens: int = 0                # 输出token数
    output_length: int = 0                # 输出字符长度
    
    # 性能信息
    latency_ms: int = 0                   # 延迟（毫秒）
    status: str = "success"               # 调用状态
    error_message: Optional[str] = None   # 错误信息（如果失败）
    
    # 元数据
    is_streaming: bool = False            # 是否流式调用
    retry_count: int = 0                  # 重试次数
    temperature: float = 0.7              # 温度参数
    max_tokens: int = 2000                # 最大token数
    
    # 内容安全
    content_filtered: bool = False        # 是否触发内容过滤
    filter_categories: List[str] = field(default_factory=list)  # 过滤类别


class LLMCallLogger:
    """
    LLM调用日志记录器
    
    功能：
    1. 记录所有LLM调用
    2. 日志文件按日期分割
    3. 自动压缩旧日志
    4. 保留至少6个月
    5. 支持日志查询
    """
    
    def __init__(
        self,
        log_dir: str = "data/logs/llm_calls",
        retention_days: int = 180,  # 6个月
        compress_after_days: int = 7,
        max_file_size_mb: int = 100
    ):
        """
        初始化日志记录器
        
        Args:
            log_dir: 日志目录
            retention_days: 日志保留天数
            compress_after_days: 多少天后压缩日志
            max_file_size_mb: 单个日志文件最大大小（MB）
        """
        self.log_dir = Path(log_dir)
        self.retention_days = retention_days
        self.compress_after_days = compress_after_days
        self.max_file_size_mb = max_file_size_mb
        
        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前日志文件
        self._current_date: Optional[str] = None
        self._current_file: Optional[Path] = None
        self._file_handle = None
        
        # 统计信息
        self._call_count = 0
        self._error_count = 0
        
        logger.info(f"LLM调用日志记录器初始化完成: {self.log_dir}")
    
    def _get_log_file(self) -> Path:
        """获取当前日志文件路径"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if self._current_date != today:
            # 日期变化，关闭旧文件
            self._close_file()
            self._current_date = today
            self._current_file = self.log_dir / f"llm_calls_{today}.jsonl"
        
        return self._current_file
    
    def _close_file(self):
        """关闭当前文件"""
        if self._file_handle:
            try:
                self._file_handle.close()
            except Exception as e:
                logger.warning(f"关闭日志文件失败: {e}")
            self._file_handle = None
    
    def _generate_call_id(self) -> str:
        """生成调用ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"llm_{timestamp}_{self._call_count:06d}"
    
    def _hash_content(self, content: str) -> str:
        """计算内容哈希（用于去重和隐私保护）"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def log_call(
        self,
        provider: LLMProvider,
        model: str,
        input_content: str,
        output_content: str,
        latency_ms: int,
        status: CallStatus = CallStatus.SUCCESS,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        system_prompt: str = "",
        few_shot_count: int = 0,
        tool_results_count: int = 0,
        is_streaming: bool = False,
        retry_count: int = 0,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        error_message: Optional[str] = None,
        content_filtered: bool = False,
        filter_categories: Optional[List[str]] = None,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> str:
        """
        记录LLM调用
        
        Args:
            provider: LLM提供商
            model: 模型名称
            input_content: 输入内容
            output_content: 输出内容
            latency_ms: 延迟（毫秒）
            status: 调用状态
            user_id: 用户ID（可选）
            session_id: 会话ID（可选）
            system_prompt: 系统提示词
            few_shot_count: Few-Shot示例数量
            tool_results_count: 工具结果数量
            is_streaming: 是否流式调用
            retry_count: 重试次数
            temperature: 温度参数
            max_tokens: 最大token数
            error_message: 错误信息
            content_filtered: 是否触发内容过滤
            filter_categories: 过滤类别
            input_tokens: 输入token数
            output_tokens: 输出token数
        
        Returns:
            str: 调用ID
        """
        self._call_count += 1
        if status != CallStatus.SUCCESS:
            self._error_count += 1
        
        # 创建日志记录
        log = LLMCallLog(
            call_id=self._generate_call_id(),
            timestamp=datetime.now().isoformat(),
            provider=provider.value,
            model=model,
            user_id=user_id,
            session_id=session_id,
            input_tokens=input_tokens or len(input_content) // 4,  # 估算
            input_hash=self._hash_content(input_content),
            system_prompt_length=len(system_prompt),
            few_shot_count=few_shot_count,
            tool_results_count=tool_results_count,
            output_tokens=output_tokens or len(output_content) // 4,  # 估算
            output_length=len(output_content),
            latency_ms=latency_ms,
            status=status.value,
            error_message=error_message,
            is_streaming=is_streaming,
            retry_count=retry_count,
            temperature=temperature,
            max_tokens=max_tokens,
            content_filtered=content_filtered,
            filter_categories=filter_categories or []
        )
        
        # 写入日志文件
        await self._write_log(log)
        
        return log.call_id
    
    async def _write_log(self, log: LLMCallLog):
        """写入日志到文件"""
        try:
            log_file = self._get_log_file()
            log_line = json.dumps(asdict(log), ensure_ascii=False) + "\n"
            
            # 异步写入
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_line)
            
            # 检查文件大小
            if log_file.stat().st_size > self.max_file_size_mb * 1024 * 1024:
                await self._rotate_log(log_file)
        
        except Exception as e:
            logger.error(f"写入LLM调用日志失败: {e}")
    
    async def _rotate_log(self, log_file: Path):
        """轮转日志文件"""
        try:
            # 重命名当前文件
            timestamp = datetime.now().strftime("%H%M%S")
            rotated_file = log_file.with_suffix(f".{timestamp}.jsonl")
            log_file.rename(rotated_file)
            
            # 压缩旧文件
            await self._compress_file(rotated_file)
            
            logger.info(f"日志文件已轮转: {rotated_file}")
        
        except Exception as e:
            logger.error(f"轮转日志文件失败: {e}")
    
    async def _compress_file(self, file_path: Path):
        """压缩日志文件"""
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + ".gz")
            
            with open(file_path, "rb") as f_in:
                with gzip.open(compressed_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 删除原文件
            file_path.unlink()
            
            logger.info(f"日志文件已压缩: {compressed_path}")
        
        except Exception as e:
            logger.error(f"压缩日志文件失败: {e}")
    
    async def cleanup_old_logs(self):
        """清理过期日志"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            compress_date = datetime.now() - timedelta(days=self.compress_after_days)
            
            for file_path in self.log_dir.glob("llm_calls_*.jsonl*"):
                try:
                    # 从文件名提取日期
                    date_str = file_path.stem.split("_")[2][:10]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    # 删除过期文件
                    if file_date < cutoff_date:
                        file_path.unlink()
                        logger.info(f"删除过期日志: {file_path}")
                    
                    # 压缩旧文件
                    elif file_date < compress_date and not file_path.suffix.endswith(".gz"):
                        await self._compress_file(file_path)
                
                except Exception as e:
                    logger.warning(f"处理日志文件失败 {file_path}: {e}")
        
        except Exception as e:
            logger.error(f"清理过期日志失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_calls": self._call_count,
            "error_count": self._error_count,
            "error_rate": self._error_count / max(self._call_count, 1),
            "log_dir": str(self.log_dir),
            "retention_days": self.retention_days,
        }
    
    async def query_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        provider: Optional[LLMProvider] = None,
        status: Optional[CallStatus] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询日志
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            provider: LLM提供商
            status: 调用状态
            user_id: 用户ID
            limit: 返回数量限制
        
        Returns:
            List[Dict]: 日志记录列表
        """
        results = []
        
        try:
            # 确定要查询的文件
            if start_date is None:
                start_date = datetime.now() - timedelta(days=7)
            if end_date is None:
                end_date = datetime.now()
            
            current_date = start_date
            while current_date <= end_date and len(results) < limit:
                date_str = current_date.strftime("%Y-%m-%d")
                log_file = self.log_dir / f"llm_calls_{date_str}.jsonl"
                
                if log_file.exists():
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if len(results) >= limit:
                                break
                            
                            try:
                                log = json.loads(line)
                                
                                # 应用过滤条件
                                if provider and log.get("provider") != provider.value:
                                    continue
                                if status and log.get("status") != status.value:
                                    continue
                                if user_id and log.get("user_id") != user_id:
                                    continue
                                
                                results.append(log)
                            
                            except json.JSONDecodeError:
                                continue
                
                current_date += timedelta(days=1)
        
        except Exception as e:
            logger.error(f"查询日志失败: {e}")
        
        return results


# 单例实例
_llm_call_logger: Optional[LLMCallLogger] = None


def get_llm_call_logger() -> LLMCallLogger:
    """获取LLM调用日志记录器单例"""
    global _llm_call_logger
    if _llm_call_logger is None:
        _llm_call_logger = LLMCallLogger()
    return _llm_call_logger


# 便捷函数
async def log_llm_call(
    provider: str,
    model: str,
    input_content: str,
    output_content: str,
    latency_ms: int,
    **kwargs
) -> str:
    """
    便捷函数：记录LLM调用
    
    Args:
        provider: LLM提供商名称
        model: 模型名称
        input_content: 输入内容
        output_content: 输出内容
        latency_ms: 延迟（毫秒）
        **kwargs: 其他参数
    
    Returns:
        str: 调用ID
    """
    logger_instance = get_llm_call_logger()
    
    # 转换provider字符串为枚举
    try:
        provider_enum = LLMProvider(provider.lower())
    except ValueError:
        provider_enum = LLMProvider.UNKNOWN
    
    # 转换status字符串为枚举
    status_str = kwargs.pop("status", "success")
    try:
        status_enum = CallStatus(status_str.lower())
    except ValueError:
        status_enum = CallStatus.SUCCESS
    
    return await logger_instance.log_call(
        provider=provider_enum,
        model=model,
        input_content=input_content,
        output_content=output_content,
        latency_ms=latency_ms,
        status=status_enum,
        **kwargs
    )
