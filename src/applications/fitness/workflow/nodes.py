# -*- coding: utf-8 -*-
"""
工作流节点函数模块

每个节点是一个纯函数：接收状态，返回状态更新。
参考 LangGraph 的节点设计，确保函数不直接修改输入状态。

版本: v1.1.0
日期: 2025-12-29

节点列表:
- node_preload_user_profile: 步骤1 - 预加载用户档案
- node_store_session: 步骤2 - 会话记录存储
- node_check_membership: 步骤3 - 检查会员权限
- node_classify_complexity: 步骤4 - BGE复杂度分类
- node_select_model: 步骤5 - 智能模型选择
- node_retrieve_few_shot: 步骤6 - Few-Shot检索
- node_select_dag_template: 步骤6.5 - LLM选择DAG模板
- node_execute_dag: 步骤7 - DAG编排执行
- node_retrieve_context: 步骤8 - 三层检索
- node_aggregate_data: 步骤9 - 工具结果汇总
- node_llm_analysis: 步骤10 - LLM生成回答
- node_log_interaction: 步骤11 - 记录交互

更新记录:
- v1.1.0 (2025-12-29): 集成智能预热器，步骤1完成后异步预热步骤3数据 (Requirements 3.1, 3.2, 3.3)
"""

import logging
import time
import hashlib
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple

from .state import WorkflowState, StateUpdate, WorkflowStep

logger = logging.getLogger(__name__)


# ============ 步骤1：预加载用户档案 ============

async def node_preload_user_profile(
    state: WorkflowState,
    backend_client=None,
    cache_manager=None,
    user_cache=None,
    performance_monitor=None,
    perf_context=None,
    smart_preloader=None  # 新增：智能预热器 (Requirements 3.1, 3.2)
) -> StateUpdate:
    """
    步骤1：预加载用户档案（混合方案：缓存优先 + MCP工具降级）
    
    新增功能 (Requirements 3.1, 3.2, 3.3):
    - 用户档案加载完成后，异步预热步骤3需要的会员数据
    - 预热不阻塞主工作流执行
    
    Args:
        state: 当前工作流状态
        backend_client: 后端客户端（可选）
        cache_manager: 缓存管理器（可选）
        user_cache: 用户缓存（可选）
        performance_monitor: 性能监控器（可选）
        perf_context: 性能上下文（可选）
        smart_preloader: 智能预热器（可选）(Requirements 3.1)
        
    Returns:
        StateUpdate: 状态更新，包含 user_profile
    """
    request_id = state.get("request_id", "unknown")
    user_id = state.get("user_id")
    
    user_profile = state.get("user_profile")  # 可能已预先提供
    
    if user_profile:
        logger.info(f"✅ [{request_id}] 步骤1完成: 使用已提供的用户档案")
        # 即使使用已提供的档案，也触发步骤3预热 (Requirements 3.1)
        await _trigger_step3_preload(user_id, smart_preloader, request_id)
        return StateUpdate(updates={"user_profile": user_profile})
    
    if not user_id:
        logger.info(f"✅ [{request_id}] 步骤1完成: 无用户ID，跳过档案加载")
        return StateUpdate(updates={"user_profile": None})
    
    try:
        # 健壮的user_id转换逻辑
        if isinstance(user_id, int):
            user_id_int = user_id
        elif isinstance(user_id, str) and user_id.isdigit():
            user_id_int = int(user_id)
        else:
            logger.warning(f"⚠️ [{request_id}] 无效的user_id: {user_id}")
            return StateUpdate(
                updates={"user_profile": None},
                warning=f"无效的user_id: {user_id}"
            )
        
        # 主路径：使用缓存管理器获取用户档案
        if cache_manager:
            cache_key = f"user_profile:{user_id_int}"
            
            async def fetch_user_profile():
                """从数据库获取用户档案"""
                if user_cache:
                    return await user_cache.get_user_profile(str(user_id_int))
                elif backend_client:
                    return await backend_client.get_user_profile(user_id_int)
                return None
            
            # 使用缓存管理器获取
            user_profile = await cache_manager.get(
                key=cache_key,
                fetch_func=fetch_user_profile,
                ttl=300  # 5分钟TTL
            )
            
            if user_profile:
                logger.info(f"✅ [{request_id}] 步骤1完成: 用户档案已加载（缓存管理器）")
            else:
                logger.warning(f"⚠️ [{request_id}] 步骤1: 缓存管理器返回空档案")
        
        # 降级路径：直接使用用户缓存
        elif user_cache:
            user_profile = await user_cache.get_user_profile(str(user_id_int))
            if user_profile:
                logger.info(f"✅ [{request_id}] 步骤1完成: 用户档案已加载（用户缓存）")
        
        # 最后降级：直接调用后端
        elif backend_client:
            user_profile = await backend_client.get_user_profile(user_id_int)
            if user_profile:
                logger.info(f"✅ [{request_id}] 步骤1完成: 用户档案已加载（后端API）")
        
        if not user_profile:
            logger.info(f"✅ [{request_id}] 步骤1完成: 用户档案未找到，继续匿名模式")
        
        # ✅ 步骤1完成后，异步预热步骤3需要的会员数据 (Requirements 3.1, 3.2)
        await _trigger_step3_preload(user_id, smart_preloader, request_id)
        
        return StateUpdate(updates={"user_profile": user_profile})
        
    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤1: 用户档案加载失败: {e}")
        return StateUpdate(
            updates={"user_profile": None},
            warning=f"用户档案加载失败: {str(e)}"
        )


async def _trigger_step3_preload(
    user_id: Any,
    smart_preloader,
    request_id: str
):
    """
    触发步骤3预热（内部辅助函数）
    
    在步骤1完成后调用，异步预热步骤3需要的会员数据。
    此函数不阻塞主工作流执行。
    
    Args:
        user_id: 用户ID
        smart_preloader: 智能预热器实例
        request_id: 请求ID（用于日志）
    
    Requirements:
        - 3.1: WHEN step 1 completes, THE DAML_RAG_System SHALL async preload membership data
        - 3.2: THE async preload SHALL NOT block the main workflow execution
    """
    if not user_id:
        return

    # 尝试获取预热器（如果未传入）
    if smart_preloader is None:
        try:
            # 使用预热系统
            from ....framework.storage.warmup import get_warmup_manager
            warmup_manager = get_warmup_manager()
            if warmup_manager:
                # 转换user_id为字符串
                user_id_str = str(user_id)
                
                # 异步预热会员数据（非阻塞）
                try:
                    await warmup_manager.preload_memberships([user_id_str])
                    logger.debug(
                        f"🚀 [{request_id}] 步骤1→步骤3预热已启动: user_id={user_id_str}"
                    )
                except Exception as e:
                    logger.warning(
                        f"⚠️ [{request_id}] 步骤3预热启动失败（不影响主流程）: {e}"
                    )
        except ImportError:
            pass
        except Exception as e:
            # 预热失败不影响主工作流
            logger.warning(
                f"⚠️ [{request_id}] 步骤3预热启动失败（不影响主流程）: {e}"
            )

