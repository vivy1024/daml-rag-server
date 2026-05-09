# -*- coding: utf-8 -*-
"""
模型评估统计服务

⚠️ DEPRECATED (2026-05-09): 已被 yuzhen-eval 评测平台替代。
新系统使用独立评测平台（yuzhen-eval/）进行自动+人工评测。
旧的基于 Qdrant FewShot 库的评估逻辑已废弃。
待全量切换稳定后删除。

从 Qdrant Few-Shot 库中聚合各模型的评估数据，
提供按 backend_used 分组的统计分析。

多模型集成 - Task 9
"""

import logging
from typing import Dict, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class ModelEvaluationService:
    """模型评估统计服务"""

    def __init__(self, qdrant_client=None):
        self.qdrant_client = qdrant_client
        self._collection_name = "fitness_fewshot_pool"

    def _get_qdrant_client(self):
        if not self.qdrant_client:
            from ....framework.clients.qdrant_client import create_qdrant_client
            self.qdrant_client = create_qdrant_client()
        return self.qdrant_client

    async def get_model_stats(self, limit: int = 10000) -> Dict[str, Any]:
        """
        获取各模型的评估统计数据。

        从 Qdrant Few-Shot 库中读取所有带 backend_used 的记录，
        按模型分组统计准入率、平均评分等指标。
        """
        try:
            client = self._get_qdrant_client()

            # 滚动读取所有 fewshot_eligible 的记录
            points = []
            offset = None
            while True:
                result = client.scroll(
                    collection_name=self._collection_name,
                    limit=500,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                batch, next_offset = result
                points.extend(batch)
                if next_offset is None:
                    break
                offset = next_offset

            if not points:
                return {"models": {}, "total_fewshot_points": 0, "message": "暂无数据"}

            # 按 backend_used 分组统计
            model_data = defaultdict(lambda: {
                "total_fewshot": 0,
                "scores": [],
                "grades": defaultdict(int),
                "templates": defaultdict(int),
            })

            no_backend_count = 0
            for point in points:
                payload = point.payload or {}
                backend = payload.get("backend_used")
                if not backend:
                    no_backend_count += 1
                    backend = "unknown"

                data = model_data[backend]
                data["total_fewshot"] += 1

                score = payload.get("personalization_score")
                if score is not None:
                    data["scores"].append(score)

                grade = payload.get("personalization_grade")
                if grade:
                    data["grades"][grade] += 1

                template = payload.get("dag_template_id")
                if template:
                    data["templates"][template] += 1

            # 计算统计指标
            models = {}
            for backend, data in model_data.items():
                scores = data["scores"]
                avg_score = sum(scores) / len(scores) if scores else 0
                std_score = (
                    (sum((s - avg_score) ** 2 for s in scores) / len(scores)) ** 0.5
                    if len(scores) > 1 else 0
                )

                models[backend] = {
                    "total_fewshot": data["total_fewshot"],
                    "avg_personalization_score": round(avg_score, 2),
                    "score_std": round(std_score, 2),
                    "grade_distribution": dict(data["grades"]),
                    "template_distribution": dict(data["templates"]),
                }

            return {
                "total_fewshot_points": len(points),
                "points_without_backend": no_backend_count,
                "models": models,
            }

        except Exception as e:
            logger.error(f"获取模型评估统计失败: {e}")
            return {"error": str(e), "models": {}}
