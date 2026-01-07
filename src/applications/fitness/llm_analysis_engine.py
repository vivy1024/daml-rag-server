# -*- coding: utf-8 -*-
"""
LLM综合分析引擎 v1.0

三段式架构的第三阶段：LLM深度分析和综合
- 基于真实数据进行专业分析
- 生成个性化建议（不仅是翻译）
- 强调安全约束和禁忌项
- 提供推理依据，确保可追溯

对应工作流程：步骤10 - LLM深度分析和综合（不仅是翻译）

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-12
"""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from ...framework.clients.llm_client import call_deepseek, call_ollama, LLMConfig

logger = logging.getLogger(__name__)


@dataclass
class AnalysisRequest:
    """分析请求"""
    user_query: str
    user_profile: Dict[str, Any]
    tool_results: Dict[str, Any]
    contraindications: List[Dict[str, Any]] = field(default_factory=list)
    safety_constraints: List[str] = field(default_factory=list)
    session_context: Optional[Dict[str, Any]] = None


@dataclass
class AnalysisResult:
    """分析结果"""
    professional_analysis: str
    personalized_recommendations: List[str]
    safety_reminders: List[str]
    reasoning_basis: Dict[str, List[str]]
    confidence: float = 0.0
    model_used: str = ""
    analysis_metadata: Dict[str, Any] = field(default_factory=dict)


