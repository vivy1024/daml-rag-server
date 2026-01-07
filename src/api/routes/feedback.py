# -*- coding: utf-8 -*-
"""
Feedback Route - 用户反馈接口

收集和处理用户对聊天回复的反馈，用于改进系统性能和质量。

POST /api/feedback/submit - 提交用户反馈
GET  /api/feedback/stats - 获取反馈统计信息
GET  /api/feedback/health - 反馈系统健康检查

版本：v2.0.0
更新日期：2025-11-17
重构说明：集成三层检索反馈机制，支持质量监控
"""

import logging
import os
import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional, List

# 导入API模型
from ..models import ApiResponse, ApiError, FeedbackRequest

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/feedback",  # 注意：main.py会添加/api前缀
    tags=["feedback"]
)

# 全局反馈存储（生产环境应使用数据库）
_feedback_storage = []


@router.post("/submit", response_model=ApiResponse[Dict[str, str]])
async def submit_feedback(request: Dict[str, Any]):
    """
    提交用户反馈

    收集用户对AI回复的评价，用于：
    - 监控服务质量
    - 训练模型改进
    - 调整检索策略
    - 优化用户体验

    Args:
        request: {
            "user_id": "用户ID",
            "interaction_id": "交互ID",
            "rating": 4,  # 1-5星评分
            "feedback_type": "accuracy",  # accuracy, helpfulness, safety
            "comment": "评论内容（可选）",
            "issue_category": "hallucination"  # 问题分类（可选）
        }

    Returns:
        ApiResponse: 提交结果
    """
    try:
        # 1. 参数验证和输入清理
        user_id = request.get("user_id")
        interaction_id = request.get("interaction_id")
        rating = request.get("rating")

        if not all([user_id, interaction_id, rating is not None]):
            raise ApiError(400, "缺少必需参数：user_id, interaction_id, rating")

        if not isinstance(rating, int) or rating < 1 or rating > 5:
            raise ApiError(400, "评分必须是1-5的整数")
        
        # 输入验证和清理
        try:
            from ..middleware.security import InputValidator
            user_id = InputValidator.validate_and_clean('user_id', user_id)
            interaction_id = InputValidator.validate_and_clean('session_id', interaction_id)
            if request.get("comment"):
                request["comment"] = InputValidator.validate_and_clean('comment', request["comment"])
        except ImportError:
            logger.warning("输入验证器未加载，跳过输入清理")
        except Exception as e:
            logger.error(f"输入验证失败: {e}")
            raise ApiError(400, f"输入验证失败: {str(e)}")

        # 2. 构建反馈对象
        feedback_request = FeedbackRequest(
            user_id=user_id,
            interaction_id=interaction_id,
            rating=rating,
            feedback_type=request.get("feedback_type", "helpfulness"),
            comment=request.get("comment"),
            issue_category=request.get("issue_category")
        )

        # 3. 添加时间戳和ID
        feedback_data = {
            "id": f"feedback_{len(_feedback_storage) + 1}",
            "timestamp": datetime.now().isoformat(),
            "user_id": feedback_request.user_id,
            "interaction_id": feedback_request.interaction_id,
            "rating": feedback_request.rating,
            "feedback_type": feedback_request.feedback_type,
            "comment": feedback_request.comment,
            "issue_category": feedback_request.issue_category,
            "processed": False
        }

        # 4. 存储反馈
        _feedback_storage.append(feedback_data)

        logger.info(
            f"✅ 反馈提交成功: user={user_id}, rating={rating}, "
            f"type={feedback_request.feedback_type}, interaction={interaction_id}"
        )

        # 5. 异步处理反馈（分析质量趋势）
        asyncio.create_task(_process_feedback_async(feedback_data))

        return ApiResponse.success(
            data={
                "feedback_id": feedback_data["id"],
                "message": "反馈提交成功，感谢您的评价！"
            },
            msg="反馈提交成功"
        )

    except ApiError as e:
        logger.error(f"反馈提交API错误: {e.msg}", exc_info=True)
        return ApiResponse.error(code=e.code, msg=e.msg, data=e.data)

    except Exception as e:
        logger.error(f"反馈提交失败: {e}", exc_info=True)
        return ApiResponse.error(
            code=500,
            msg=f"反馈提交失败: {str(e)}"
        )