# ============ 步骤2：会话记录存储 + 加载对话历史 ============

async def node_store_session(
    state: WorkflowState,
    conversation_memory=None,
) -> StateUpdate:
    """
    步骤2：会话记录存储 + 加载对话历史

    新增功能：
    - 从 ConversationMemory 加载对话历史（Redis → 内存 → 后端）
    - 将历史格式化为 LLM 可用格式存入 state

    Args:
        state: 当前工作流状态
        conversation_memory: ConversationMemory 实例（可选）

    Returns:
        StateUpdate: 状态更新，包含 session_id, conversation_history, conversation_topic_id
    """
    request_id = state.get("request_id", "unknown")
    user_id = state.get("user_id", "anonymous")
    session_id = state.get("session_id")
    topic_id = state.get("conversation_topic_id")

    if not session_id:
        session_id = f"session_{user_id}_{int(time.time())}"

    # 加载对话历史
    conversation_history = []
    active_topic_id = topic_id

    if conversation_memory and user_id != "anonymous":
        try:
            # 如果指定了 topic_id，切换到该话题
            if topic_id:
                await conversation_memory.switch_topic(
                    user_id, topic_id, create_if_not_exists=True
                )
            else:
                active_topic_id = conversation_memory.get_active_topic_id(user_id)

            messages = await conversation_memory.get_history(
                user_id=user_id,
                topic_id=active_topic_id,
            )
            if messages:
                conversation_history = conversation_memory.format_history_for_llm(messages)
                logger.info(
                    f"✅ [{request_id}] 步骤2: 加载对话历史 {len(conversation_history)} 条, "
                    f"topic={active_topic_id}"
                )
        except Exception as e:
            logger.warning(f"⚠️ [{request_id}] 步骤2: 加载对话历史失败（不影响主流程）: {e}")

    logger.info(f"✅ [{request_id}] 步骤2完成: 会话ID={session_id[:16]}...")

    return StateUpdate(updates={
        "session_id": session_id,
        "conversation_history": conversation_history,
        "conversation_topic_id": active_topic_id,
    })


# ============ 步骤3：检查会员权限 ============

async def node_check_membership(
    state: WorkflowState,
    backend_client=None,
    cache_manager=None,
    membership_cache=None,
    smart_preloader=None  # 新增：智能预热器（用于追踪预热效果）(Requirements 3.3)
) -> StateUpdate:
    """
    步骤3：检查会员权限（带完整错误处理 + 缓存管理器集成）
    
    新增功能 (Requirements 3.3):
    - 记录预热缓存命中，用于追踪预热效果
    
    Args:
        state: 当前工作流状态
        backend_client: 后端客户端（可选）
        cache_manager: 缓存管理器（可选）
        membership_cache: 会员缓存（可选）
        smart_preloader: 智能预热器（可选，用于追踪预热效果）
        
    Returns:
        StateUpdate: 状态更新，包含 membership_info 和 is_premium
    """
    request_id = state.get("request_id", "unknown")
    user_id = state.get("user_id")
    
    if not user_id:
        logger.info(f"✅ [{request_id}] 步骤3完成: 匿名用户")
        return StateUpdate(updates={
            "membership_info": None,
            "is_premium": False
        })
    
    try:
        # 健壮的user_id转换
        if isinstance(user_id, int):
            user_id_int = user_id
        elif isinstance(user_id, str) and user_id.isdigit():
            user_id_int = int(user_id)
        else:
            logger.info(f"✅ [{request_id}] 步骤3完成: 无效user_id，匿名模式")
            return StateUpdate(updates={
                "membership_info": None,
                "is_premium": False
            })
        
        membership = None
        cache_hit = False  # 追踪是否缓存命中
        
        # 主路径：使用缓存管理器
        if cache_manager:
            cache_key = f"user_membership:{user_id_int}"
            
            async def fetch_membership():
                if membership_cache:
                    return await membership_cache.get_user_membership(str(user_id_int))
                return None
            
            membership = await cache_manager.get(
                key=cache_key,
                fetch_func=fetch_membership,
                ttl=600  # 10分钟TTL
            )
            
            # 检查是否是缓存命中（通过缓存管理器的统计）
            if membership and hasattr(cache_manager, 'stats'):
                cache_hit = True
        
        # 降级路径：直接使用会员缓存
        elif membership_cache:
            membership = await membership_cache.get_user_membership(str(user_id_int))
            cache_hit = membership is not None
        
        # ✅ 记录预热缓存命中（用于追踪预热效果）(Requirements 3.3)
        if cache_hit:
            await _record_preload_cache_hit(str(user_id_int), smart_preloader, request_id)
        
        if membership:
            tier = membership.get('tier', 'free')
            is_fallback = membership.get('_fallback', False)
            is_premium = tier != 'free'
            
            if is_fallback:
                logger.info(f"✅ [{request_id}] 步骤3完成: 会员等级={tier}（降级）")
            else:
                logger.info(f"✅ [{request_id}] 步骤3完成: 会员等级={tier}")
            
            return StateUpdate(updates={
                "membership_info": membership,
                "is_premium": is_premium
            })
        else:
            logger.info(f"✅ [{request_id}] 步骤3完成: 会员信息未找到")
            return StateUpdate(updates={
                "membership_info": None,
                "is_premium": False
            })
            
    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤3: 会员权限检查失败: {e}")
        return StateUpdate(
            updates={
                "membership_info": None,
                "is_premium": False
            },
            warning=f"会员权限检查失败: {str(e)}"
        )


async def _record_preload_cache_hit(
    user_id: str,
    smart_preloader,
    request_id: str
):
    """
    记录预热缓存命中（内部辅助函数）
    
    用于追踪步骤1预热步骤3的效果。
    
    Args:
        user_id: 用户ID
        smart_preloader: 智能预热器实例
        request_id: 请求ID（用于日志）
    
    Requirements:
        - 3.3: WHEN step 3 executes, THE Membership_Cache SHALL find data already in cache
    """
    # 尝试获取预热器（如果未传入）
    if smart_preloader is None:
        try:
            # 预热系统暂时没有record_cache_hit方法，跳过追踪
            logger.debug(
                f"📊 [{request_id}] 步骤3预热效果追踪（暂不支持）: user_id={user_id}"
            )
        except ImportError:
            pass
        except Exception as e:
            # 追踪失败不影响主工作流
            logger.debug(f"⚠️ [{request_id}] 预热效果追踪失败: {e}")


# ============ 步骤4：BGE复杂度分类 ============

