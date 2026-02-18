# -*- coding: utf-8 -*-
"""
Agent模式流式执行器

基于Skills架构的Agent模式执行，支持流式输出。
与DAG模式的区别：
- DAG模式：预定义工作流，步骤固定
- Agent模式：LLM自主决策，动态调用工具

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import logging
import time
import uuid
import json
from typing import Dict, Any, Optional, AsyncGenerator, List

logger = logging.getLogger(__name__)


class AgentStreamExecutor:
    """
    Agent模式流式执行器
    
    工作流程：
    1. 构建包含技能列表的system prompt
    2. LLM决策（选择技能或工具）
    3. 如果是load_skill，加载技能内容
    4. 如果是call_tool，执行安全检查+工具
    5. 流式生成最终响应
    
    Requirements: 8.1-8.4
    """
    
    DEFAULT_MAX_ITERATIONS = 8
    DEFAULT_TIMEOUT_SECONDS = 60
    
    def __init__(
        self,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    ):
        """
        初始化Agent流式执行器
        
        Args:
            max_iterations: 最大迭代次数
            timeout_seconds: 超时时间（秒）
        """
        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds
        
        # 懒加载组件
        self._skill_manager = None
        self._llm_client = None
        self._mcp_tools = None
        self._layer3_rules = None
        
        logger.info(f"✅ AgentStreamExecutor初始化: max_iterations={max_iterations}")
    
    @property
    def skill_manager(self):
        """获取技能管理器（懒加载）"""
        if self._skill_manager is None:
            try:
                from ...framework.skills import get_skills_integration
                integration = get_skills_integration()
                self._skill_manager = integration.get_skill_manager()
            except Exception as e:
                logger.warning(f"获取SkillManager失败: {e}")
        return self._skill_manager
    
    @property
    def llm_client(self):
        """获取LLM客户端（懒加载）"""
        if self._llm_client is None:
            try:
                from ....framework.clients.llm_client import get_llm_client
                self._llm_client = get_llm_client()
            except Exception as e:
                logger.warning(f"获取LLM客户端失败: {e}")
        return self._llm_client
    
    def _get_mcp_tools(self) -> Dict[str, Any]:
        """获取MCP工具（懒加载）"""
        if self._mcp_tools is None:
            try:
                from .singletons import get_mcp_orchestrator
                orchestrator = get_mcp_orchestrator()
                self._mcp_tools = orchestrator.get_tools() if orchestrator else {}
            except Exception as e:
                logger.warning(f"获取MCP工具失败: {e}")
                self._mcp_tools = {}
        return self._mcp_tools
    
    def _get_layer3_rules(self) -> List:
        """获取Layer3规则（懒加载）"""
        if self._layer3_rules is None:
            try:
                from ..fitness_adapter import FitnessAdapter
                adapter = FitnessAdapter()
                self._layer3_rules = adapter.get_layer3_rules()
            except Exception as e:
                logger.warning(f"获取Layer3规则失败: {e}")
                self._layer3_rules = []
        return self._layer3_rules
    
    def _build_system_prompt(self, user_profile: Optional[Dict[str, Any]] = None) -> str:
        """
        构建Agent模式的system prompt
        
        Args:
            user_profile: 用户档案
        
        Returns:
            str: system prompt
        """
        # 获取技能列表
        skills_prompt = ""
        if self.skill_manager:
            skills_prompt = self.skill_manager.get_system_prompt_skills()
        else:
            skills_prompt = "## 可用技能\n暂无可用技能，请直接回答用户问题。"
        
        # 用户档案摘要
        profile_summary = "未提供"
        if user_profile:
            basic = user_profile.get("basic_info", {})
            profile_summary = f"性别:{basic.get('gender', '未知')}, 年龄:{basic.get('age', '未知')}, 健身水平:{basic.get('fitness_level', '未知')}"
        
        return f"""你是一个专业的健身教练AI助手，名叫"玉珍健身顾问"。

## 用户档案
{profile_summary}

{skills_prompt}

## 工作模式
你正在Agent模式下运行，可以自主决策调用哪些工具来帮助用户。

## 响应要求
1. 如果用户问题简单（问候、闲聊），直接友好回答
2. 如果需要专业分析，先调用load_skill获取技能详情
3. 根据技能指令调用相应工具
4. 综合工具结果生成专业、友好的回答