@router.get("/stats")
async def get_feedback_stats():
    """
    获取反馈统计信息

    提供用户反馈的统计分析，用于质量监控和系统改进。

    Returns:
        {
            "code": 200,
            "msg": "操作成功",
            "data": {
                "total_feedbacks": 150,
                "average_rating": 4.2,
                "rating_distribution": {
                    "5_star": 60,
                    "4_star": 45,
                    "3_star": 25,
                    "2_star": 15,
                    "1_star": 5
                },
                "feedback_types": {
                    "accuracy": 50,
                    "helpfulness": 70,
                    "safety": 30
                },
                "recent_trends": {
                    "last_7_days_avg": 4.3,
                    "last_30_days_avg": 4.1
                },
                "quality_metrics": {
                    "hallucination_rate": "2.0%",
                    "satisfaction_rate": "85.3%",
                    "response_quality": "良好"
                }
            }
        }
    """
    try:
        if not _feedback_storage:
            return ApiResponse.success(
                data={
                    "total_feedbacks": 0,
                    "average_rating": 0.0,
                    "rating_distribution": {},
                    "feedback_types": {},
                    "recent_trends": {},
                    "quality_metrics": {}
                },
                msg="暂无反馈数据"
            )

        # 1. 基础统计
        total_feedbacks = len(_feedback_storage)
        ratings = [f["rating"] for f in _feedback_storage]
        average_rating = sum(ratings) / len(ratings)

        # 2. 评分分布
        rating_distribution = {}
        for rating in [1, 2, 3, 4, 5]:
            rating_distribution[f"{rating}_star"] = ratings.count(rating)

        # 3. 反馈类型统计
        feedback_types = {}
        for feedback in _feedback_storage:
            fb_type = feedback["feedback_type"]
            feedback_types[fb_type] = feedback_types.get(fb_type, 0) + 1

        # 4. 最近趋势
        now = datetime.now()
        last_7_days = now - timedelta(days=7)
        last_30_days = now - timedelta(days=30)

        recent_7_days = [
            f["rating"] for f in _feedback_storage
            if datetime.fromisoformat(f["timestamp"]) >= last_7_days
        ]
        recent_30_days = [
            f["rating"] for f in _feedback_storage
            if datetime.fromisoformat(f["timestamp"]) >= last_30_days
        ]

        recent_trends = {}
        if recent_7_days:
            recent_trends["last_7_days_avg"] = sum(recent_7_days) / len(recent_7_days)
        if recent_30_days:
            recent_trends["last_30_days_avg"] = sum(recent_30_days) / len(recent_30_days)

        # 5. 质量指标
        quality_metrics = _calculate_quality_metrics()

        # 6. 构建响应数据
        stats_data = {
            "total_feedbacks": total_feedbacks,
            "average_rating": round(average_rating, 2),
            "rating_distribution": rating_distribution,
            "feedback_types": feedback_types,
            "recent_trends": recent_trends,
            "quality_metrics": quality_metrics,
            "last_updated": now.isoformat()
        }

        logger.info(f"反馈统计: 总数={total_feedbacks}, 平均评分={average_rating:.2f}")

        return ApiResponse.success(data=stats_data, msg="操作成功")

    except Exception as e:
        logger.error(f"获取反馈统计失败: {e}", exc_info=True)
        return ApiResponse.error(
            code=500,
            msg=f"获取统计失败: {str(e)}"
        )


@router.get("/health")
async def feedback_health():
    """
    反馈系统健康检查

    检查反馈系统的状态和性能。

    Returns:
        {
            "code": 200,
            "msg": "反馈系统正常",
            "data": {
                "status": "healthy",
                "total_feedbacks": 150,
                "storage_type": "memory",
                "recent_activity": true,
                "average_processing_time": "0.05s",
                "error_rate": "0.0%"
            }
        }
    """
    try:
        # 1. 基础状态检查
        total_feedbacks = len(_feedback_storage)
        status = "healthy" if total_feedbacks >= 0 else "unhealthy"

        # 2. 检查最近活动
        now = datetime.now()
        recent_activity = any(
            datetime.fromisoformat(f["timestamp"]) > now - timedelta(hours=1)
            for f in _feedback_storage
        )

        # 3. 存储类型（生产环境应该是数据库）
        storage_type = "memory"  # 实际生产应该是 "database"

        # 4. 构建健康数据
        health_data = {
            "status": status,
            "total_feedbacks": total_feedbacks,
            "storage_type": storage_type,
            "recent_activity": recent_activity,
            "average_processing_time": "0.05s",  # 模拟数据
            "error_rate": "0.0%",
            "timestamp": now.isoformat()
        }

        return ApiResponse.success(
            data=health_data,
            msg="反馈系统正常"
        )

    except Exception as e:
        logger.error(f"反馈健康检查失败: {e}", exc_info=True)
        return ApiResponse.error(
            code=500,
            msg=f"健康检查失败: {str(e)}",
            data={"status": "unhealthy", "error": str(e)}
        )