async def node_classify_complexity(
    state: WorkflowState,
    classifier=None,
    cache_manager=None
) -> StateUpdate:
    """
    步骤4：BGE复杂度分类（带完整错误处理 + 缓存管理器集成）
    
    注意：当DUAL_MODEL_ENABLED=false时，此步骤会快速跳过
    
    Args:
        state: 当前工作流状态
        classifier: 复杂度分类器（可选）
        cache_manager: 缓存管理器（可选）
        
    Returns:
        StateUpdate: 状态更新，包含 complexity_level
    """
    import os
    request_id = state.get("request_id", "unknown")
    query_text = state.get("query_text", "")
    
    # ✅ 检查是否启用双模型选择，如果禁用则快速跳过
    dual_model_enabled = os.getenv("DUAL_MODEL_ENABLED", "false").lower() == "true"
    if not dual_model_enabled:
        logger.info(f"✅ [{request_id}] 步骤4跳过: 双模型选择已禁用，直接使用DeepSeek")
        return StateUpdate(updates={
            "complexity_level": "complex",  # 默认复杂，使用DeepSeek
            "_complexity_similarity": 1.0,
            "_complexity_reason": "双模型选择已禁用"
        })
    
    try:
        # 延迟导入分类器
        if classifier is None:
            from ....framework.models.query_complexity_classifier import QueryComplexityClassifier
            classifier = QueryComplexityClassifier()
        
        # 生成缓存键
        query_hash = hashlib.md5(query_text.encode('utf-8')).hexdigest()
        cache_key = f"bge_complexity:{query_hash}"
        
        async def fetch_complexity():
            return classifier.classify_complexity(query_text)
        
        # 使用缓存管理器（如果可用）
        if cache_manager:
            result = await cache_manager.get(
                key=cache_key,
                fetch_func=fetch_complexity,
                ttl=3600  # 1小时TTL
            )
        else:
            result = classifier.classify_complexity(query_text)
        
        # 提取结果
        is_complex = result.is_complex
        similarity = result.similarity
        reason = result.reason
        
        # 确定复杂度级别
        if is_complex:
            complexity_level = "complex"
        elif similarity >= 0.5:
            complexity_level = "moderate"
        else:
            complexity_level = "simple"
        
        logger.info(
            f"✅ [{request_id}] 步骤4完成: 复杂度={complexity_level}, "
            f"相似度={similarity:.2f}, 耗时={result.duration_ms:.2f}ms"
        )
        
        return StateUpdate(updates={
            "complexity_level": complexity_level,
            "_complexity_similarity": similarity,
            "_complexity_reason": reason
        })
        
    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤4: BGE复杂度分类失败: {e}")
        # 降级策略：默认为简单查询
        return StateUpdate(
            updates={"complexity_level": "simple"},
            warning=f"BGE复杂度分类失败，使用降级策略: {str(e)}"
        )


# ============ 步骤5：智能模型选择 ============

async def node_select_model(
    state: WorkflowState
) -> StateUpdate:
    """
    步骤5：智能模型选择（三段式决策）
    
    注意：当DUAL_MODEL_ENABLED=false时，直接选择DeepSeek（teacher）
    
    Args:
        state: 当前工作流状态
        
    Returns:
        StateUpdate: 状态更新，包含 selected_model
    """
    import os
    request_id = state.get("request_id", "unknown")
    
    # ✅ 检查是否启用双模型选择
    dual_model_enabled = os.getenv("DUAL_MODEL_ENABLED", "false").lower() == "true"
    if not dual_model_enabled:
        logger.info(f"✅ [{request_id}] 步骤5完成: 双模型选择已禁用，直接使用DeepSeek")
        return StateUpdate(updates={"selected_model": "teacher"})
    
    complexity_level = state.get("complexity_level", "simple")
    similarity = state.get("_complexity_similarity", 0.0)
    is_premium = state.get("is_premium", False)
    
    # 模型选择逻辑
    if complexity_level == "complex" or similarity >= 0.7:
        model_choice = "teacher"
    else:
        model_choice = "student"
    
    logger.info(f"✅ [{request_id}] 步骤5完成: 选择模型={model_choice}")
    
    return StateUpdate(updates={"selected_model": model_choice})



# ============ 步骤6：Few-Shot检索 ============

async def node_retrieve_few_shot(
    state: WorkflowState,
    backend_client=None,
    cache_manager=None
) -> StateUpdate:
    """
    步骤6：Few-Shot检索（推理时学习 + 缓存管理器集成）
    
    Args:
        state: 当前工作流状态
        backend_client: 后端客户端（可选）
        cache_manager: 缓存管理器（可选）
        
    Returns:
        StateUpdate: 状态更新，包含 few_shot_examples
    """
    request_id = state.get("request_id", "unknown")
    query_text = state.get("query_text", "")
    user_profile = state.get("user_profile")
    domain = state.get("domain", "fitness")
    
    few_shot_examples = []
    
    try:
        from ....framework.retrieval.enhanced_few_shot_retriever import EnhancedFewShotRetriever
        
        few_shot_retriever = EnhancedFewShotRetriever(
            vector_store=None,
            backend_client=backend_client
        )
        
        # 生成缓存键
        cache_key_data = f"{query_text}:{user_profile.get('fitness_goal', '') if user_profile else ''}:{domain}"
        cache_hash = hashlib.md5(cache_key_data.encode('utf-8')).hexdigest()
        cache_key = f"few_shot:{cache_hash}"
        
        async def fetch_few_shot_examples():
            best_practices = await few_shot_retriever.get_best_practices(
                query=query_text,
                user_profile=user_profile,
                domain=domain,
                top_k=3
            )
            
            examples = []
            for match in best_practices:
                bp = match.best_practice
                formatted = few_shot_retriever.best_practices_retriever.format_best_practice(
                    bp, user_profile,
                    {"exercise_name": "动作", "goal": user_profile.get("fitness_goal", "健康") if user_profile else "健康"}
                )
                
                examples.append({
                    "query": bp.query_pattern,
                    "response": formatted,
                    "match_score": match.match_score,
                    "pattern_id": bp.pattern_id
                })
            
            return examples
        
        # 使用缓存管理器（如果可用）
        if cache_manager:
            few_shot_examples = await cache_manager.get(
                key=cache_key,
                fetch_func=fetch_few_shot_examples,
                ttl=1800  # 30分钟TTL
            )
        else:
            few_shot_examples = await fetch_few_shot_examples()
        
        if few_shot_examples is None:
            few_shot_examples = []
        
        logger.info(f"✅ [{request_id}] 步骤6完成: {len(few_shot_examples)}个最佳实践")
        
        return StateUpdate(updates={"few_shot_examples": few_shot_examples})
        
    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤6: Few-Shot检索异常: {e}")
        return StateUpdate(
            updates={"few_shot_examples": []},
            warning=f"Few-Shot检索异常: {str(e)}"
        )


# ============ 步骤6.5：LLM选择DAG模板（含会员权限检查） ============

