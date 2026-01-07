# -*- coding: utf-8 -*-
"""
DAG可视化器测试

测试DAG结构可视化、执行日志输出和调试模式功能。

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-12
"""

import pytest
import time
from src.framework.monitoring.dag_visualizer import (
    DAGVisualizer,
    VisualizationFormat,
    LogLevel,
    ExecutionLogEntry
)


class TestDAGVisualizer:
    """DAG可视化器测试类"""
    
    @pytest.fixture
    def visualizer(self):
        """创建可视化器实例"""
        return DAGVisualizer(debug_mode=False, log_level=LogLevel.NORMAL)
    
    @pytest.fixture
    def debug_visualizer(self):
        """创建调试模式的可视化器实例"""
        return DAGVisualizer(debug_mode=True, log_level=LogLevel.DEBUG)
    
    @pytest.fixture
    def sample_dag(self):
        """示例DAG结构"""
        return {
            "template_name": "完整训练计划",
            "tools": [
                "get_user_profile",
                "contraindications_checker",
                "injury_risk_assessor",
                "intelligent_exercise_selector",
                "muscle_group_volume_calculator",
                "professional_program_designer"
            ],
            "dependencies": {
                "get_user_profile": [],
                "contraindications_checker": ["get_user_profile"],
                "injury_risk_assessor": ["get_user_profile"],
                "intelligent_exercise_selector": ["contraindications_checker", "injury_risk_assessor"],
                "muscle_group_volume_calculator": ["get_user_profile"],
                "professional_program_designer": ["intelligent_exercise_selector", "muscle_group_volume_calculator"]
            },
            "parallel_groups": [
                ["get_user_profile"],
                ["contraindications_checker", "injury_risk_assessor", "muscle_group_volume_calculator"],
                ["intelligent_exercise_selector"],
                ["professional_program_designer"]
            ]
        }
    
    def test_visualizer_initialization(self, visualizer):
        """测试可视化器初始化"""
        assert visualizer is not None
        assert visualizer.debug_mode == False
        assert visualizer.log_level == LogLevel.NORMAL
        assert len(visualizer.execution_logs) == 0
    
    def test_debug_visualizer_initialization(self, debug_visualizer):
        """测试调试模式可视化器初始化"""
        assert debug_visualizer.debug_mode == True
        assert debug_visualizer.log_level == LogLevel.DEBUG
    
    def test_ascii_visualization(self, visualizer, sample_dag):
        """测试ASCII可视化"""
        result = visualizer.visualize_dag_structure(
            sample_dag["template_name"],
            sample_dag["tools"],
            sample_dag["dependencies"],
            sample_dag["parallel_groups"],
            VisualizationFormat.ASCII
        )
        
        assert result is not None
        assert result.format == "ascii"
        assert "完整训练计划" in result.content
        assert "层级" in result.content
        assert "统计信息" in result.content
        assert result.metadata["total_tools"] == 6
        assert result.metadata["parallel_groups_count"] == 4
    
    def test_mermaid_visualization(self, visualizer, sample_dag):
        """测试Mermaid可视化"""
        result = visualizer.visualize_dag_structure(
            sample_dag["template_name"],
            sample_dag["tools"],
            sample_dag["dependencies"],
            sample_dag["parallel_groups"],
            VisualizationFormat.MERMAID
        )
        
        assert result is not None
        assert result.format == "mermaid"
        assert "```mermaid" in result.content
        assert "graph TD" in result.content
        assert "get_user_profile" in result.content
        assert "-->" in result.content
    
    def test_json_visualization(self, visualizer, sample_dag):
        """测试JSON可视化"""
        result = visualizer.visualize_dag_structure(
            sample_dag["template_name"],
            sample_dag["tools"],
            sample_dag["dependencies"],
            sample_dag["parallel_groups"],
            VisualizationFormat.JSON
        )
        
        assert result is not None
        assert result.format == "json"
        assert "template_name" in result.content
        assert "tools" in result.content
        assert "dependencies" in result.content
        
        # 验证JSON格式正确
        import json
        data = json.loads(result.content)
        assert data["template_name"] == "完整训练计划"
        assert len(data["tools"]) == 6
    
    def test_tree_visualization(self, visualizer, sample_dag):
        """测试树形可视化"""
        result = visualizer.visualize_dag_structure(
            sample_dag["template_name"],
            sample_dag["tools"],
            sample_dag["dependencies"],
            sample_dag["parallel_groups"],
            VisualizationFormat.TREE
        )
        
        assert result is not None
        assert result.format == "tree"
        assert "完整训练计划" in result.content
        assert "├──" in result.content or "└──" in result.content
    
    def test_log_tool_execution(self, visualizer):
        """测试工具执行日志"""
        visualizer.log_tool_execution(
            tool_name="get_user_profile",
            status="running",
            message="开始获取用户档案"
        )
        
        assert len(visualizer.execution_logs) == 1
        log = visualizer.execution_logs[0]
        assert log.tool_name == "get_user_profile"
        assert log.status == "running"
        assert log.message == "开始获取用户档案"
    
    def test_log_tool_execution_with_details(self, debug_visualizer):
        """测试带详细信息的工具执行日志"""
        details = {
            "user_id": "test_123",
            "params": {"age": 28, "gender": "男"}
        }
        
        debug_visualizer.log_tool_execution(
            tool_name="get_user_profile",
            status="completed",
            message="用户档案获取成功",
            details=details,
            duration=0.5
        )
        
        assert len(debug_visualizer.execution_logs) == 1
        log = debug_visualizer.execution_logs[0]
        assert log.details == details
        assert log.duration == 0.5
    
    def test_log_tool_execution_with_error(self, visualizer):
        """测试带错误信息的工具执行日志"""
        visualizer.log_tool_execution(
            tool_name="contraindications_checker",
            status="failed",
            message="禁忌检查失败",
            error="数据库连接超时",
            duration=2.0
        )
        
        assert len(visualizer.execution_logs) == 1
        log = visualizer.execution_logs[0]
        assert log.status == "failed"
        assert log.error == "数据库连接超时"
        assert log.level == "ERROR"
    
    def test_log_decision_process(self, debug_visualizer):
        """测试决策过程日志（调试模式）"""
        # 调试模式下应该记录决策过程
        debug_visualizer.log_decision_process(
            stage="DAG选择",
            decision="complete_training_plan",
            reason="用户需要完整的增肌训练计划",
            alternatives=["nutrition_plan", "exercise_selection"],
            confidence=0.95
        )
        
        # 决策过程不会添加到execution_logs，只是输出日志
        # 这里主要测试不会抛出异常
        assert True
    
    def test_log_decision_process_non_debug(self, visualizer):
        """测试非调试模式下的决策过程日志"""
        # 非调试模式下不应该记录决策过程
        visualizer.log_decision_process(
            stage="DAG选择",
            decision="complete_training_plan",
            reason="用户需要完整的增肌训练计划"
        )
        
        # 不应该有任何日志
        assert len(visualizer.execution_logs) == 0
    
    def test_get_execution_logs(self, visualizer):
        """测试获取执行日志"""
        # 添加多条日志
        visualizer.log_tool_execution("tool1", "completed", "完成1", duration=1.0)
        visualizer.log_tool_execution("tool2", "completed", "完成2", duration=2.0)
        visualizer.log_tool_execution("tool1", "failed", "失败", error="错误")
        
        # 获取所有日志
        all_logs = visualizer.get_execution_logs()
        assert len(all_logs) == 3
        
        # 按工具名过滤
        tool1_logs = visualizer.get_execution_logs(tool_name="tool1")
        assert len(tool1_logs) == 2
        
        # 按状态过滤
        failed_logs = visualizer.get_execution_logs(status="failed")
        assert len(failed_logs) == 1
        
        # 限制数量
        limited_logs = visualizer.get_execution_logs(limit=2)
        assert len(limited_logs) == 2
    
    def test_generate_execution_summary(self, visualizer):
        """测试生成执行摘要"""
        # 添加多条日志
        visualizer.log_tool_execution("tool1", "completed", "完成1", duration=1.0)
        visualizer.log_tool_execution("tool2", "completed", "完成2", duration=2.0)
        visualizer.log_tool_execution("tool3", "failed", "失败", duration=0.5)
        
        summary = visualizer.generate_execution_summary()
        
        assert "执行摘要" in summary
        assert "总日志数: 3" in summary
        assert "总执行时长: 3.50s" in summary
        assert "状态统计" in summary
        assert "工具统计" in summary
    
    def test_clear_logs(self, visualizer):
        """测试清空日志"""
        visualizer.log_tool_execution("tool1", "completed", "完成")
        assert len(visualizer.execution_logs) == 1
        
        visualizer.clear_logs()
        assert len(visualizer.execution_logs) == 0
    
    def test_export_logs_to_file(self, visualizer, tmp_path):
        """测试导出日志到文件"""
        # 添加日志
        visualizer.log_tool_execution("tool1", "completed", "完成1", duration=1.0)
        visualizer.log_tool_execution("tool2", "failed", "失败", error="错误")
        
        # 导出到临时文件
        filepath = tmp_path / "execution_logs.json"
        visualizer.export_logs_to_file(str(filepath))
        
        # 验证文件存在
        assert filepath.exists()
        
        # 验证文件内容
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            logs_data = json.load(f)
        
        assert len(logs_data) == 2
        assert logs_data[0]["tool_name"] == "tool1"
        assert logs_data[1]["tool_name"] == "tool2"
    
    def test_calculate_levels(self, visualizer, sample_dag):
        """测试层级计算"""
        levels = visualizer._calculate_levels(
            sample_dag["tools"],
            sample_dag["dependencies"]
        )
        
        assert len(levels) > 0
        # 第一层应该只有get_user_profile
        assert "get_user_profile" in levels[0]
        # 最后一层应该有professional_program_designer
        assert "professional_program_designer" in levels[-1]
    
    def test_find_last_level_tools(self, visualizer, sample_dag):
        """测试找到最后一层工具"""
        last_tools = visualizer._find_last_level_tools(
            sample_dag["tools"],
            sample_dag["dependencies"]
        )
        
        # professional_program_designer应该在最后一层
        assert "professional_program_designer" in last_tools
    
    def test_minimal_log_level(self):
        """测试最小日志级别"""
        visualizer = DAGVisualizer(debug_mode=False, log_level=LogLevel.MINIMAL)
        
        # 最小日志级别只记录完成和失败
        visualizer.log_tool_execution("tool1", "running", "运行中")
        assert len(visualizer.execution_logs) == 0
        
        visualizer.log_tool_execution("tool1", "completed", "完成")
        assert len(visualizer.execution_logs) == 1
        
        visualizer.log_tool_execution("tool2", "failed", "失败")
        assert len(visualizer.execution_logs) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
