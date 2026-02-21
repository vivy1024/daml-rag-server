# -*- coding: utf-8 -*-
"""
Alertmanager → 飞书 Webhook 转发

接收 Alertmanager 标准 webhook 告警，格式化为飞书卡片消息后转发。
配置环境变量 FEISHU_WEBHOOK_URL 即可启用。

版本：v1.0.0
创建日期：2026-02-21
"""

import os
import logging
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")

# ─── Alertmanager Payload Models ─────────────────────────────────────────────

class AlertLabel(BaseModel):
    alertname: str = ""
    severity: str = ""
    job: str = ""
    instance: str = ""

class AlertAnnotation(BaseModel):
    summary: str = ""
    description: str = ""

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

# ─── 飞书卡片构建 ────────────────────────────────────────────────────────────

SEVERITY_COLORS = {
    "critical": "red",
    "warning": "orange",
    "info": "blue",
}

SEVERITY_EMOJI = {
    "critical": "🚨",
    "warning": "⚠️",
    "info": "ℹ️",
}

STATUS_TEXT = {
    "firing": "🔥 触发",
    "resolved": "✅ 已恢复",
}


def _build_feishu_card(payload: AlertmanagerPayload) -> dict:
    """将 Alertmanager payload 转换为飞书交互卡片"""
    status = payload.status
    severity = payload.commonLabels.get("severity", "warning")
    alertname = payload.groupLabels.get("alertname", "Unknown")

    emoji = SEVERITY_EMOJI.get(severity, "⚠️")
    color = SEVERITY_COLORS.get(severity, "orange")
    status_text = STATUS_TEXT.get(status, status)

    # 构建告警详情
    alert_elements = []
    for alert in payload.alerts:
        summary = alert.annotations.get("summary", "无摘要")
        description = alert.annotations.get("description", "")
        instance = alert.labels.get("instance", "")
        job = alert.labels.get("job", "")

        text_parts = [f"**{summary}**"]
        if description:
            text_parts.append(description)
        if instance:
            text_parts.append(f"实例: `{instance}`")
        if job:
            text_parts.append(f"任务: `{job}`")
        if alert.startsAt:
            text_parts.append(f"开始: {alert.startsAt[:19]}")

        alert_elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": "\n".join(text_parts)}
        })
        alert_elements.append({"tag": "hr"})

    # 移除最后一个分隔线
    if alert_elements and alert_elements[-1].get("tag") == "hr":
        alert_elements.pop()

    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"{emoji} [{severity.upper()}] {alertname} — {status_text}"},
                "template": color,
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": f"**状态**: {status_text}  |  **告警数**: {len(payload.alerts)}  |  **时间**: {datetime.now().strftime('%H:%M:%S')}"}
                },
                {"tag": "hr"},
                *alert_elements,
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": "玉珍健身 · Alertmanager · Prometheus"}]
                }
            ]
        }
    }


# ─── 路由 ────────────────────────────────────────────────────────────────────

@router.post("/alertmanager")
async def receive_alertmanager_webhook(payload: AlertmanagerPayload):
    """接收 Alertmanager 告警并转发到飞书"""
    if not FEISHU_WEBHOOK_URL:
        logger.warning("FEISHU_WEBHOOK_URL 未配置，告警仅记录日志")
        for alert in payload.alerts:
            severity = alert.labels.get("severity", "unknown")
            alertname = alert.labels.get("alertname", "unknown")
            summary = alert.annotations.get("summary", "")
            logger.info(f"[ALERT][{alert.status}][{severity}] {alertname}: {summary}")
        return {"status": "logged", "message": "FEISHU_WEBHOOK_URL not configured"}

    card = _build_feishu_card(payload)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(FEISHU_WEBHOOK_URL, json=card)
            resp.raise_for_status()
            logger.info(f"飞书告警发送成功: {payload.status} {len(payload.alerts)} alerts")
            return {"status": "sent", "feishu_response": resp.json()}
    except httpx.HTTPError as e:
        logger.error(f"飞书告警发送失败: {e}")
        return {"status": "error", "message": str(e)}