async def node_select_dag_template(
    state: WorkflowState,
    template_manager=None,
    decision_engine=None,
    cache_manager=None
) -> StateUpdate:
    """
    步骤6.5：LLM选择DAG模板（含会员权限检查）

    工作流程：
    1. 检查是否有用户强制指定的模板ID（template_id参数）
    2. 如果有强制指定，直接使用该模板（跳过LLM选择）
    3. 如果没有强制指定，先查缓存，未命中再调LLM选择
    4. 检查用户会员等级是否有权使用该模板
    5. 如果无权限，自动降级到用户可用的模板
    6. 返回最终选择的模板ID和权限检查结果

    会员等级与模板对应（MVP阶段）：
    - 免费版(2个): greeting, quick_consultation
    - 暖心会员(13个): 全部模板（¥6首充福利）
    - 能量会员: 暂不开放（等Agent模式开发完成）

    Args:
        state: 当前工作流状态
        template_manager: DAG模板管理器（可选）
        decision_engine: LLM决策引擎（可选）
        cache_manager: 缓存管理器（可选，用于缓存LLM模板选择结果）
        
    Returns:
        StateUpdate: 状态更新，包含 dag_template_id, _permission_check_result
    """
    request_id = state.get("request_id", "unknown")
    query_text = state.get("query_text", "")
    user_profile = state.get("user_profile")
    session_id = state.get("session_id")
    few_shot_examples = state.get("few_shot_examples", [])
    membership_info = state.get("membership_info")  # 从步骤3获取的会员信息
    force_template_id = state.get("template_id")  # 用户强制指定的模板ID
    
    selected_template_id = None
    cached_template_id = None
    permission_denied = False
    upgrade_message = None
    
    try:
        from ..llm_decision_engine import LLMDecisionEngine, DAGSelectionRequest
        from ..dag_template_system import DAGTemplateManager
        from ..services.dag_template_permission import (
            check_template_permission,
            get_user_membership_tier,
            get_template_count_by_tier
        )
        
        # 初始化模板管理器
        if template_manager is None:
            template_manager = DAGTemplateManager()
        
        # ✅ 检查是否有用户强制指定的模板ID
        if force_template_id:
            # 验证模板ID是否有效
            template = template_manager.get_template(force_template_id)
            if template:
                original_template_id = force_template_id
                logger.info(
                    f"🎯 [{request_id}] 步骤6.5: 用户强制指定模板={force_template_id}，跳过LLM选择"
                )
            else:
                # 无效的模板ID，回退到LLM选择
                logger.warning(
                    f"⚠️ [{request_id}] 步骤6.5: 无效的模板ID={force_template_id}，回退到LLM选择"
                )
                force_template_id = None
        
        # 如果没有强制指定，使用LLM选择（带缓存）
        if not force_template_id:
            # 初始化决策引擎
            if decision_engine is None:
                decision_engine = LLMDecisionEngine(template_manager)

            # 缓存key: 基于查询文本hash + 会员等级
            user_tier = get_user_membership_tier(membership_info)
            import hashlib
            query_hash = hashlib.md5(query_text.encode()).hexdigest()[:12]
            cache_key = f"dag_template:{query_hash}:{user_tier}"

            # 尝试从缓存获取
            cached_template_id = None
            if cache_manager:
                cached_template_id = await cache_manager.get(cache_key)

            if cached_template_id:
                # 缓存命中，跳过LLM调用
                original_template_id = cached_template_id
                logger.info(
                    f"⚡ [{request_id}] 步骤6.5: 缓存命中 模板={original_template_id}, "
                    f"key={cache_key}"
                )
            else:
                # 缓存未命中，调用LLM选择
                selection_request = DAGSelectionRequest(
                    user_query=query_text,
                    user_profile=user_profile or {},
                    available_templates=template_manager.get_all_templates(),
                    session_context={"session_id": session_id},
                    few_shot_examples=few_shot_examples
                )

                selection_result = await decision_engine.select_dag_template(selection_request)
                original_template_id = selection_result.selected_template_id

                # 写入缓存（TTL=1小时）
                if cache_manager and original_template_id:
                    await cache_manager.set(cache_key, original_template_id, ttl=3600)

                logger.info(
                    f"🤖 [{request_id}] 步骤6.5: LLM选择模板={original_template_id}, "
                    f"置信度={selection_result.confidence:.2f}, 已缓存"
                )
        else:
            original_template_id = force_template_id
        
        # ✅ 会员权限检查
        permission_result = check_template_permission(original_template_id, membership_info)
        user_tier = get_user_membership_tier(membership_info)
        available_count, total_count = get_template_count_by_tier(user_tier)
        
        if permission_result.allowed:
            # 有权限，使用原始选择
            selected_template_id = original_template_id
            logger.info(
                f"✅ [{request_id}] 步骤6.5完成: 模板={selected_template_id}, "
                f"会员={user_tier}, 可用模板={available_count}/{total_count}"
                f"{', 用户强制指定' if force_template_id else ''}"
            )
        else:
            # 无权限，使用降级模板
            selected_template_id = permission_result.fallback_template_id or "quick_consultation"
            permission_denied = True
            upgrade_message = permission_result.message
            
            logger.warning(
                f"⚠️ [{request_id}] 步骤6.5: 权限不足，模板降级 "
                f"{original_template_id} → {selected_template_id}, "
                f"会员={user_tier}, 需要={permission_result.required_tier}"
            )
        
        return StateUpdate(updates={
            "dag_template_id": selected_template_id,
            "_dag_selection_confidence": 1.0 if (force_template_id or cached_template_id) else selection_result.confidence,
            "_dag_selection_reason": "用户强制指定" if force_template_id else ("缓存命中" if cached_template_id else selection_result.selection_reason),
            "_original_template_id": original_template_id,
            "_force_template_used": bool(force_template_id),
            "_permission_denied": permission_denied,
            "_upgrade_message": upgrade_message,
            "_user_tier": user_tier,
            "_available_templates_count": available_count,
            "_total_templates_count": total_count
        })
        
    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤6.5: LLM选择失败: {e}")
        
        # 降级到规则匹配
        try:
            from ..dag_template_system import DAGTemplateManager
            from ..services.dag_template_permission import check_template_permission
            
            if template_manager is None:
                template_manager = DAGTemplateManager()
            selected_template_id = template_manager.match_template_by_keywords(query_text)
            
            # 即使降级也要检查权限
            permission_result = check_template_permission(selected_template_id, membership_info)
            if not permission_result.allowed:
                selected_template_id = permission_result.fallback_template_id or "quick_consultation"
            
            logger.info(f"✅ [{request_id}] 步骤6.5完成: 使用降级策略，选择模板={selected_template_id}")
        except Exception as fallback_error:
            logger.error(f"❌ [{request_id}] 步骤6.5: 降级策略也失败: {fallback_error}")
            selected_template_id = "quick_consultation"  # 最终降级到免费模板
        
        return StateUpdate(
            updates={"dag_template_id": selected_template_id},
            warning=f"LLM选择失败，使用降级策略: {str(e)}"
        )


# ============ 步骤7：DAG编排执行 ============

