# -*- coding: utf-8 -*-
"""
模型评估统计 API

内部端点，提供各 LLM 后端在健身垂直领域的评估统计数据。
数据来源：Qdrant Few-Shot 库中带 backend_used 标签的记录。

GET /api/internal/model-evaluation/stats

多模型集成 - Task 9
"""

import logging
import os
from fastapi import APIRouter, HTTPException, Request
from src.api.models.api_response import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/model-evaluation", tags=["ModelEvaluation"])


def _verify_internal_request(request: Request) -> bool:
    """验证内部请求（127.0.0.1 或 Bearer Token）"""
    client_ip = request.client.host if request.client else ""
    if client_ip in ("127.0.0.1", "::1"):
        return True

    auth = request.headers.get("Authorization", "")
    expected = os.getenv("INTERNAL_API_TOKEN", "")
    if expected and auth == f"Bearer {expected}":
        return True

    return False


@router.get("/stats")
async def get_model_evaluation_stats(request: Request):
    """
    获取各模型的评估统计数据。

    返回每个 LLM 后端的 Few-Shot 准入数、平均个性化评分、
    等级分布、模板分布等指标。
    """
    if not _verify_internal_request(request):
        raise HTTPException(status_code=401, detail="Internal access only")

    try:
        from src.applications.fitness.services.model_evaluation import ModelEvaluationService
        service = ModelEvaluationService()
        stats = await service.get_model_stats()
        return ApiResponse.success(data=stats, msg="模型评估统计")
    except Exception as e:
        logger.error(f"获取模型评估统计失败: {e}")
        return ApiResponse.error(msg=f"获取失败: {str(e)}")