class LLMAnalysisEngine:
    """LLM综合分析引擎"""

    def __init__(self, prefer_teacher_model: bool = True):
        """
        初始化LLM综合分析引擎

        Args:
            prefer_teacher_model: 是否优先使用教师模型（DeepSeek）
        """
        self.prefer_teacher_model = prefer_teacher_model
        logger.info(f"✅ LLM综合分析引擎初始化完成 (prefer_teacher={prefer_teacher_model})")

    async def analyze_results(
        self,
        request: AnalysisRequest
    ) -> AnalysisResult:
        """
        分析工具执行结果，生成专业建议

        Args:
            request: 分析请求

        Returns:
            AnalysisResult: 分析结果
        """
        logger.info("🔍 开始LLM综合分析...")
        logger.info(f"📊 工具结果数量: {len(request.tool_results)}")
        logger.info(f"⚠️ 禁忌动作数量: {len(request.contraindications)}")

        try:
            # 步骤1: 构建分析提示词
            analysis_prompt = self.build_analysis_prompt(request)

            # 步骤2: 选择模型并调用LLM
            model_used = "unknown"
            llm_response = ""

            if self.prefer_teacher_model and LLMConfig.DEEPSEEK_API_KEY:
                try:
                    llm_response = await call_deepseek(
                        query=request.user_query,
                        few_shot_examples=[],  # 分析阶段不需要Few-Shot
                        tool_results={},  # 工具结果已在system_prompt中
                        system_prompt=analysis_prompt,
                        max_tokens=3000  # 分析需要更多token
                    )
                    model_used = "deepseek-chat"
                    logger.info("✅ 使用教师模型(DeepSeek)进行深度分析")
                except Exception as e:
                    logger.warning(f"DeepSeek调用失败，降级到Ollama: {e}")
                    llm_response = await call_ollama(
                        query=request.user_query,
                        few_shot_examples=[],
                        tool_results={},
                        system_prompt=analysis_prompt,
                        model=LLMConfig.OLLAMA_MODEL
                    )
                    model_used = "ollama-" + LLMConfig.OLLAMA_MODEL
            else:
                try:
                    llm_response = await call_ollama(
                        query=request.user_query,
                        few_shot_examples=[],
                        tool_results={},
                        system_prompt=analysis_prompt,
                        model=LLMConfig.OLLAMA_MODEL
                    )
                    model_used = "ollama-" + LLMConfig.OLLAMA_MODEL
                    logger.info("✅ 使用学生模型(Ollama)进行分析")
                except Exception as e:
                    logger.warning(f"Ollama调用失败，尝试DeepSeek: {e}")
                    if LLMConfig.DEEPSEEK_API_KEY:
                        llm_response = await call_deepseek(
                            query=request.user_query,
                            few_shot_examples=[],
                            tool_results={},
                            system_prompt=analysis_prompt,
                            max_tokens=3000
                        )
                        model_used = "deepseek-chat"
                    else:
                        raise

            # 步骤3: 解析LLM响应
            analysis_result = self.parse_analysis_response(
                llm_response,
                request,
                model_used
            )

            logger.info(f"✅ LLM综合分析完成 (model={model_used})")
            logger.info(f"📝 生成建议数量: {len(analysis_result.personalized_recommendations)}")
            logger.info(f"⚠️ 安全提醒数量: {len(analysis_result.safety_reminders)}")

            return analysis_result

        except Exception as e:
            logger.error(f"❌ LLM综合分析失败: {e}", exc_info=True)
            # 返回降级响应
            return self._create_fallback_response(request, str(e))

    def build_analysis_prompt(
        self,
        request: AnalysisRequest
    ) -> str:
        """
        构建LLM分析提示词

        Args:
            request: 分析请求

        Returns:
            str: 分析提示词
        """
        # 基础提示词
        prompt = """你是一位专业的健身教练和运动科学专家。你的任务是基于真实的工具执行结果，为用户提供专业、个性化的健身指导。

## 🎯 你的核心任务

1. **专业分析**: 基于提供的真实数据进行深度分析，而不仅仅是翻译数据
2. **个性化建议**: 结合用户档案和健身目标，生成具体可行的建议
3. **安全第一**: 必须强调安全约束和禁忌项，确保用户安全
4. **推理依据**: 所有建议都必须基于提供的真实数据，并说明依据

## ⚠️ 重要约束条件

1. ❌ **绝对禁止推荐禁忌动作** - 如果提供了禁忌动作列表，这些动作绝对不能出现在你的建议中
2. ✅ **必须基于真实数据** - 所有建议必须来自工具执行结果，不要编造或推测
3. ✅ **数据不足时明确告知** - 如果数据不足以回答问题，明确告知用户而不是猜测
4. ✅ **提供推理依据** - 每个建议都要说明来源（来自哪个工具的哪个数据）

"""

        # 添加用户档案
        if request.user_profile:
            prompt += "\n## 👤 用户档案\n\n"
            prompt += self._format_user_profile(request.user_profile)

        # 添加禁忌动作（最重要，必须强调）
        if request.contraindications:
            prompt += "\n## ⚠️ 禁忌动作列表（用户健康原因，严禁推荐）\n\n"
            prompt += "**以下动作绝对不能推荐给用户：**\n\n"
            for i, exercise in enumerate(request.contraindications[:15], 1):
                if isinstance(exercise, dict):
                    name = exercise.get('name', exercise.get('exercise_name', '未知'))
                    reason = exercise.get('reason', exercise.get('contraindication_reason', ''))
                    prompt += f"{i}. ❌ **{name}**"
                    if reason:
                        prompt += f" - 原因: {reason}"
                    prompt += "\n"
                else:
                    prompt += f"{i}. ❌ **{exercise}**\n"
            prompt += "\n"

        # 添加工具执行结果
        if request.tool_results:
            prompt += "\n## 🔧 工具执行结果（真实数据）\n\n"
            prompt += self._format_tool_results(request.tool_results)

        # 添加安全约束
        if request.safety_constraints:
            prompt += "\n## 🛡️ 安全约束\n\n"
            for constraint in request.safety_constraints:
                prompt += f"- {constraint}\n"
            prompt += "\n"

        # 添加输出要求
        prompt += """
## 📋 输出要求

请按照以下结构输出你的分析：

### 1. 专业分析
基于工具结果进行深度分析，包括：
- 用户当前状况评估
- 训练计划的科学性分析
- 营养搭配的合理性分析
- 潜在风险评估

### 2. 个性化建议
提供3-5条具体可行的建议，每条建议必须：
- 明确具体（不要泛泛而谈）
- 基于真实数据
- 说明推理依据

### 3. 安全提醒
强调必须注意的安全事项，特别是：
- 禁忌动作提醒
- 健康状况相关注意事项
- 训练强度控制建议

### 4. 推理依据
说明你的建议来自哪些工具的哪些数据，确保可追溯。

---

**记住：你的所有建议都必须基于上述真实数据，不要编造或推测！**
"""

        return prompt

    def _format_user_profile(self, user_profile: Dict[str, Any]) -> str:
        """格式化用户档案"""
        lines = []

        # 基本信息
        basic_info = user_profile.get('basic_info', {})
        if basic_info:
            lines.append("**基本信息：**")
            if basic_info.get('age'):
                lines.append(f"- 年龄: {basic_info['age']}岁")
            if basic_info.get('gender'):
                lines.append(f"- 性别: {basic_info['gender']}")
            if basic_info.get('weight'):
                lines.append(f"- 体重: {basic_info['weight']}kg")
            if basic_info.get('height'):
                lines.append(f"- 身高: {basic_info['height']}cm")
            lines.append("")

        # 健身配置
        fitness_config = user_profile.get('fitness_config', {})
        if fitness_config:
            lines.append("**健身配置：**")
            if fitness_config.get('fitness_level'):
                lines.append(f"- 训练水平: {fitness_config['fitness_level']}")
            if fitness_config.get('training_days_per_week'):
                lines.append(f"- 训练频率: 每周{fitness_config['training_days_per_week']}次")
            if fitness_config.get('available_equipment'):
                equipment = fitness_config['available_equipment']
                if isinstance(equipment, list):
                    lines.append(f"- 可用器械: {', '.join(equipment)}")
                else:
                    lines.append(f"- 可用器械: {equipment}")
            lines.append("")

        # 健身目标
        fitness_goals = user_profile.get('fitness_goals', {})
        if fitness_goals:
            lines.append("**健身目标：**")
            primary_goal = fitness_goals.get('primary_goal')
            if primary_goal:
                lines.append(f"- 主要目标: {primary_goal}")
            secondary_goals = fitness_goals.get('secondary_goals', [])
            if secondary_goals:
                lines.append(f"- 次要目标: {', '.join(secondary_goals)}")
            lines.append("")

        # 健康状况
        health_profile = user_profile.get('health_profile', {})
        if health_profile:
            lines.append("**健康状况：**")
            injuries = health_profile.get('injuries', [])
            if injuries:
                lines.append(f"- 损伤史: {', '.join(injuries)}")
            medical_conditions = health_profile.get('medical_conditions', [])
            if medical_conditions:
                lines.append(f"- 健康状况: {', '.join(medical_conditions)}")
            lines.append("")

        return "\n".join(lines)

    def _format_tool_results(self, tool_results: Dict[str, Any]) -> str:
        """格式化工具结果"""
        lines = []

        for tool_name, result in tool_results.items():
            # 跳过用户档案（已单独显示）
            if tool_name in ['user_profile', 'get_user_profile']:
                continue

            lines.append(f"### {tool_name}\n")

            if isinstance(result, dict):
                # 字典类型：格式化为键值对
                for key, value in result.items():
                    if isinstance(value, (list, dict)):
                        lines.append(f"**{key}:**")
                        lines.append(f"```json")
                        lines.append(json.dumps(value, ensure_ascii=False, indent=2))
                        lines.append(f"```")
                    else:
                        lines.append(f"- **{key}**: {value}")
            elif isinstance(result, list):
                # 列表类型：格式化为列表项
                if len(result) > 0:
                    lines.append(f"共 {len(result)} 项：")
                    for i, item in enumerate(result[:10], 1):  # 最多显示10项
                        if isinstance(item, dict):
                            # 提取关键字段
                            name = item.get('name', item.get('exercise_name', f'项目{i}'))
                            lines.append(f"{i}. {name}")
                        else:
                            lines.append(f"{i}. {item}")
                    if len(result) > 10:
                        lines.append(f"... 还有 {len(result) - 10} 项")
                else:
                    lines.append("（无数据）")
            else:
                # 其他类型：直接显示
                lines.append(f"{result}")

            lines.append("")

        return "\n".join(lines)

    def parse_analysis_response(
        self,
        llm_output: str,
        request: AnalysisRequest,
        model_used: str
    ) -> AnalysisResult:
        """
        解析LLM分析结果

        Args:
            llm_output: LLM输出文本
            request: 原始请求
            model_used: 使用的模型

        Returns:
            AnalysisResult: 解析后的分析结果
        """
        try:
            # 提取专业分析
            professional_analysis = self._extract_section(
                llm_output,
                ["专业分析", "### 1. 专业分析", "## 专业分析"]
            )

            # 提取个性化建议
            recommendations_text = self._extract_section(
                llm_output,
                ["个性化建议", "### 2. 个性化建议", "## 个性化建议"]
            )
            personalized_recommendations = self._parse_recommendations(recommendations_text)

            # 提取安全提醒
            safety_text = self._extract_section(
                llm_output,
                ["安全提醒", "### 3. 安全提醒", "## 安全提醒"]
            )
            safety_reminders = self._parse_safety_reminders(safety_text)

            # 提取推理依据
            reasoning_text = self._extract_section(
                llm_output,
                ["推理依据", "### 4. 推理依据", "## 推理依据"]
            )
            reasoning_basis = self._parse_reasoning_basis(reasoning_text)

            # 计算置信度（基于输出质量）
            confidence = self._calculate_confidence(
                professional_analysis,
                personalized_recommendations,
                safety_reminders,
                reasoning_basis
            )

            return AnalysisResult(
                professional_analysis=professional_analysis or llm_output,
                personalized_recommendations=personalized_recommendations,
                safety_reminders=safety_reminders,
                reasoning_basis=reasoning_basis,
                confidence=confidence,
                model_used=model_used,
                analysis_metadata={
                    "contraindications_count": len(request.contraindications),
                    "tools_used": list(request.tool_results.keys()),
                    "output_length": len(llm_output)
                }
            )

        except Exception as e:
            logger.error(f"解析LLM响应失败: {e}", exc_info=True)
            # 返回原始输出
            return AnalysisResult(
                professional_analysis=llm_output,
                personalized_recommendations=[],
                safety_reminders=[],
                reasoning_basis={},
                confidence=0.5,
                model_used=model_used,
                analysis_metadata={"parse_error": str(e)}
            )

    def _extract_section(self, text: str, section_markers: List[str]) -> str:
        """提取文本中的特定章节"""
        for marker in section_markers:
            if marker in text:
                # 找到章节开始位置
                start_idx = text.find(marker)
                # 找到下一个章节标记（### 或 ##）
                next_section_idx = text.find("\n##", start_idx + len(marker))
                if next_section_idx == -1:
                    # 如果没有下一个章节，取到文本末尾
                    section_text = text[start_idx + len(marker):].strip()
                else:
                    section_text = text[start_idx + len(marker):next_section_idx].strip()
                return section_text
        return ""

    def _parse_recommendations(self, text: str) -> List[str]:
        """解析建议列表"""
        if not text:
            return []

        recommendations = []
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            # 匹配列表项（1. 2. 3. 或 - 开头）
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                # 移除列表标记
                recommendation = line.lstrip('0123456789.-•').strip()
                if recommendation:
                    recommendations.append(recommendation)

        return recommendations

    def _parse_safety_reminders(self, text: str) -> List[str]:
        """解析安全提醒列表"""
        return self._parse_recommendations(text)  # 使用相同的解析逻辑

    def _parse_reasoning_basis(self, text: str) -> Dict[str, List[str]]:
        """解析推理依据"""
        if not text:
            return {}

        reasoning = {}
        current_tool = None
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测工具名称（通常是粗体或特殊标记）
            if '**' in line or line.endswith(':'):
                current_tool = line.replace('**', '').replace(':', '').strip()
                reasoning[current_tool] = []
            elif current_tool and (line.startswith('-') or line.startswith('•')):
                # 添加到当前工具的依据列表
                basis = line.lstrip('-•').strip()
                if basis:
                    reasoning[current_tool].append(basis)

        return reasoning

    def _calculate_confidence(
        self,
        professional_analysis: str,
        recommendations: List[str],
        safety_reminders: List[str],
        reasoning_basis: Dict[str, List[str]]
    ) -> float:
        """计算分析结果的置信度"""
        confidence = 0.0

        # 专业分析存在且有内容 (+0.3)
        if professional_analysis and len(professional_analysis) > 100:
            confidence += 0.3

        # 建议数量合理 (+0.3)
        if 3 <= len(recommendations) <= 7:
            confidence += 0.3
        elif len(recommendations) > 0:
            confidence += 0.15

        # 安全提醒存在 (+0.2)
        if len(safety_reminders) > 0:
            confidence += 0.2

        # 推理依据完整 (+0.2)
        if len(reasoning_basis) > 0:
            confidence += 0.2

        return min(confidence, 1.0)

    def _create_fallback_response(
        self,
        request: AnalysisRequest,
        error_message: str
    ) -> AnalysisResult:
        """创建降级响应"""
        return AnalysisResult(
            professional_analysis=f"抱歉，分析过程中出现了错误：{error_message}。请稍后重试。",
            personalized_recommendations=[
                "建议咨询专业健身教练获取个性化指导",
                "确保训练前进行充分热身",
                "注意倾听身体信号，避免过度训练"
            ],
            safety_reminders=[
                "如有任何不适，请立即停止训练并咨询医生",
                "遵循渐进式训练原则，不要急于求成"
            ],
            reasoning_basis={
                "error": [error_message]
            },
            confidence=0.0,
            model_used="fallback",
            analysis_metadata={
                "error": error_message,
                "fallback": True
            }
        )