async def node_execute_dag(
    state: WorkflowState,
    dag_orchestrator=None,
    mcp_tool_manager=None,
    template_manager=None
) -> StateUpdate:
    """
    步骤7：DAG编排执行
    
    Args:
        state: 当前工作流状态
        dag_orchestrator: DAG编排器（可选）
        mcp_tool_manager: MCP工具管理器（可选）
        template_manager: DAG模板管理器（可选）
        
    Returns:
        StateUpdate: 状态更新，包含 dag_results
    """
    request_id = state.get("request_id", "unknown")
    selected_template_id = state.get("dag_template_id")
    user_profile = state.get("user_profile")
    session_id = state.get("session_id")
    query_text = state.get("query_text", "")
    user_id = state.get("user_id")  # 修复: 从state中提取user_id
    
    if not selected_template_id:
        logger.warning(f"⚠️ [{request_id}] 步骤7: 无DAG模板ID，跳过执行")
        return StateUpdate(
            updates={"dag_results": None},
            warning="无DAG模板ID"
        )
    
    try:
        from ..enhanced_dag_orchestrator import EnhancedDAGOrchestrator
        from ..dag_template_system import DAGTemplateManager
        
        # 初始化模板管理器
        if template_manager is None:
            template_manager = DAGTemplateManager()
        
        # 初始化DAG编排器
        if dag_orchestrator is None:
            dag_orchestrator = EnhancedDAGOrchestrator(
                template_manager=template_manager,
                mcp_orchestrator=mcp_tool_manager
            )
        
        # 执行DAG模板
        # 构建完整的_context，包含user_id, query, session_id, user_profile
        # 这些数据将被ParameterExtractor用于workflow state回退提取
        dag_execution_result = await dag_orchestrator.execute_template(
            template_id=selected_template_id,
            user_profile=user_profile or {},
            session_context={
                "session_id": session_id,
                "query": query_text,
                "_context": {
                    "user_id": user_id,
                    "query": query_text,
                    "session_id": session_id,
                    "user_profile": user_profile
                }
            },
            cached_results=None
        )
        
        # 提取结果
        dag_results = dag_execution_result.results
        
        if dag_results:
            logger.info(
                f"✅ [{request_id}] 步骤7完成: "
                f"{dag_execution_result.tasks_completed}个任务成功, "
                f"{dag_execution_result.tasks_failed}个任务失败"
            )
            
            return StateUpdate(updates={
                "dag_results": dag_results,
                "_dag_tasks_completed": dag_execution_result.tasks_completed,
                "_dag_tasks_failed": dag_execution_result.tasks_failed
            })
        else:
            logger.warning(f"⚠️ [{request_id}] 步骤7: DAG执行返回空结果")
            return StateUpdate(
                updates={"dag_results": None},
                warning="DAG执行返回空结果"
            )
            
    except Exception as e:
        logger.error(f"❌ [{request_id}] 步骤7: DAG执行异常: {e}")
        return StateUpdate(
            updates={"dag_results": None},
            error=f"DAG执行异常: {str(e)}"
        )


# ============ 步骤8：意图路由 + 检索 ============