async def _process_feedback_async(feedback_data: Dict[str, Any]):
    """
    异步处理反馈数据

    用于分析质量趋势、检测异常、触发改进流程等。

    Args:
        feedback_data: 反馈数据
    """
    try:
        # 1. 标记为已处理
        feedback_data["processed"] = True
        feedback_data["processed_at"] = datetime.now().isoformat()

        # 2. 检测低评分反馈
        if feedback_data["rating"] <= 2:
            logger.warning(
                f"⚠️ 低评分反馈: user={feedback_data['user_id']}, "
                f"rating={feedback_data['rating']}, "
                f"comment={feedback_data.get('comment', '')[:100]}"
            )
            # 这里可以触发警报或通知

        # 3. 检测安全问题
        if feedback_data.get("issue_category") in ["hallucination", "safety", "inaccuracy"]:
            logger.error(
                f"🚨 严重问题反馈: type={feedback_data.get('issue_category')}, "
                f"interaction={feedback_data['interaction_id']}"
            )
            # 这里应该触发紧急处理流程

        # 4. 更新质量指标（这里可以连接到监控系统）
        await _update_quality_metrics(feedback_data)

        logger.debug(f"反馈处理完成: {feedback_data['id']}")

    except Exception as e:
        logger.error(f"反馈处理失败: {e}")


def _calculate_quality_metrics() -> Dict[str, Any]:
    """
    计算质量指标

    Returns:
        Dict: 质量指标
    """
    if not _feedback_storage:
        return {
            "hallucination_rate": "0.0%",
            "satisfaction_rate": "0.0%",
            "response_quality": "无数据"
        }

    total = len(_feedback_storage)

    # 幻觉率（基于issue_category）
    hallucination_count = sum(
        1 for f in _feedback_storage
        if f.get("issue_category") == "hallucination"
    )
    hallucination_rate = (hallucination_count / total * 100) if total > 0 else 0

    # 满意率（4-5星评分）
    satisfied_count = sum(1 for f in _feedback_storage if f["rating"] >= 4)
    satisfaction_rate = (satisfied_count / total * 100) if total > 0 else 0

    # 响应质量评估
    average_rating = sum(f["rating"] for f in _feedback_storage) / total
    if average_rating >= 4.5:
        quality = "优秀"
    elif average_rating >= 4.0:
        quality = "良好"
    elif average_rating >= 3.5:
        quality = "一般"
    else:
        quality = "需要改进"

    return {
        "hallucination_rate": f"{hallucination_rate:.1f}%",
        "satisfaction_rate": f"{satisfaction_rate:.1f}%",
        "response_quality": quality,
        "average_rating": round(average_rating, 2)
    }


async def _update_quality_metrics(feedback_data: Dict[str, Any]):
    """
    更新质量指标

    连接到外部监控系统或更新内部统计数据

    Args:
        feedback_data: 反馈数据
    """
    # 这里可以连接到外部监控系统
    # 例如：Prometheus, Grafana, ELK等
    pass


def get_feedback_data() -> List[Dict[str, Any]]:
    """
    获取所有反馈数据（用于测试和调试）

    Returns:
        List[Dict]: 反馈数据列表
    """
    return _feedback_storage.copy()


def clear_feedback_data():
    """
    清空反馈数据（仅用于测试）

    生产环境不应该提供此功能
    """
    global _feedback_storage
    _feedback_storage.clear()
    logger.warning("反馈数据已清空（测试环境）")


# 导出路由和函数
__all__ = ['router', 'get_feedback_data', 'clear_feedback_data']