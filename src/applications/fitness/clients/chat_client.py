# -*- coding: utf-8 -*-
"""ChatMixin — 对话记录相关 API"""

import httpx
import logging
from typing import Dict, Any, Optional, List

from .models import BackendAPIError

logger = logging.getLogger(__name__)


class ChatMixin:
    """对话记录 API 方法集"""

    async def save_chat_session(
        self, session_id: str, user_id: Optional[int], user_query: str,
        llm_response: str, model_used: str, tools_used: List[str],
        metadata: Dict[str, Any], qdrant_point_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """保存对话记录到MySQL数据库"""
        endpoint = "/api/internal/chat/save-session"
        data = await self._request(
            "POST", endpoint,
            json={
                'session_id': session_id, 'user_id': user_id,
                'user_query': user_query, 'llm_response': llm_response,
                'model_used': model_used, 'tools_used': tools_used,
                'metadata': metadata, 'qdrant_point_id': qdrant_point_id,
            }
        )
        return data

    async def update_chat_feedback(
        self, session_id: str, reward: float, feedback_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """更新对话反馈（用户评分）"""
        endpoint = "/api/internal/chat/update-feedback"
        data = await self._request(
            "POST", endpoint,
            json={'session_id': session_id, 'reward': reward, 'feedback_text': feedback_text}
        )
        return data

    async def search_similar_conversations(
        self, query: str, user_id: Optional[int] = None, limit: int = 10,
        min_rating: float = 4.0, only_fewshot_eligible: bool = True,
        training_effect_filter: Optional[str] = None, days_back: int = 90
    ) -> Dict[str, Any]:
        """搜索相似的历史对话（Few-Shot降级策略）"""
        try:
            client = self._get_client()

            payload = {
                "query": query, "limit": limit,
                "min_rating": min_rating, "only_fewshot_eligible": only_fewshot_eligible
            }
            if user_id is not None:
                payload["user_id"] = user_id
            if training_effect_filter is not None:
                payload["training_effect_filter"] = training_effect_filter

            response = await client.post("/api/internal/chat/search-similar", json=payload)
            response.raise_for_status()

            data = response.json()

            if data.get("code") == 200:
                result_data = data.get("data", {})
                conversations = result_data.get("conversations", [])
            else:
                conversations = []
                result_data = {}
                logger.warning(f"Search similar conversations returned non-200: {data.get('msg')}")

            logger.info(
                f"Similar conversations search completed: query='{query[:50]}...', "
                f"results={len(conversations)}, method={result_data.get('search_method', 'unknown')}",
                extra={
                    'query': query[:100], 'user_id': user_id,
                    'result_count': len(conversations),
                    'only_fewshot_eligible': only_fewshot_eligible
                }
            )

            return {
                "conversations": conversations,
                "total": len(conversations),
                "search_method": result_data.get("search_method", "keyword_fallback"),
                "filters_applied": result_data.get("filters_applied", {})
            }

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("Similar conversations search API not found (404)")
                return {"conversations": [], "total": 0, "search_method": "error"}
            else:
                logger.error(f"HTTP error in similar conversations search: {e}")
                raise BackendAPIError(f"相似对话搜索失败: {e.response.status_code}")

        except (BackendAPIError, httpx.HTTPError, ConnectionError, TimeoutError) as e:
            logger.error(f"Similar conversations search failed: {e}")
            raise BackendAPIError(f"相似对话搜索连接失败: {str(e)}")

    async def submit_three_track_rating(
        self, session_id: str, personalization_scores: Dict[str, float],
        personalization_grade: str, fewshot_eligible: bool,
        eligibility_reason: str, overall_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """提交三轨评分"""
        endpoint = "/api/internal/chat/update-personalization"
        try:
            data = await self._request(
                "POST", endpoint,
                json={
                    'session_id': session_id,
                    'profile_utilization_rate': personalization_scores.get('profile_utilization_rate', 0),
                    'goal_alignment': personalization_scores.get('goal_alignment', 0),
                    'uniqueness': personalization_scores.get('uniqueness', 0),
                    'dynamic_adjustment': personalization_scores.get('dynamic_adjustment', 0),
                    'personalization_grade': personalization_grade,
                    'fewshot_eligible': fewshot_eligible,
                    'overall_score': overall_score,
                    'eligibility_reason': eligibility_reason
                }
            )
            logger.info(
                f"三轨评分提交成功: session_id={session_id}, "
                f"grade={personalization_grade}, eligible={fewshot_eligible}",
                extra={
                    'session_id': session_id,
                    'personalization_grade': personalization_grade,
                    'fewshot_eligible': fewshot_eligible
                }
            )
            return data
        except Exception as e:
            logger.error(f"三轨评分提交失败: session_id={session_id}, error={e}")
            return {'success': False, 'error': str(e)}

    async def get_user_session_count(self, user_id: int) -> int:
        """获取用户会话数量（用于冷启动判断）"""
        endpoint = f"/api/internal/chat/session-count/{user_id}"
        try:
            data = await self._request("GET", endpoint)
            return data.get('count', 0)
        except Exception as e:
            logger.warning(f"获取用户会话数量失败: user_id={user_id}, error={e}")
            return 0

    async def check_fewshot_eligibility(self, session_id: str) -> Dict[str, Any]:
        """检查会话Few-Shot资格"""
        endpoint = f"/api/internal/chat/fewshot-eligibility/{session_id}"
        try:
            data = await self._request("GET", endpoint)
            return data
        except Exception as e:
            logger.warning(f"检查Few-Shot资格失败: session_id={session_id}, error={e}")
            return {'eligible': False, 'reason': str(e)}

    async def save_conversation_message(
        self, user_id: str, topic_id: str,
        message: Dict[str, Any], session_id: str = None
    ) -> Dict[str, Any]:
        """保存对话消息到后端"""
        endpoint = "/api/internal/chat/save-message"
        try:
            request_data = {
                'user_id': user_id, 'topic_id': topic_id,
                'role': message.get('role', 'user'),
                'content': message.get('content', ''),
            }
            if session_id:
                request_data['session_id'] = session_id
            elif message.get('session_id'):
                request_data['session_id'] = message.get('session_id')

            data = await self._request("POST", endpoint, json=request_data)
            logger.debug(
                f"对话消息保存成功: user_id={user_id}, topic_id={topic_id}",
                extra={'user_id': user_id, 'topic_id': topic_id}
            )
            return data
        except Exception as e:
            logger.warning(f"对话消息保存失败: user_id={user_id}, topic_id={topic_id}, error={e}")
            return {'success': False, 'error': str(e)}

    async def save_conversation_topic(self, user_id: str, topic: Dict[str, Any]) -> Dict[str, Any]:
        """保存对话话题到后端"""
        endpoint = "/api/internal/chat/save-topic"
        try:
            data = await self._request("POST", endpoint, json={'user_id': user_id, 'topic': topic})
            logger.debug(
                f"对话话题保存成功: user_id={user_id}, topic_id={topic.get('topic_id')}",
                extra={'user_id': user_id, 'topic_id': topic.get('topic_id')}
            )
            return data
        except Exception as e:
            logger.warning(f"对话话题保存失败: user_id={user_id}, error={e}")
            return {'success': False, 'error': str(e)}

    async def clear_conversation_topic(self, user_id: str, topic_id: str) -> Dict[str, Any]:
        """从后端清除对话话题"""
        endpoint = f"/api/internal/chat/clear-topic/{topic_id}"
        try:
            data = await self._request("DELETE", endpoint, params={'user_id': user_id})
            logger.debug(
                f"对话话题清除成功: user_id={user_id}, topic_id={topic_id}",
                extra={'user_id': user_id, 'topic_id': topic_id}
            )
            return data
        except Exception as e:
            logger.warning(f"对话话题清除失败: user_id={user_id}, topic_id={topic_id}, error={e}")
            return {'success': False, 'error': str(e)}
