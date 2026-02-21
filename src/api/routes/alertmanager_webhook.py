# -*- coding: utf-8 -*-
"""
Alertmanager → 企业微信 Webhook 转发

接收 Alertmanager 标准 webhook 告警，格式化为企业微信 Markdown 消息后转发。
配置环境变量 WECHAT_WEBHOOK_URL 即可启用。

版本：v2.0.0
创建日期：2026-02-21
"""

import os
import logging
from datetime import datetime
from typing import List

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

WECHAT_WEBHOOK_URL = os.getenv("WECHAT_WEBHOOK_URL", "")

# ─── Alertmanager Payload Models ─────────────────────────────────────────────

class Alert(BaseModel):
    status: str  # "firing" | "resolved"
    labels: dict = {}
    annotations: dict = {}
    startsAt: str = ""
    endsAt: str = ""

class AlertmanagerPayload(BaseModel):
    status: str  # "firing" | "resolved"
    alerts: List[Alert] = []
    groupLabels: dict = {}
    commonLabels: dict = {}

# ─── 企业微信 Markdown 构建 ──────────────────────────────────────────────────

SEVERITY_EMOJI = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}
STATUS_TEXT = {"firing": "🔥 触发", "resolved": "✅ 已恢复"}
# 企业微信 font color: warning=橙色, info=绿色, comment=灰色
SEVERITY_COLOR = {"critical": "warning", "warning": "warning", "info": "info"}


def _build_wechat_markdown(payload: AlertmanagerPayload) -> dict:
    """将 Alertmanager payload 转换为企业微信 Markdown 消息"""
    severity = payload.commonLabels.get("severity", "warning")
    alertname = payload.groupLabels.get("alertname", "Unknown")
    emoji = SEVERITY_EMOJI.get(severity, "⚠️")
    status_text = STATUS_TEXT.get(payload.status, payload.status)
    color = SEVERITY_COLOR.get(severity, "warning")

    lines = [
        f"{emoji} <font color=\"{color}\">**[{severity.upper()}] {alertname}**</font>",
        f"> 状态: {status_text} | 告警数: {len(payload.alerts)} | {datetime.now().strftime('%H:%M:%S')}",
    ]

    for i, alert in enumerate(payload.alerts, 1):
        summary = alert.annotations.get("summary", "无摘要")
        description = alert.annotations.get("description", "")
        instance = alert.labels.get("instance", "")
        job = alert.labels.get("job", "")

        lines.append(f"**{i}. {summary}**")
        if description:
            lines.append(f"> {description}")
        details = []
        if instance:
            details.append(f"实例:`{instance}`")
        if job:
            details.append(f"任务:`{job}`")
        if alert.startsAt:
            details.append(f"开始:{alert.startsAt[:19]}")
        if details:
            lines.append(" | ".join(details))

    lines.append(f"<font color=\"comment\">玉珍健身 · Alertmanager · Prometheus</font>")

    return {
        "msgtype": "markdown",
        "markdown": {"content": "\n".join(lines)}
    }


# ─── 路由 ────────────────────────────────────────────────────────────────────

@router.post("/alertmanager")
async def receive_alertmanager_webhook(payload: AlertmanagerPayload):
    """接收 Alertmanager 告警并转发到企业微信"""
    if not WECHAT_WEBHOOK_URL:
        logger.warning("WECHAT_WEBHOOK_URL 未配置，告警仅记录日志")
        for alert in payload.alerts:
            sev = alert.labels.get("severity", "unknown")
            name = alert.labels.get("alertname", "unknown")
            summary = alert.annotations.get("summary", "")
            logger.info(f"[ALERT][{alert.status}][{sev}] {name}: {summary}")
        return {"status": "logged", "message": "WECHAT_WEBHOOK_URL not configured"}

    msg = _build_wechat_markdown(payload)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(WECHAT_WEBHOOK_URL, json=msg)
            resp.raise_for_status()
            result = resp.json()
            if result.get("errcode") == 0:
                logger.info(f"企业微信告警发送成功: {payload.status} {len(payload.alerts)} alerts")
                return {"status": "sent", "wechat_response": result}
            else:
                logger.error(f"企业微信返回错误: {result}")
                return {"status": "error", "wechat_response": result}
    except httpx.HTTPError as e:
        logger.error(f"企业微信告警发送失败: {e}")
        return {"status": "error", "message": str(e)}