async def node_retrieve_context(
    state: WorkflowState,
    three_layer_engine=None,
    graphrag_retriever=None,
    hybrid_search_engine=None,
    cypher_executor=None,
) -> StateUpdate:
    """
    步骤8：意图路由检索（Phase 4C）

    路由逻辑：
    0. DAG已有结果 → 直接使用
    1. 意图分类器判断查询类型
       - structured → Neo4j Cypher 直查（跳过向量检索，~50ms）
       - semantic   → HybridSearch（BM25 + 向量 + RRF，~200ms）
       - hybrid     → Neo4j + HybridSearch 融合
    2. 降级链：GraphRAG → 三层检索 → 空结果
    3. 所有路径均追加 knowledge_articles 知识库检索结果（knowledge_refs）

    Args:
        state: 当前工作流状态
        three_layer_engine: 旧三层检索引擎（降级用）
        graphrag_retriever: 新 GraphRAG 检索器
        hybrid_search_engine: 混合检索引擎
        cypher_executor: Neo4j Cypher 直查执行器

    Returns:
        StateUpdate: 状态更新，包含 retrieval_results（含 knowledge_refs）
    """
    request_id = state.get("request_id", "unknown")
    query_text = state.get("query_text", "")
    domain = state.get("domain", "fitness")
    dag_results = state.get("dag_results")

    # 并行启动 knowledge_articles 检索（不阻塞主检索路径）
    knowledge_task: Optional[asyncio.Task] = None
    if hybrid_search_engine is not None:
        try:
            knowledge_task = asyncio.ensure_future(
                hybrid_search_engine.search_knowledge_articles(query_text, top_k=5)
            )
        except Exception as e:
            logger.warning(f"⚠️ [{request_id}] 步骤8: 启动知识库检索任务失败: {e}")

    async def _get_knowledge_refs() -> List[Dict]:
        """等待知识库检索任务，失败时返回空列表"""
        if knowledge_task is None:
            return []
        try:
            return await knowledge_task
        except Exception as e:
            logger.warning(f"⚠️ [{request_id}] 步骤8: 知识库检索任务失败: {e}")
            return []

    # 如果DAG已经返回结果，可能不需要额外检索
    if dag_results:
        knowledge_refs = await _get_knowledge_refs()
        logger.info(f"✅ [{request_id}] 步骤8完成: 使用DAG结果，跳过检索")
        return StateUpdate(updates={
            "retrieval_results": {
                "results": _convert_dag_results_to_list(dag_results),
                "query_type": "dag_orchestration",
                "domain": domain,
                "count": len(dag_results),
                "knowledge_refs": knowledge_refs,
            }
        })

    # ─── Phase 4C: 意图分类路由 ───
    intent_result = None
    try:
        from ....framework.retrieval.intent_classifier import classify_intent, QueryIntent
        intent_result = classify_intent(query_text)
    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤8: 意图分类失败，降级到混合检索: {e}")

    # 路由1: structured → Neo4j Cypher 直查
    if (intent_result
            and intent_result.intent == QueryIntent.STRUCTURED
            and intent_result.structured_type
            and intent_result.extracted_entity):
        try:
            if cypher_executor is None:
                from ....framework.retrieval.cypher_templates import CypherQueryExecutor
                cypher_executor = CypherQueryExecutor()

            neo4j_results = cypher_executor.execute(
                query_type=intent_result.structured_type,
                entity=intent_result.extracted_entity,
                limit=10
            )

            if neo4j_results:
                knowledge_refs = await _get_knowledge_refs()
                logger.info(
                    f"✅ [{request_id}] 步骤8完成: "
                    f"Neo4j直查({intent_result.structured_type.value}) "
                    f"返回 {len(neo4j_results)} 个结果, "
                    f"实体='{intent_result.extracted_entity}'"
                )
                return StateUpdate(updates={
                    "retrieval_results": {
                        "results": neo4j_results,
                        "query_type": f"neo4j_structured:{intent_result.structured_type.value}",
                        "domain": domain,
                        "count": len(neo4j_results),
                        "intent": intent_result.intent.value,
                        "entity": intent_result.extracted_entity,
                        "knowledge_refs": knowledge_refs,
                    }
                })
            else:
                logger.info(
                    f"⚠️ [{request_id}] 步骤8: Neo4j直查无结果，降级到混合检索"
                )
        except Exception as e:
            logger.warning(
                f"⚠️ [{request_id}] 步骤8: Neo4j直查失败，降级到混合检索: {e}"
            )

    # 路由2: hybrid → Neo4j + HybridSearch 融合
    if intent_result and intent_result.intent == QueryIntent.HYBRID:
        try:
            neo4j_results = []
            if intent_result.extracted_entity and cypher_executor:
                try:
                    # 尝试用 exercise_details 作为通用结构化补充
                    from ....framework.retrieval.intent_classifier import StructuredQueryType
                    neo4j_results = cypher_executor.execute(
                        query_type=StructuredQueryType.EXERCISE_DETAILS,
                        entity=intent_result.extracted_entity,
                        limit=5
                    )
                except Exception:
                    pass

            # 同时走混合检索
            hybrid_results = []
            if hybrid_search_engine:
                try:
                    hybrid_results = await hybrid_search_engine.hybrid_search(
                        query=query_text, domain=domain, top_k=10,
                        intent_type="HYBRID"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [{request_id}] 步骤8: 混合检索失败: {e}")

            # 融合：Neo4j 结果排前面，HybridSearch 结果排后面（去重）
            merged = _merge_results(neo4j_results, hybrid_results, max_total=10)

            if merged:
                knowledge_refs = await _get_knowledge_refs()
                logger.info(
                    f"✅ [{request_id}] 步骤8完成: "
                    f"Hybrid路由(Neo4j={len(neo4j_results)}+Search={len(hybrid_results)}) "
                    f"→ 融合{len(merged)}个结果"
                )
                return StateUpdate(updates={
                    "retrieval_results": {
                        "results": merged,
                        "query_type": "intent_hybrid",
                        "domain": domain,
                        "count": len(merged),
                        "intent": "hybrid",
                        "entity": intent_result.extracted_entity,
                        "knowledge_refs": knowledge_refs,
                    }
                })
        except Exception as e:
            logger.warning(
                f"⚠️ [{request_id}] 步骤8: Hybrid路由整体失败，降级到语义检索: {e}"
            )

    # 路由3: semantic → HybridSearch（BM25 + 向量 + 加权RRF）
    if hybrid_search_engine:
        try:
            # 传入意图类型，动态调整 BM25/向量权重
            search_intent = intent_result.intent.value if intent_result else "SEMANTIC"
            hybrid_results = await hybrid_search_engine.hybrid_search(
                query=query_text,
                domain=domain,
                top_k=10,
                intent_type=search_intent
            )
            query_type_label = "hybrid_search"
            if intent_result and intent_result.intent == QueryIntent.SEMANTIC:
                query_type_label = "semantic_hybrid_search"

            logger.info(
                f"✅ [{request_id}] 步骤8完成: "
                f"HybridSearch(BM25+向量+RRF) 返回 {len(hybrid_results)} 个结果"
            )
            knowledge_refs = await _get_knowledge_refs()
            return StateUpdate(updates={
                "retrieval_results": {
                    "results": hybrid_results,
                    "query_type": query_type_label,
                    "domain": domain,
                    "count": len(hybrid_results),
                    "intent": intent_result.intent.value if intent_result else "unknown",
                    "knowledge_refs": knowledge_refs,
                }
            })
        except Exception as e:
            logger.warning(
                f"⚠️ [{request_id}] 步骤8: 混合检索失败，降级到GraphRAG: {e}"
            )

    # 降级：GraphRAG 或旧三层检索
    retriever = graphrag_retriever or three_layer_engine

    try:
        if retriever:
            retrieval_results = await retriever.search(
                query=query_text,
                domain=domain,
                top_k=10
            )

            retriever_name = getattr(retriever, '__class__', type(retriever)).__name__
            logger.info(
                f"✅ [{request_id}] 步骤8完成: "
                f"{retriever_name} 返回 {len(retrieval_results.get('results', []))} 个结果"
            )

            knowledge_refs = await _get_knowledge_refs()
            retrieval_results["knowledge_refs"] = knowledge_refs
            return StateUpdate(updates={"retrieval_results": retrieval_results})
        else:
            knowledge_refs = await _get_knowledge_refs()
            logger.warning(f"⚠️ [{request_id}] 步骤8: 无检索引擎")
            return StateUpdate(
                updates={"retrieval_results": {"results": [], "count": 0, "knowledge_refs": knowledge_refs}},
                warning="无检索引擎"
            )

    except Exception as e:
        logger.error(f"❌ [{request_id}] 步骤8: 检索异常: {e}")
        return StateUpdate(
            updates={"retrieval_results": {"results": [], "count": 0, "knowledge_refs": []}},
            error=f"检索异常: {str(e)}"
        )


def _merge_results(
    neo4j_results: List[Dict],
    hybrid_results: List[Dict],
    max_total: int = 10
) -> List[Dict]:
    """融合 Neo4j 和 HybridSearch 结果（去重）"""
    seen_texts = set()
    merged = []

    # Neo4j 结果优先
    for r in neo4j_results:
        text_key = r.get("text", "")[:80]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            merged.append(r)

    # HybridSearch 结果补充
    for r in hybrid_results:
        if len(merged) >= max_total:
            break
        text_key = r.get("text", "")[:80]
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            merged.append(r)

    return merged


def _convert_dag_results_to_list(dag_results: Dict[str, Any]) -> list:
    """将DAG结果转换为列表格式"""
    if not dag_results:
        return []
    
    results = []
    for task_name, result in dag_results.items():
        if result and isinstance(result, dict) and "error" not in result:
            results.append({
                "id": f"{task_name}_result",
                "content": str(result),
                "score": 0.8,
                "metadata": {
                    "layer": "dag_task",
                    "source": task_name,
                    "task": task_name
                }
            })
    return results



# ============ 步骤9：工具结果汇总 ============

# MCP工具类型列表（15个Python MCP工具）
MCP_TASK_TYPES = [
    # 训练计划相关（5个）
    "intelligent_exercise_selector",
    "professional_program_designer",
    "periodized_program_designer",
    "training_split_designer",
    "intelligent_weight_calculator",
    # 安全与康复相关（5个）
    "contraindications_checker",
    "injury_risk_assessor",
    "exercise_alternative_finder",
    "safe_exercise_modifier",
    "movement_pattern_balancer",
    # 训练量与恢复相关（2个）
    "muscle_group_volume_calculator",
    "tdee_calculator",
    # 营养相关（3个）
    "nutrition_intake_analyzer",
    "meal_plan_designer",
    "exercise_nutrition_optimization"
]

# 工作流程步骤列表（不是MCP工具）
WORKFLOW_STEPS = [
    "get_user_profile",
    "get_user_membership",
    "semantic_search",
    "three_layer_retrieval",
    "assess_fitness_level",
    "analyze_nutrition_needs",
    "search_foods"
]


async def node_aggregate_data(
    state: WorkflowState
) -> StateUpdate:
    """
    步骤9：工具结果汇总（结构化JSON）
    
    Args:
        state: 当前工作流状态
        
    Returns:
        StateUpdate: 状态更新，包含 aggregated_data
    """
    request_id = state.get("request_id", "unknown")
    dag_results = state.get("dag_results", {})
    user_profile = state.get("user_profile")
    membership_info = state.get("membership_info")
    retrieval_results = state.get("retrieval_results")
    
    # 汇总所有数据
    all_data = {}
    mcp_tools_called = []
    
    # 1. 从DAG执行结果中提取MCP工具调用结果
    if dag_results:
        for task_name, task_result in dag_results.items():
            # 只记录真正的MCP工具
            if task_name in MCP_TASK_TYPES:
                if task_result and isinstance(task_result, dict):
                    all_data[task_name] = task_result
                    
                    # 严格的成功判断
                    has_error = "error" in task_result and task_result["error"] is not None
                    is_success = task_result.get("success", False) is True
                    is_fallback = task_result.get("fallback", False) or task_result.get("fallback_used", False)
                    
                    if is_success and not has_error and not is_fallback:
                        mcp_tools_called.append(task_name)
                        logger.debug(f"   ✅ MCP工具: {task_name} (成功)")
                    else:
                        error_msg = task_result.get('error', 'Unknown')
                        logger.warning(f"   ⚠️ MCP工具: {task_name} (失败: {error_msg})")
            
            # 工作流程步骤数据也保存
            elif task_name in WORKFLOW_STEPS:
                if task_result and isinstance(task_result, dict):
                    all_data[task_name] = task_result
    
    # 2. 添加用户档案
    if user_profile:
        all_data["user_profile"] = user_profile
    
    # 3. 添加会员信息
    if membership_info:
        all_data["user_membership"] = membership_info
    
    # 4. 添加检索结果
    if retrieval_results and retrieval_results.get("results"):
        all_data["retrieval_results"] = {
            "results": retrieval_results.get("results", []),
            "count": retrieval_results.get("count", 0),
            "query_type": retrieval_results.get("query_type", "unknown")
        }
    
    workflow_data_count = len([
        k for k in all_data.keys() 
        if k in WORKFLOW_STEPS or k in ['user_profile', 'user_membership', 'retrieval_results']
    ])
    
    logger.info(f"✅ [{request_id}] 步骤9完成:")
    logger.info(f"   - MCP工具调用: {len(mcp_tools_called)}个 ({', '.join(mcp_tools_called) if mcp_tools_called else '无'})")
    logger.info(f"   - 工作流程数据: {workflow_data_count}项")
    logger.info(f"   - 总数据项: {len(all_data)}个")
    
    return StateUpdate(updates={
        "aggregated_data": all_data,
        "_mcp_tools_called": mcp_tools_called
    })


# ============ 步骤10：LLM生成回答 ============

async def node_llm_analysis(
    state: WorkflowState,
    config_manager=None,
    fallback_manager=None,
    template_manager=None
) -> StateUpdate:
    """
    步骤10：LLM生成最终回答（使用配置管理器）
    
    Args:
        state: 当前工作流状态
        config_manager: LLM响应配置管理器（可选）
        fallback_manager: LLM降级管理器（可选）
        template_manager: DAG模板管理器（可选）
        
    Returns:
        StateUpdate: 状态更新，包含 final_response
    """
    request_id = state.get("request_id", "unknown")
    query_text = state.get("query_text", "")
    selected_template_id = state.get("dag_template_id", "default")
    user_profile = state.get("user_profile")
    aggregated_data = state.get("aggregated_data", {})
    few_shot_examples = state.get("few_shot_examples", [])
    dag_results = state.get("dag_results", {})
    mcp_tools_called = state.get("_mcp_tools_called", [])
    retrieval_results = state.get("retrieval_results") or {}
    conversation_history = state.get("conversation_history") or []
    
    try:
        # 1. 初始化配置管理器
        if config_manager is None:
            from ....framework.config.llm_response_config_manager import LLMResponseConfigManager
            config_manager = LLMResponseConfigManager()
        
        # 2. 获取模板配置
        llm_response_config = config_manager.get_config(selected_template_id)
        logger.info(f"   - 使用模板配置: {selected_template_id}")
        logger.info(f"   - max_tokens={llm_response_config.max_tokens}, temperature={llm_response_config.temperature}")
        
        # 3. 从DAG模板获取response_hint
        if template_manager is None:
            from ..dag_template_system import DAGTemplateManager
            template_manager = DAGTemplateManager()
        
        selected_template = template_manager.get_template(selected_template_id)
        response_hint = selected_template.response_hint if selected_template else "请提供专业的分析和建议"
        
        # 4. 准备用户档案字符串
        user_profile_for_prompt = '未提供'
        if user_profile:
            try:
                serializable_profile = {}
                for key, value in user_profile.items():
                    if key == 'membership' and hasattr(value, '__dict__'):
                        if hasattr(value, 'tier'):
                            serializable_profile['membership_tier'] = str(value.tier)
                    elif isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        serializable_profile[key] = value
                    else:
                        serializable_profile[key] = str(value)
                user_profile_for_prompt = json.dumps(serializable_profile, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"用户档案序列化失败: {e}")
                user_profile_for_prompt = str(user_profile)
        
        # 5. 准备MCP工具结果
        mcp_tools_result_json = "{}"
        if mcp_tools_called and dag_results:
            try:
                if "professional_program_designer" in dag_results:
                    program_result = dag_results["professional_program_designer"]
                    if program_result and not program_result.get("error"):
                        # 使用WeeklyPlanGenerator转换为单周输出
                        try:
                            from ..services.weekly_plan_generator import WeeklyPlanGenerator
                            
                            weekly_generator = WeeklyPlanGenerator()
                            total_weeks = program_result.get("program_overview", {}).get("training_weeks", 4)
                            
                            weekly_plan = weekly_generator.generate_first_week(
                                full_program=program_result,
                                user_profile=user_profile,
                                total_weeks=total_weeks
                            )
                            
                            weekly_plan_output = weekly_generator.convert_to_output_format(weekly_plan)
                            program_result["weekly_plan_output"] = weekly_plan_output
                            program_result["output_mode"] = "weekly"
                            
                        except Exception as weekly_gen_error:
                            logger.warning(f"分周计划生成失败: {weekly_gen_error}")
                            program_result["output_mode"] = "full"
                        
                        mcp_tools_result_json = json.dumps(program_result, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"提取MCP工具结果失败: {e}")
        
        # 6. 构建提示词
        system_prompt = config_manager.build_prompt(
            template_id=selected_template_id,
            query=query_text,
            user_profile=user_profile_for_prompt,
            response_hint=response_hint,
            mcp_tools_count=len(mcp_tools_called),
            retrieval_count=len(retrieval_results.get('results', [])),
            mcp_tools_result=mcp_tools_result_json
        )

        # 6.1 追加知识库引用到 system_prompt
        knowledge_refs = retrieval_results.get("knowledge_refs", [])
        if knowledge_refs:
            refs_lines = ["", "---", "【知识库参考文献】"]
            for ref in knowledge_refs:
                title = ref.get("title", "")
                source_book = ref.get("source_book", "")
                chapter = ref.get("chapter", "")
                chapter_part = f" Ch.{chapter}" if chapter else ""
                refs_lines.append(f"[知识引用] {title} — {source_book}{chapter_part}")
            system_prompt = system_prompt + "\n".join(refs_lines)
            logger.info(f"   - 注入知识库引用: {len(knowledge_refs)} 条")
        
        logger.info(f"   - 提示词长度: {len(system_prompt)}字")
        
        # 7. 调用LLM
        if fallback_manager is None:
            from .singletons import get_llm_degradation_manager
            fallback_manager = get_llm_degradation_manager()
        
        few_shot_dicts = [{"query": ex["query"], "response": ex["response"]} for ex in few_shot_examples]
        
        from ....framework.clients.llm_fallback_manager import LLMRequest
        llm_request = LLMRequest(
            query=query_text,
            few_shot_examples=few_shot_dicts,
            tool_results=aggregated_data,
            system_prompt=system_prompt,
            max_tokens=llm_response_config.max_tokens,
            temperature=llm_response_config.temperature,
            stream=False,
            conversation_history=conversation_history if conversation_history else None,
        )
        
        llm_response = await fallback_manager.call_with_fallback(llm_request)
        final_response = llm_response.content
        
        # 记录降级信息
        if llm_response.fallback_used:
            logger.warning(
                f"⚠️ [{request_id}] 步骤10: 使用了降级策略 "
                f"(backend={llm_response.backend_used.value})"
            )
        
        logger.info(
            f"✅ [{request_id}] 步骤10完成: LLM生成完成 "
            f"(backend={llm_response.backend_used.value}, "
            f"length={len(final_response)}字)"
        )
        
        return StateUpdate(updates={
            "final_response": final_response,
            "_llm_backend_used": llm_response.backend_used.value,
            "_llm_fallback_used": llm_response.fallback_used
        })
        
    except Exception as e:
        logger.error(f"❌ [{request_id}] 步骤10: LLM生成异常: {e}", exc_info=True)
        
        # 构建降级响应
        results_data = retrieval_results.get('results', []) if retrieval_results else []
        final_response = _build_fallback_response(
            query_text=query_text,
            user_profile=user_profile,
            results_data=results_data,
            error=str(e)
        )
        
        return StateUpdate(
            updates={"final_response": final_response},
            error=f"LLM生成异常: {str(e)}"
        )


def _build_fallback_response(
    query_text: str,
    user_profile: Optional[Dict[str, Any]],
    results_data: list,
    error: str
) -> str:
    """构建降级响应"""
    user_profile_summary = ""
    if user_profile:
        user_profile_summary = f"""
👤 **用户档案**：
- 年龄：{user_profile.get('age', '未知')}岁
- 训练经验：{user_profile.get('training_experience', '未知')}
- 训练目标：{user_profile.get('fitness_goal', '未知')}
"""
    
    retrieval_summary = ""
    if results_data:
        retrieval_summary = f"""
🔍 **检索结果**：找到 {len(results_data)} 个相关推荐
"""
        for i, item in enumerate(results_data[:3], 1):
            name = item.get('name_zh', item.get('name', '未知'))
            retrieval_summary += f"{i}. {name}\n"
    
    return f"""抱歉，AI分析功能暂时不可用（{error[:100]}）。

📝 **您的查询**：{query_text}
{user_profile_summary}
✅ **已完成以下数据分析**：
{retrieval_summary}

💡 **建议**：
- 请稍后重试获取AI分析
- 或联系客服获取人工指导

感谢您的理解！"""


# ============ 步骤11：记录交互 ============

async def node_log_interaction(
    state: WorkflowState,
    backend_client=None
) -> StateUpdate:
    """
    步骤11：记录交互（用于未来学习）
    
    Args:
        state: 当前工作流状态
        backend_client: 后端客户端（可选）
        
    Returns:
        StateUpdate: 状态更新，包含 interaction_logged
    """
    request_id = state.get("request_id", "unknown")
    user_id = state.get("user_id")
    session_id = state.get("session_id")
    query_text = state.get("query_text", "")
    final_response = state.get("final_response", "")
    selected_model = state.get("selected_model", "unknown")
    mcp_tools_called = state.get("_mcp_tools_called", [])
    dag_template_id = state.get("dag_template_id")
    complexity_level = state.get("complexity_level")
    few_shot_examples = state.get("few_shot_examples", [])
    retrieval_results = state.get("retrieval_results", {})
    
    if not backend_client:
        logger.warning(f"⚠️ [{request_id}] 步骤11: 无后端客户端，跳过交互记录")
        return StateUpdate(updates={"interaction_logged": False})
    
    try:
        # 转换user_id
        user_id_int = None
        if isinstance(user_id, int):
            user_id_int = user_id
        elif isinstance(user_id, str) and user_id.isdigit():
            user_id_int = int(user_id)
        
        if not user_id_int:
            logger.info(f"✅ [{request_id}] 步骤11完成: 匿名用户，跳过交互记录")
            return StateUpdate(updates={"interaction_logged": False})
        
        # 计算检索层数
        retrieval_layers_count = 0
        if retrieval_results:
            layer_results = retrieval_results.get("layer_results", {})
            if layer_results:
                retrieval_layers_count = len(layer_results)
            elif retrieval_results.get("results"):
                retrieval_layers_count = 1
        
        # 保存会话
        result_data = await backend_client.save_chat_session(
            session_id=session_id,
            user_id=user_id_int,
            user_query=query_text,
            llm_response=final_response,
            model_used=selected_model,
            tools_used=mcp_tools_called,
            metadata={
                "graphrag_service": True,
                "quality_score": None,
                "retrieval_layers": retrieval_layers_count,
                "workflow_steps": 11,
                "is_complex": complexity_level == "complex",
                "few_shot_count": len(few_shot_examples),
                "dag_template_id": dag_template_id,
                "mcp_tools_count": len(mcp_tools_called),
                "request_id": request_id,
                "awaiting_user_feedback": True
            },
            qdrant_point_id=None
        )
        
        logger.info(f"✅ [{request_id}] 步骤11完成: 交互记录完成 (db_id={result_data.get('id')})")
        logger.info(f"   - MCP工具: {', '.join(mcp_tools_called) if mcp_tools_called else '无'}")
        logger.info(f"   - 工具数量: {len(mcp_tools_called)}")
        
        return StateUpdate(updates={
            "interaction_logged": True,
            "_interaction_db_id": result_data.get('id')
        })
        
    except Exception as e:
        logger.warning(f"⚠️ [{request_id}] 步骤11: 交互记录失败: {e}")
        return StateUpdate(
            updates={"interaction_logged": False},
            warning=f"交互记录失败: {str(e)}"
        )


# ============ 导出所有节点函数 ============

__all__ = [
    # 节点函数
    "node_preload_user_profile",
    "node_store_session",
    "node_check_membership",
    "node_classify_complexity",
    "node_select_model",
    "node_retrieve_few_shot",
    "node_select_dag_template",
    "node_execute_dag",
    "node_retrieve_context",
    "node_aggregate_data",
    "node_llm_analysis",
    "node_log_interaction",
    # 常量
    "MCP_TASK_TYPES",
    "WORKFLOW_STEPS",
]
