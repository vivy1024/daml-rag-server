# -*- coding: utf-8 -*-
"""
PermissionMixin: 权限检查 + 三轨评分 + 辅助方法

从 StreamWorkflowExecutor 提取的权限与评分相关方法。

版本: v1.0.0
日期: 2026-03-05
"""

import logging
import httpx
from typing import Any, Dict, Optional

from .state import WorkflowState

logger = logging.getLogger(__name__)


class PermissionMixin:
    """
    权限检查与评分 Mixin

    提供权限控制和后处理能力：
    - _check_permission_before_execute(): 执行前权限检查
    - _execute_step_12_three_track_rating(): 三轨评分
    - _make_json_serializable(): JSON序列化辅助
    - _increment_usage_after_execute(): 用量计数
    - _report_credit_consumption(): 积分上报
    """

    async def _check_permission_before_execute(
        self,
        user_id: str,
        strategy: str,
        request_id: str
    ) -> Dict[str, Any]:
        """
        执行前检查权限

        Requirements: 7.1, 7.2, 7.3

        Args:
            user_id: 用户ID
            strategy: 执行策略（dag或agent）
            request_id: 请求ID

        Returns:
            Dict[str, Any]: 权限检查结果
        """
        try:
            # 获取权限检查器
            from ....framework.auth.permission_checker import get_permission_checker
            permission_checker = get_permission_checker()

            # 如果权限检查器没有后端客户端，尝试设置
            if permission_checker.backend_client is None:
                backend_client = self._get_backend_client()
                if backend_client:
                    permission_checker.backend_client = backend_client

            # 检查权限
            result = await permission_checker.check_permission(
                user_id=int(user_id) if user_id.isdigit() else 0,
                mode=strategy
            )

            if result.allowed:
                logger.info(
                    f"✅ [{request_id}] 权限检查通过: "
                    f"user_id={user_id}, tier={result.tier}, "
                    f"remaining={result.remaining}"
                )
                return {
                    "allowed": True,
                    "tier": result.tier,
                    "remaining": result.remaining,
                    "message": result.message
                }
            else:
                logger.warning(
                    f"⚠️ [{request_id}] 权限检查失败: "
                    f"user_id={user_id}, message={result.message}"
                )
                return {
                    "allowed": False,
                    "tier": result.tier,
                    "remaining": result.remaining,
                    "message": result.message,
                    "upgrade_hint": result.upgrade_hint
                }

        except (ImportError, httpx.HTTPError, ConnectionError, TimeoutError, ValueError) as e:
            logger.error(f"❌ [{request_id}] 权限检查异常(fail-closed拒绝): {e}")
            return {
                "allowed": False,
                "tier": "unknown",
                "remaining": 0,
                "message": "系统繁忙，请稍后重试"
            }

    async def _execute_step_12_three_track_rating(self, state: WorkflowState) -> WorkflowState:
        """
        执行步骤12：三轨评分

        在LLM翻译完成后执行：
        1. 自动计算个性化感知评分
        2. 检查Few-Shot准入资格
        3. 高评分对话自动导入Few-Shot库

        Requirements: 3.7, 3.8
        """
        request_id = state.get("request_id", "unknown")
        session_id = state.get("session_id")
        user_id = state.get("user_id")
        user_query = state.get("query_text", "")
        final_response = state.get("final_response", "")
        user_profile = state.get("user_profile")
        tools_used = state.get("_mcp_tools_called", [])

        try:
            logger.info(f"🎯 [{request_id}] 步骤12: 开始三轨评分")

            # 导入三轨评分服务
            from ..services.three_track_rating import ThreeTrackRatingService

            # 获取后端客户端和Qdrant客户端
            backend_client = self._get_backend_client()
            qdrant_client = self._get_qdrant_client()

            # 创建三轨评分服务
            rating_service = ThreeTrackRatingService(
                backend_client=backend_client,
                qdrant_client=qdrant_client
            )

            # 构建元数据
            metadata = {
                'dag_template_id': state.get("dag_template_id"),
                'complexity_level': state.get("complexity_level"),
                'few_shot_count': len(state.get("few_shot_examples", [])),
                'context_used': state.get("context_used", False),
                'conversation_turn': state.get("conversation_turn", 1),
                'backend_used': state.get("backend_used"),
            }

            # 处理三轨评分
            rating_result = await rating_service.process_rating(
                session_id=session_id or request_id,
                user_id=str(user_id) if user_id else "anonymous",
                user_query=user_query,
                llm_response=final_response,
                user_profile=user_profile,
                tools_used=tools_used,
                metadata=metadata
            )

            # 将评分结果存入状态
            state["three_track_rating"] = rating_result.to_dict()
            state["personalization_grade"] = rating_result.personalization_grade.value
            state["fewshot_eligible"] = rating_result.fewshot_eligible

            # 如果有后端客户端，提交评分到后端
            if backend_client and session_id:
                try:
                    await backend_client.submit_three_track_rating(
                        session_id=session_id,
                        personalization_scores=rating_result.personalization.to_dict(),
                        personalization_grade=rating_result.personalization_grade.value,
                        fewshot_eligible=rating_result.fewshot_eligible,
                        eligibility_reason=rating_result.eligibility_reason,
                        overall_score=rating_result.overall_score
                    )
                except (httpx.HTTPError, ConnectionError, TimeoutError) as e:
                    logger.warning(f"[{request_id}] 提交三轨评分到后端失败: {e}")

            logger.info(
                f"✅ [{request_id}] 步骤12完成: "
                f"grade={rating_result.personalization_grade.value}, "
                f"eligible={rating_result.fewshot_eligible}"
            )

        except (ImportError, ValueError, RuntimeError, ConnectionError, TimeoutError) as e:
            logger.error(f"❌ [{request_id}] 步骤12: 三轨评分异常: {e}")
            # 不影响主流程，记录错误但继续
            state["three_track_rating"] = {
                'error': str(e),
                'fewshot_eligible': False
            }

        return state

    def _get_qdrant_client(self):
        """获取Qdrant客户端（懒加载）"""
        try:
            from ....framework.clients.qdrant_client import get_qdrant_client
            return get_qdrant_client()
        except (ImportError, ConnectionError) as e:
            logger.warning(f"获取Qdrant客户端失败: {e}")
            return None

    def _make_json_serializable(self, obj: Any) -> Any:
        """
        将对象转换为JSON可序列化格式

        处理特殊对象类型（如MembershipPermissions、dataclass等）

        Args:
            obj: 要转换的对象

        Returns:
            JSON可序列化的对象
        """
        # 基本类型直接返回
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj

        # 列表递归处理
        if isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]

        # 字典递归处理
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}

        # 有to_dict方法的对象（如MembershipPermissions、UserProfile等）
        if hasattr(obj, 'to_dict') and callable(getattr(obj, 'to_dict')):
            return obj.to_dict()

        # 有__dict__属性的对象
        if hasattr(obj, '__dict__'):
            return {k: self._make_json_serializable(v) for k, v in obj.__dict__.items() if not k.startswith('_')}

        # 其他情况转为字符串
        return str(obj)

    async def _increment_usage_after_execute(
        self,
        user_id: str,
        strategy: str,
        request_id: str
    ) -> bool:
        """
        执行后增加用量计数

        Requirements: 7.4

        Args:
            user_id: 用户ID
            strategy: 执行策略（dag或agent）
            request_id: 请求ID

        Returns:
            bool: 是否成功
        """
        try:
            # 获取权限检查器
            from ....framework.auth.permission_checker import get_permission_checker
            permission_checker = get_permission_checker()

            # 如果权限检查器没有后端客户端，尝试设置
            if permission_checker.backend_client is None:
                backend_client = self._get_backend_client()
                if backend_client:
                    permission_checker.backend_client = backend_client

            # 增加用量
            success = await permission_checker.increment_usage(
                user_id=int(user_id) if user_id.isdigit() else 0,
                mode=strategy
            )

            if success:
                logger.info(
                    f"✅ [{request_id}] 用量增加成功: "
                    f"user_id={user_id}, mode={strategy}"
                )
            else:
                logger.warning(
                    f"⚠️ [{request_id}] 用量增加失败: "
                    f"user_id={user_id}, mode={strategy}"
                )

            return success

        except (ImportError, httpx.HTTPError, ConnectionError, TimeoutError, ValueError) as e:
            logger.error(f"❌ [{request_id}] 用量增加异常: {e}")
            return False

    async def _report_credit_consumption(
        self,
        user_id: str,
        tokens_generated: int,
        mode: str,
        template_name: Optional[str] = None,
        conversation_id: Optional[str] = None,
        request_id: str = "unknown",
        # 性能监控字段
        ttfb_ms: int = 0,
        duration_ms: int = 0,
        backend_used: str = "unknown",
        fallback_count: int = 0,
        error_type: str = "",
    ) -> bool:
        """
        上报积分消耗到后端

        Requirements: 10.1

        在DAG工作流完成后调用，将Token消耗上报到后端进行积分扣除。
        使用try-except确保不阻塞主响应流程。

        Args:
            user_id: 用户ID
            tokens_generated: 生成的Token数量（作为总Token消耗的估算）
            mode: 执行模式（dag或agent）
            template_name: DAG模板名称
            conversation_id: 会话ID
            request_id: 请求ID（用于日志）

        Returns:
            bool: 是否成功
        """
        try:
            # 导入积分上报服务
            from ..services.credit_reporter import report_credit_consumption

            # 估算Token消耗（输出Token通常是主要消耗）
            # 实际项目中可以从LLM响应中获取精确的Token统计
            # 这里使用生成的Token数作为输出Token的估算
            # 输入Token估算为输出Token的0.3倍（经验值）
            output_tokens = tokens_generated
            input_tokens = int(tokens_generated * 0.3)
            total_tokens = input_tokens + output_tokens

            # 上报积分消耗
            result = await report_credit_consumption(
                user_id=int(user_id) if user_id.isdigit() else 0,
                tokens=total_tokens,
                mode=mode,
                template_name=template_name,
                conversation_id=conversation_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                backend_used=backend_used,
                ttfb_ms=ttfb_ms,
                duration_ms=duration_ms,
                tokens_per_sec=output_tokens / max(duration_ms / 1000, 0.1) if duration_ms > 0 else 0.0,
                fallback_count=fallback_count,
                error_type=error_type,
            )

            if result.get("success"):
                credits = result.get("credits", 0)
                logger.info(
                    f"💰 [{request_id}] 积分上报成功: "
                    f"user_id={user_id}, credits={credits}, "
                    f"tokens={total_tokens}, mode={mode}, "
                    f"template={template_name}"
                )
                return True
            else:
                error = result.get("error", "未知错误")
                logger.warning(
                    f"⚠️ [{request_id}] 积分上报失败: "
                    f"user_id={user_id}, error={error}"
                )
                return False

        except (ImportError, httpx.HTTPError, ConnectionError, TimeoutError, ValueError) as e:
            # 积分上报失败不应阻塞主流程
            logger.error(
                f"❌ [{request_id}] 积分上报异常: {e}",
                exc_info=True
            )
            return False
