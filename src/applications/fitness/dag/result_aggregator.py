# -*- coding: utf-8 -*-
"""
DAG结果汇总器

负责汇总DAG执行结果，包括：
1. 结果合并和格式化
2. LLM格式化输出
3. 错误汇总

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-28
"""

import logging
from typing import Dict, List, Any, Optional

from .models import DAGExecutionResult, TaskResult

logger = logging.getLogger(__name__)


class ResultAggregator:
    """
    结果汇总器
    
    负责汇总和格式化DAG执行结果。
    """

    def __init__(self):
        pass

    def aggregate_results(
        self,
        execution_result: DAGExecutionResult,
        include_errors: bool = True,
        include_metrics: bool = True
    ) -> Dict[str, Any]:
        """
        汇总执行结果
        
        Args:
            execution_result: DAG执行结果
            include_errors: 是否包含错误信息
            include_metrics: 是否包含性能指标
            
        Returns:
            Dict[str, Any]: 汇总后的结果
        """
        aggregated = {
            "execution_id": execution_result.execution_id,
            "success": execution_result.success,
            "summary": self._generate_summary(execution_result),
            "tool_results": self._format_tool_results(execution_result.results),
        }
        
        if include_errors and execution_result.errors:
            aggregated["errors"] = execution_result.errors
        
        if include_metrics:
            aggregated["metrics"] = {
                "total_time": execution_result.total_time,
                "levels_executed": execution_result.levels_executed,
                "tasks_completed": execution_result.tasks_completed,
                "tasks_failed": execution_result.tasks_failed,
                "tasks_skipped": execution_result.tasks_skipped,
                "success_rate": execution_result.success_rate,
                "average_task_time": execution_result.average_task_time,
            }
        
        return aggregated

    def _generate_summary(self, execution_result: DAGExecutionResult) -> str:
        """生成执行摘要"""
        if execution_result.success:
            return (
                f"DAG执行成功: 完成 {execution_result.tasks_completed} 个任务, "
                f"跳过 {execution_result.tasks_skipped} 个任务, "
                f"耗时 {execution_result.total_time:.2f}s"
            )
        else:
            return (
                f"DAG执行部分失败: 完成 {execution_result.tasks_completed} 个任务, "
                f"失败 {execution_result.tasks_failed} 个任务, "
                f"跳过 {execution_result.tasks_skipped} 个任务"
            )

    def _format_tool_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """格式化工具结果"""
        formatted = {}
        
        for tool_name, result in results.items():
            if tool_name.startswith("_"):
                continue  # 跳过内部字段如_context
            
            if isinstance(result, dict):
                if result.get("skipped"):
                    formatted[tool_name] = {
                        "status": "skipped",
                        "reason": result.get("reason", "未知原因")
                    }
                elif result.get("success") is False:
                    formatted[tool_name] = {
                        "status": "failed",
                        "error": result.get("error", "未知错误")
                    }
                else:
                    formatted[tool_name] = {
                        "status": "success",
                        "data": self._extract_key_data(tool_name, result)
                    }
            else:
                formatted[tool_name] = {
                    "status": "success",
                    "data": result
                }
        
        return formatted

    def _extract_key_data(self, tool_name: str, result: Dict[str, Any]) -> Any:
        """提取工具结果的关键数据"""
        # 根据工具类型提取关键数据
        key_extractors = {
            "get_user_profile": lambda r: r.get("profile", r),
            "intelligent_exercise_selector": lambda r: r.get("recommendations", r.get("selected_exercises", r)),
            "professional_program_designer": lambda r: r.get("program", r),
            "tdee_calculator": lambda r: {
                "tdee": r.get("tdee"),
                "bmr": r.get("bmr"),
                "target_calories": r.get("target_calories")
            },
            "meal_plan_designer": lambda r: r.get("meal_plan", r),
            "contraindications_checker": lambda r: r.get("contraindications", r),
            "injury_risk_assessor": lambda r: r.get("risk_assessment", r),
        }
        
        extractor = key_extractors.get(tool_name, lambda r: r)
        return extractor(result)

    def format_for_llm(
        self,
        execution_result: DAGExecutionResult,
        max_length: int = 4000
    ) -> str:
        """
        格式化结果供LLM使用
        
        Args:
            execution_result: DAG执行结果
            max_length: 最大长度限制
            
        Returns:
            str: 格式化后的文本
        """
        lines = []
        
        # 执行摘要
        lines.append("## DAG执行结果摘要")
        lines.append(f"- 执行ID: {execution_result.execution_id}")
        lines.append(f"- 状态: {'成功' if execution_result.success else '部分失败'}")
        lines.append(f"- 完成任务: {execution_result.tasks_completed}")
        lines.append(f"- 失败任务: {execution_result.tasks_failed}")
        lines.append(f"- 跳过任务: {execution_result.tasks_skipped}")
        lines.append(f"- 总耗时: {execution_result.total_time:.2f}s")
        lines.append("")
        
        # 工具结果
        lines.append("## 工具执行结果")
        for tool_name, result in execution_result.results.items():
            if tool_name.startswith("_"):
                continue
            
            if isinstance(result, dict):
                if result.get("skipped"):
                    lines.append(f"### {tool_name} (已跳过)")
                    lines.append(f"原因: {result.get('reason', '未知')}")
                elif result.get("success") is False:
                    lines.append(f"### {tool_name} (失败)")
                    lines.append(f"错误: {result.get('error', '未知')}")
                else:
                    lines.append(f"### {tool_name} (成功)")
                    key_data = self._extract_key_data(tool_name, result)
                    lines.append(self._format_data_for_llm(key_data))
            lines.append("")
        
        # 错误信息
        if execution_result.errors:
            lines.append("## 错误信息")
            for tool_name, error in execution_result.errors.items():
                lines.append(f"- {tool_name}: {error}")
        
        # 截断处理
        text = "\n".join(lines)
        if len(text) > max_length:
            text = text[:max_length - 100] + "\n\n... (结果已截断)"
        
        return text

    def _format_data_for_llm(self, data: Any, indent: int = 0) -> str:
        """格式化数据供LLM阅读"""
        prefix = "  " * indent
        
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}- {key}:")
                    lines.append(self._format_data_for_llm(value, indent + 1))
                else:
                    lines.append(f"{prefix}- {key}: {value}")
            return "\n".join(lines)
        elif isinstance(data, list):
            if len(data) == 0:
                return f"{prefix}(空列表)"
            elif len(data) <= 3:
                lines = []
                for i, item in enumerate(data):
                    lines.append(f"{prefix}{i + 1}. {self._format_data_for_llm(item, indent + 1)}")
                return "\n".join(lines)
            else:
                lines = []
                for i, item in enumerate(data[:3]):
                    lines.append(f"{prefix}{i + 1}. {self._format_data_for_llm(item, indent + 1)}")
                lines.append(f"{prefix}... 还有 {len(data) - 3} 项")
                return "\n".join(lines)
        else:
            return f"{prefix}{data}"

    def merge_results(
        self,
        results: List[DAGExecutionResult]
    ) -> Dict[str, Any]:
        """
        合并多个执行结果
        
        Args:
            results: 执行结果列表
            
        Returns:
            Dict[str, Any]: 合并后的结果
        """
        if not results:
            return {}
        
        merged = {
            "execution_ids": [r.execution_id for r in results],
            "overall_success": all(r.success for r in results),
            "total_time": sum(r.total_time for r in results),
            "total_tasks_completed": sum(r.tasks_completed for r in results),
            "total_tasks_failed": sum(r.tasks_failed for r in results),
            "total_tasks_skipped": sum(r.tasks_skipped for r in results),
            "results": {},
            "errors": {}
        }
        
        for result in results:
            merged["results"].update(result.results)
            merged["errors"].update(result.errors)
        
        return merged

    def extract_tool_result(
        self,
        execution_result: DAGExecutionResult,
        tool_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        提取特定工具的结果
        
        Args:
            execution_result: DAG执行结果
            tool_name: 工具名称
            
        Returns:
            Optional[Dict[str, Any]]: 工具结果
        """
        return execution_result.get_result(tool_name)

    def get_successful_tools(
        self,
        execution_result: DAGExecutionResult
    ) -> List[str]:
        """获取成功执行的工具列表"""
        successful = []
        for tool_name, result in execution_result.results.items():
            if tool_name.startswith("_"):
                continue
            if isinstance(result, dict):
                if not result.get("skipped") and result.get("success") is not False:
                    successful.append(tool_name)
            else:
                successful.append(tool_name)
        return successful

    def get_failed_tools(
        self,
        execution_result: DAGExecutionResult
    ) -> List[str]:
        """获取失败的工具列表"""
        return list(execution_result.errors.keys())

    def get_skipped_tools(
        self,
        execution_result: DAGExecutionResult
    ) -> List[str]:
        """获取跳过的工具列表"""
        skipped = []
        for tool_name, result in execution_result.results.items():
            if tool_name.startswith("_"):
                continue
            if isinstance(result, dict) and result.get("skipped"):
                skipped.append(tool_name)
        return skipped
