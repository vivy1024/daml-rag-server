# -*- coding: utf-8 -*-
"""
告警系统 - Alert System

提供性能和错误告警功能，包括：
1. 阈值配置
2. 告警规则
3. 告警触发
4. 告警通知
5. 告警历史

版本: v1.0.0
日期: 2025-12-16
作者: 薛小川
"""

import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

from .structured_logger import get_logger

logger = get_logger("alert_system")


class AlertSeverity(Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态"""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    description: str
    metric_name: str
    condition: str  # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    severity: AlertSeverity
    duration_seconds: int = 60  # 持续时间
    cooldown_seconds: int = 300  # 冷却时间
    enabled: bool = True
    labels: Dict[str, str] = field(default_factory=dict)
    
    def evaluate(self, value: float) -> bool:
        """
        评估规则
        
        Args:
            value: 指标值
            
        Returns:
            bool: 是否触发告警
        """
        if not self.enabled:
            return False
        
        if self.condition == "gt":
            return value > self.threshold
        elif self.condition == "lt":
            return value < self.threshold
        elif self.condition == "eq":
            return value == self.threshold
        elif self.condition == "gte":
            return value >= self.threshold
        elif self.condition == "lte":
            return value <= self.threshold
        else:
            return False


@dataclass
class Alert:
    """告警"""
    alert_id: str
    rule_name: str
    severity: AlertSeverity
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    timestamp: float
    status: AlertStatus = AlertStatus.ACTIVE
    resolved_at: Optional[float] = None
    acknowledged_at: Optional[float] = None
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "alert_id": self.alert_id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "status": self.status.value,
            "resolved_at": self.resolved_at,
            "acknowledged_at": self.acknowledged_at,
            "labels": self.labels,
            "metadata": self.metadata
        }


class AlertSystem:
    """告警系统"""
    
    def __init__(
        self,
        max_alerts: int = 1000,
        notification_handlers: Optional[List[Callable]] = None
    ):
        """
        初始化告警系统
        
        Args:
            max_alerts: 最大告警历史数量
            notification_handlers: 通知处理器列表
        """
        self.max_alerts = max_alerts
        self.notification_handlers = notification_handlers or []
        
        # 告警规则
        self.rules: Dict[str, AlertRule] = {}
        
        # 活跃告警
        self.active_alerts: Dict[str, Alert] = {}
        
        # 告警历史
        self.alert_history: deque = deque(maxlen=max_alerts)
        
        # 规则触发状态
        self.rule_trigger_times: Dict[str, float] = {}
        self.rule_last_alert_times: Dict[str, float] = {}
        
        # 注册默认规则
        self._register_default_rules()
        
        logger.info("告警系统初始化完成")
    
    def _register_default_rules(self):
        """注册默认告警规则"""
        # 响应时间告警
        self.add_rule(AlertRule(
            name="high_response_time",
            description="响应时间过高",
            metric_name="request_duration_seconds",
            condition="gt",
            threshold=5.0,
            severity=AlertSeverity.WARNING,
            duration_seconds=60
        ))
        
        # 错误率告警
        self.add_rule(AlertRule(
            name="high_error_rate",
            description="错误率过高",
            metric_name="error_rate",
            condition="gt",
            threshold=0.1,
            severity=AlertSeverity.ERROR,
            duration_seconds=60
        ))
        
        # CPU使用率告警
        self.add_rule(AlertRule(
            name="high_cpu_usage",
            description="CPU使用率过高",
            metric_name="cpu_usage_percent",
            condition="gt",
            threshold=90.0,
            severity=AlertSeverity.WARNING,
            duration_seconds=120
        ))
        
        # 内存使用告警
        self.add_rule(AlertRule(
            name="high_memory_usage",
            description="内存使用过高",
            metric_name="memory_usage_bytes",
            condition="gt",
            threshold=8 * 1024 * 1024 * 1024,  # 8GB
            severity=AlertSeverity.WARNING,
            duration_seconds=120
        ))
        
        # 缓存命中率告警
        self.add_rule(AlertRule(
            name="low_cache_hit_rate",
            description="缓存命中率过低",
            metric_name="cache_hit_rate",
            condition="lt",
            threshold=0.5,
            severity=AlertSeverity.WARNING,
            duration_seconds=300
        ))
    
    def add_rule(self, rule: AlertRule):
        """
        添加告警规则
        
        Args:
            rule: 告警规则
        """
        self.rules[rule.name] = rule
        logger.info(
            "添加告警规则",
            rule_name=rule.name,
            metric=rule.metric_name,
            threshold=rule.threshold
        )
    
    def remove_rule(self, rule_name: str):
        """
        移除告警规则
        
        Args:
            rule_name: 规则名称
        """
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info("移除告警规则", rule_name=rule_name)
    
    def enable_rule(self, rule_name: str):
        """
        启用告警规则
        
        Args:
            rule_name: 规则名称
        """
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True
            logger.info("启用告警规则", rule_name=rule_name)
    
    def disable_rule(self, rule_name: str):
        """
        禁用告警规则
        
        Args:
            rule_name: 规则名称
        """
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False
            logger.info("禁用告警规则", rule_name=rule_name)
    
    def check_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ):
        """
        检查指标是否触发告警
        
        Args:
            metric_name: 指标名称
            value: 指标值
            labels: 标签
        """
        current_time = time.time()
        labels = labels or {}
        
        # 查找匹配的规则
        for rule in self.rules.values():
            if rule.metric_name != metric_name:
                continue
            
            # 评估规则
            if rule.evaluate(value):
                # 检查持续时间
                trigger_key = f"{rule.name}:{metric_name}"
                
                if trigger_key not in self.rule_trigger_times:
                    # 首次触发
                    self.rule_trigger_times[trigger_key] = current_time
                else:
                    # 检查是否持续超过阈值时间
                    trigger_duration = current_time - self.rule_trigger_times[trigger_key]
                    
                    if trigger_duration >= rule.duration_seconds:
                        # 检查冷却时间
                        last_alert_time = self.rule_last_alert_times.get(trigger_key, 0)
                        if current_time - last_alert_time >= rule.cooldown_seconds:
                            # 触发告警
                            self._trigger_alert(rule, metric_name, value, labels)
                            self.rule_last_alert_times[trigger_key] = current_time
            else:
                # 规则不再满足，清除触发时间
                trigger_key = f"{rule.name}:{metric_name}"
                if trigger_key in self.rule_trigger_times:
                    del self.rule_trigger_times[trigger_key]
    
    def _trigger_alert(
        self,
        rule: AlertRule,
        metric_name: str,
        value: float,
        labels: Dict[str, str]
    ):
        """
        触发告警
        
        Args:
            rule: 告警规则
            metric_name: 指标名称
            value: 指标值
            labels: 标签
        """
        import uuid
        
        alert_id = str(uuid.uuid4())
        
        message = (
            f"{rule.description}: {metric_name}={value:.2f} "
            f"(阈值: {rule.condition} {rule.threshold})"
        )
        
        alert = Alert(
            alert_id=alert_id,
            rule_name=rule.name,
            severity=rule.severity,
            message=message,
            metric_name=metric_name,
            metric_value=value,
            threshold=rule.threshold,
            timestamp=time.time(),
            labels={**rule.labels, **labels}
        )
        
        # 添加到活跃告警
        self.active_alerts[alert_id] = alert
        
        # 添加到历史
        self.alert_history.append(alert)
        
        # 记录日志
        logger.warning(
            "触发告警",
            alert_id=alert_id,
            rule_name=rule.name,
            severity=rule.severity.value,
            alert_message=message,
            metric_name=metric_name,
            metric_value=value
        )
        
        # 发送通知
        self._send_notifications(alert)
    
    def _send_notifications(self, alert: Alert):
        """
        发送告警通知
        
        Args:
            alert: 告警对象
        """
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(
                    "告警通知发送失败",
                    alert_id=alert.alert_id,
                    error=str(e)
                )
    
    def resolve_alert(self, alert_id: str):
        """
        解决告警
        
        Args:
            alert_id: 告警ID
        """
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = time.time()
            
            del self.active_alerts[alert_id]
            
            logger.info(
                "告警已解决",
                alert_id=alert_id,
                rule_name=alert.rule_name
            )
    
    def acknowledge_alert(self, alert_id: str):
        """
        确认告警
        
        Args:
            alert_id: 告警ID
        """
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = time.time()
            
            logger.info(
                "告警已确认",
                alert_id=alert_id,
                rule_name=alert.rule_name
            )
    
    def get_active_alerts(
        self,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """
        获取活跃告警
        
        Args:
            severity: 严重程度过滤
            
        Returns:
            List[Alert]: 活跃告警列表
        """
        alerts = list(self.active_alerts.values())
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def get_alert_history(
        self,
        time_window_seconds: Optional[int] = None,
        severity: Optional[AlertSeverity] = None
    ) -> List[Alert]:
        """
        获取告警历史
        
        Args:
            time_window_seconds: 时间窗口（秒）
            severity: 严重程度过滤
            
        Returns:
            List[Alert]: 告警历史列表
        """
        alerts = list(self.alert_history)
        
        # 时间过滤
        if time_window_seconds:
            cutoff_time = time.time() - time_window_seconds
            alerts = [a for a in alerts if a.timestamp >= cutoff_time]
        
        # 严重程度过滤
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def get_alert_statistics(
        self,
        time_window_seconds: int = 3600
    ) -> Dict[str, Any]:
        """
        获取告警统计
        
        Args:
            time_window_seconds: 时间窗口（秒）
            
        Returns:
            Dict[str, Any]: 告警统计
        """
        cutoff_time = time.time() - time_window_seconds
        recent_alerts = [
            a for a in self.alert_history
            if a.timestamp >= cutoff_time
        ]
        
        # 按严重程度统计
        severity_counts = {
            severity.value: 0
            for severity in AlertSeverity
        }
        for alert in recent_alerts:
            severity_counts[alert.severity.value] += 1
        
        # 按规则统计
        rule_counts = {}
        for alert in recent_alerts:
            rule_counts[alert.rule_name] = rule_counts.get(alert.rule_name, 0) + 1
        
        # 按状态统计
        status_counts = {
            status.value: 0
            for status in AlertStatus
        }
        for alert in recent_alerts:
            status_counts[alert.status.value] += 1
        
        return {
            "time_window_seconds": time_window_seconds,
            "total_alerts": len(recent_alerts),
            "active_alerts": len(self.active_alerts),
            "severity_distribution": severity_counts,
            "rule_distribution": rule_counts,
            "status_distribution": status_counts,
            "top_rules": sorted(
                rule_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
    
    def add_notification_handler(self, handler: Callable):
        """
        添加通知处理器
        
        Args:
            handler: 通知处理器函数
        """
        self.notification_handlers.append(handler)
        logger.info("添加通知处理器")


# 全局告警系统实例
_global_alert_system: Optional[AlertSystem] = None


def get_alert_system() -> AlertSystem:
    """
    获取全局告警系统
    
    Returns:
        AlertSystem: 告警系统
    """
    global _global_alert_system
    if _global_alert_system is None:
        _global_alert_system = AlertSystem()
    return _global_alert_system


# 导出
__all__ = [
    "AlertSeverity",
    "AlertStatus",
    "AlertRule",
    "Alert",
    "AlertSystem",
    "get_alert_system"
]