## 动作格式
当需要执行动作时，使用JSON格式：
```json
{{"action": "load_skill", "skill_id": "技能ID"}}
```
或
```json
{{"action": "call_tool", "tool_name": "工具名", "params": {{...}}}}
```
或直接回答用户问题（无需JSON）。

## 安全注意
- 遵守技能中的安全约束
- 对有伤病的用户给出谨慎建议
- 不提供医疗诊断
"""
    
    async def execute_stream(
        self,
        query_text: str,
        user_id: str,
        user_profile: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        topic_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行Agent模式
        
        Args:
            query_text: 用户查询
            user_id: 用户ID
            user_profile: 用户档案
            session_id: 会话ID
            topic_id: 话题ID
            conversation_history: 对话历史
            **kwargs: 其他参数
        
        Yields:
            SSE事件字典
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        
        logger.info(f"🤖 [{request_id}] Agent模式开始执行")
        logger.info(f"📝 查询: {query_text[:50]}...")
        
        # 初始化执行上下文
        skills_loaded = []
        tool_calls = []
        final_response = ""
        
        try:
            # 步骤1：初始化
            yield {
                "type": "step",
                "step": 1,
                "message": "Agent模式初始化..."
            }
            
            # 构建消息列表
            messages = [
                {"role": "system", "content": self._build_system_prompt(user_profile)}
            ]
            
            # 添加对话历史
            if conversation_history:
                messages.extend(conversation_history)
            
            # 添加用户查询
            messages.append({"role": "user", "content": query_text})
            
            # 步骤2：Agent决策循环
            yield {
                "type": "step",
                "step": 2,
                "message": "AI正在分析您的需求..."
            }
            
            for iteration in range(self.max_iterations):
                logger.info(f"   [{request_id}] 迭代 {iteration + 1}/{self.max_iterations}")
                
                # 调用LLM获取决策
                decision = await self._get_llm_decision(messages)
                
                if decision is None:
                    # LLM直接回答，无需动作
                    break
                
                action = decision.get("action")
                
                if action == "load_skill":
                    # 加载技能
                    skill_id = decision.get("skill_id")
                    if skill_id and self.skill_manager:
                        yield {
                            "type": "step",
                            "step": 3,
                            "message": f"加载技能: {skill_id}..."
                        }
                        
                        skill_content = self.skill_manager.load_skill(skill_id)
                        skills_loaded.append(skill_id)
                        
                        # 添加到对话
                        messages.append({
                            "role": "assistant",
                            "content": f"调用 load_skill(\"{skill_id}\")"
                        })
                        messages.append({
                            "role": "tool",
                            "content": skill_content
                        })
                        
                        logger.info(f"   📖 加载技能: {skill_id}")
                
                elif action == "call_tool":
                    # 调用工具
                    tool_name = decision.get("tool_name")
                    tool_params = decision.get("params", {})
                    
                    yield {
                        "type": "step",
                        "step": 4,
                        "message": f"执行工具: {tool_name}..."
                    }
                    
                    # 执行工具
                    result = await self._execute_tool(
                        tool_name,
                        tool_params,
                        user_profile
                    )
                    
                    tool_calls.append({
                        "tool": tool_name,
                        "params": tool_params,
                        "result": result,
                        "iteration": iteration + 1
                    })
                    
                    # 添加到对话
                    messages.append({
                        "role": "assistant",
                        "content": f"调用 {tool_name}"
                    })
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False, indent=2)[:2000]  # 限制长度
                    })
                    
                    logger.info(f"   🔧 执行工具: {tool_name}")
                
                else:
                    # 未知动作或完成
                    break
            
            # 步骤5：生成最终响应（流式）
            yield {
                "type": "step",
                "step": 5,
                "message": "生成专业建议..."
            }
            
            # 添加生成指令
            messages.append({
                "role": "user",
                "content": "请根据以上信息，为用户生成专业、友好的回答。"
            })
            
            # 流式生成响应
            ttfb_start = time.time()
            first_chunk = True
            tokens_generated = 0
            
            async for chunk in self._stream_llm_response(messages):
                if first_chunk:
                    ttfb_ms = (time.time() - ttfb_start) * 1000
                    first_chunk = False
                
                tokens_generated += 1
                final_response += chunk
                
                yield {
                    "type": "chunk",
                    "content": chunk,
                    "tokens": tokens_generated
                }
            
            # 发送结构化数据
            yield {
                "type": "structured_data",
                "data": {
                    "mode": "agent",
                    "skills_loaded": skills_loaded,
                    "tool_calls": [t["tool"] for t in tool_calls]
                }
            }
            
            # 完成
            processing_time = time.time() - start_time
            
            yield {
                "type": "done",
                "data": {
                    "request_id": request_id,
                    "mode": "agent",
                    "processing_time": processing_time,
                    "iterations": len(tool_calls) + len(skills_loaded),
                    "skills_loaded": skills_loaded,
                    "tool_calls": [t["tool"] for t in tool_calls],
                    "tokens_generated": tokens_generated
                }
            }
            
            logger.info(
                f"✅ [{request_id}] Agent模式完成: "
                f"耗时={processing_time:.2f}s, "
                f"技能={len(skills_loaded)}, "
                f"工具={len(tool_calls)}"
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ [{request_id}] Agent模式执行失败: {e}", exc_info=True)
            
            yield {
                "type": "error",
                "error": str(e),
                "request_id": request_id
            }
    
    async def _get_llm_decision(
        self,
        messages: List[Dict[str, str]]
    ) -> Optional[Dict[str, Any]]:
        """
        获取LLM决策
        
        Args:
            messages: 对话消息列表
        
        Returns:
            决策字典或None（直接回答）
        """
        try:
            if not self.llm_client:
                return None
            
            # 调用LLM
            response = await self.llm_client.chat(messages)
            
            # 尝试解析JSON动作
            import re
            json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response, re.DOTALL)
            
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # 没有找到动作，返回None表示直接回答
            return None
            
        except Exception as e:
            logger.error(f"LLM决策失败: {e}")
            return None
    
    async def _execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        user_profile: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            user_profile: 用户档案
        
        Returns:
            工具执行结果
        """
        try:
            tools = self._get_mcp_tools()
            
            if tool_name not in tools:
                return {"error": f"工具 {tool_name} 不存在"}
            
            tool = tools[tool_name]
            
            # 注入用户档案
            execution_params = {**params}
            if user_profile:
                execution_params["user_profile"] = user_profile
            
            # 执行工具
            if hasattr(tool, 'execute'):
                result = await tool.execute(execution_params)
            elif callable(tool):
                result = await tool(execution_params)
            else:
                return {"error": f"工具 {tool_name} 不可执行"}
            
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行失败: {e}")
            return {"error": str(e)}
    
    async def _stream_llm_response(
        self,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """
        流式生成LLM响应
        
        Args:
            messages: 对话消息列表
        
        Yields:
            响应文本块
        """
        try:
            if not self.llm_client:
                yield "抱歉，AI服务暂时不可用。"
                return
            
            # 使用LLM降级管理器进行流式调用
            from ....framework.clients.llm_fallback_manager import LLMFallbackManager, LLMRequest
            
            fallback_manager = LLMFallbackManager(
                primary_backend="anthropic",
                fallback_backends=["deepseek", "template"],
                max_retries=2,
                timeout=30
            )
            
            # 构建请求
            llm_request = LLMRequest(
                query=messages[-1]["content"] if messages else "",
                system_prompt=messages[0]["content"] if messages else "",
                max_tokens=2000,
                temperature=0.7,
                stream=True,
                conversation_history=messages[1:-1] if len(messages) > 2 else []
            )
            
            # 流式调用
            async for chunk, _ in fallback_manager.call_with_fallback_stream(llm_request):
                if chunk:
                    yield chunk
                    
        except Exception as e:
            logger.error(f"流式LLM响应失败: {e}")
            yield f"抱歉，生成响应时出现问题: {str(e)}"


# =============================================================================
# 工厂函数
# =============================================================================

def create_agent_stream_executor(
    max_iterations: int = AgentStreamExecutor.DEFAULT_MAX_ITERATIONS
) -> AgentStreamExecutor:
    """创建Agent流式执行器"""
    return AgentStreamExecutor(max_iterations=max_iterations)


# 单例实例
_agent_executor_instance: Optional[AgentStreamExecutor] = None


def get_agent_stream_executor() -> AgentStreamExecutor:
    """获取Agent流式执行器单例"""
    global _agent_executor_instance
    if _agent_executor_instance is None:
        _agent_executor_instance = create_agent_stream_executor()
    return _agent_executor_instance


__all__ = [
    "AgentStreamExecutor",
    "create_agent_stream_executor",
    "get_agent_stream_executor",
]
