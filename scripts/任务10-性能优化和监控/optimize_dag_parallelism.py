# -*- coding: utf-8 -*-
"""
DAG编排并行执行优化脚本

分析DAG任务依赖关系，优化并行执行策略。

优化措施:
1. 分析任务依赖图
2. 识别可并行执行的任务
3. 优化任务调度策略
4. 测量并行效率提升

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-16
"""

import asyncio
import time
import logging
from typing import Dict, List, Set, Any
from dataclasses import dataclass, field
import json
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TaskExecutionMetrics:
    """任务执行指标"""
    task_name: str
    execution_time: float
    dependencies: List[str] = field(default_factory=list)
    parallel_group: int = 0


@dataclass
class DAGOptimizationReport:
    """DAG优化报告"""
    total_tasks: int
    sequential_time: float
    parallel_time: float
    speedup: float
    parallel_groups: List[List[str]]
    bottleneck_tasks: List[str]
    recommendations: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class DAGParallelismOptimizer:
    """DAG并行执行优化器"""
    
    def __init__(self):
        self.task_metrics: Dict[str, TaskExecutionMetrics] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
    
    def analyze_dag_template(self, template) -> DAGOptimizationReport:
        """
        分析DAG模板的并行执行潜力
        
        Args:
            template: DAG模板对象
            
        Returns:
            DAGOptimizationReport: 优化报告
        """
        logger.info(f"分析DAG模板: {template.name}")
        
        # 1. 构建依赖图
        self._build_dependency_graph(template)
        
        # 2. 识别并行组
        parallel_groups = self._identify_parallel_groups()
        
        # 3. 计算理论加速比
        sequential_time, parallel_time, speedup = self._calculate_speedup(parallel_groups)
        
        # 4. 识别瓶颈任务
        bottleneck_tasks = self._identify_bottlenecks()
        
        # 5. 生成优化建议
        recommendations = self._generate_recommendations(
            parallel_groups,
            bottleneck_tasks,
            speedup
        )
        
        report = DAGOptimizationReport(
            total_tasks=len(template.required_tools) + len(template.optional_tools),
            sequential_time=sequential_time,
            parallel_time=parallel_time,
            speedup=speedup,
            parallel_groups=parallel_groups,
            bottleneck_tasks=bottleneck_tasks,
            recommendations=recommendations
        )
        
        return report
    
    def _build_dependency_graph(self, template):
        """构建任务依赖图"""
        logger.info("构建任务依赖图...")
        
        # 初始化依赖图
        all_tools = template.required_tools + template.optional_tools
        for tool in all_tools:
            self.dependency_graph[tool] = set()
        
        # 分析依赖关系（基于工具特性）
        # 用户档案工具：无依赖
        if "get-user-profile" in all_tools:
            self.dependency_graph["get-user-profile"] = set()
        
        # 基础计算工具：依赖用户档案
        basic_tools = ["tdee-calculator", "assess-strength-level", "rpe-recommender"]
        for tool in basic_tools:
            if tool in all_tools:
                if "get-user-profile" in all_tools:
                    self.dependency_graph[tool] = {"get-user-profile"}
                else:
                    self.dependency_graph[tool] = set()
        
        # 动作选择工具：依赖用户档案
        if "intelligent-exercise-selector" in all_tools:
            if "get-user-profile" in all_tools:
                self.dependency_graph["intelligent-exercise-selector"] = {"get-user-profile"}
            else:
                self.dependency_graph["intelligent-exercise-selector"] = set()
        
        # 安全检查工具：依赖动作选择
        safety_tools = ["contraindications-checker", "injury-risk-assessor"]
        for tool in safety_tools:
            if tool in all_tools:
                deps = set()
                if "intelligent-exercise-selector" in all_tools:
                    deps.add("intelligent-exercise-selector")
                if "get-user-profile" in all_tools:
                    deps.add("get-user-profile")
                self.dependency_graph[tool] = deps
        
        # 训练计划工具：依赖多个前置工具
        if "professional-program-designer" in all_tools:
            deps = set()
            for dep_tool in ["intelligent-exercise-selector", "tdee-calculator", "get-user-profile"]:
                if dep_tool in all_tools:
                    deps.add(dep_tool)
            self.dependency_graph["professional-program-designer"] = deps
        
        logger.info(f"依赖图构建完成，共 {len(self.dependency_graph)} 个任务")
    
    def _identify_parallel_groups(self) -> List[List[str]]:
        """识别可并行执行的任务组"""
        logger.info("识别并行执行组...")
        
        parallel_groups = []
        remaining_tasks = set(self.dependency_graph.keys())
        completed_tasks = set()
        
        while remaining_tasks:
            # 找出当前可执行的任务（依赖已满足）
            current_group = []
            for task in remaining_tasks:
                deps = self.dependency_graph[task]
                if deps.issubset(completed_tasks):
                    current_group.append(task)
            
            if not current_group:
                # 如果没有可执行的任务，说明有循环依赖
                logger.warning(f"检测到循环依赖或孤立任务: {remaining_tasks}")
                break
            
            parallel_groups.append(current_group)
            completed_tasks.update(current_group)
            remaining_tasks -= set(current_group)
        
        logger.info(f"识别到 {len(parallel_groups)} 个并行组")
        for i, group in enumerate(parallel_groups, 1):
            logger.info(f"  组{i}: {len(group)}个任务 - {group}")
        
        return parallel_groups
    
    def _calculate_speedup(
        self,
        parallel_groups: List[List[str]]
    ) -> tuple[float, float, float]:
        """计算理论加速比"""
        # 假设每个任务平均耗时100ms
        avg_task_time = 100.0
        
        # 顺序执行时间
        total_tasks = sum(len(group) for group in parallel_groups)
        sequential_time = total_tasks * avg_task_time
        
        # 并行执行时间（每组取最长任务）
        parallel_time = len(parallel_groups) * avg_task_time
        
        # 加速比
        speedup = sequential_time / parallel_time if parallel_time > 0 else 1.0
        
        logger.info(f"理论性能:")
        logger.info(f"  顺序执行: {sequential_time:.0f}ms")
        logger.info(f"  并行执行: {parallel_time:.0f}ms")
        logger.info(f"  加速比: {speedup:.2f}x")
        
        return sequential_time, parallel_time, speedup
    
    def _identify_bottlenecks(self) -> List[str]:
        """识别瓶颈任务"""
        bottlenecks = []
        
        # 瓶颈1：被多个任务依赖的任务
        dependency_count = {}
        for task, deps in self.dependency_graph.items():
            for dep in deps:
                dependency_count[dep] = dependency_count.get(dep, 0) + 1
        
        # 找出被依赖次数最多的任务
        if dependency_count:
            max_deps = max(dependency_count.values())
            for task, count in dependency_count.items():
                if count >= max_deps and count > 1:
                    bottlenecks.append(task)
        
        logger.info(f"识别到 {len(bottlenecks)} 个瓶颈任务: {bottlenecks}")
        
        return bottlenecks
    
    def _generate_recommendations(
        self,
        parallel_groups: List[List[str]],
        bottleneck_tasks: List[str],
        speedup: float
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 建议1：并行执行策略
        if len(parallel_groups) > 1:
            recommendations.append(
                f"✅ 启用并行执行：识别到 {len(parallel_groups)} 个并行组，"
                f"理论加速比 {speedup:.2f}x"
            )
            recommendations.append(
                "  实施方式：使用 asyncio.gather() 并行执行同组任务"
            )
        else:
            recommendations.append(
                "⚠️  当前DAG任务依赖链较长，并行潜力有限"
            )
        
        # 建议2：瓶颈优化
        if bottleneck_tasks:
            recommendations.append(
                f"🔧 优化瓶颈任务：{', '.join(bottleneck_tasks)}"
            )
            recommendations.append(
                "  - 为瓶颈任务启用缓存"
            )
            recommendations.append(
                "  - 优化瓶颈任务的执行效率"
            )
            recommendations.append(
                "  - 考虑预加载瓶颈任务结果"
            )
        
        # 建议3：依赖优化
        recommendations.append(
            "📊 依赖关系优化："
        )
        recommendations.append(
            "  - 减少不必要的任务依赖"
        )
        recommendations.append(
            "  - 将串行任务改为并行（如果逻辑允许）"
        )
        recommendations.append(
            "  - 使用懒加载策略（按需执行可选任务）"
        )
        
        # 建议4：资源管理
        recommendations.append(
            "⚡ 资源管理优化："
        )
        recommendations.append(
            "  - 限制并发任务数（避免资源耗尽）"
        )
        recommendations.append(
            "  - 使用信号量控制并发度"
        )
        recommendations.append(
            "  - 实现任务优先级队列"
        )
        
        return recommendations
    
    def print_report(self, report: DAGOptimizationReport):
        """打印优化报告"""
        print("\n" + "="*80)
        print("DAG并行执行优化报告")
        print("="*80)
        print(f"生成时间: {report.timestamp}")
        print(f"总任务数: {report.total_tasks}")
        print()
        
        print("📊 性能分析:")
        print(f"  顺序执行时间: {report.sequential_time:.0f}ms")
        print(f"  并行执行时间: {report.parallel_time:.0f}ms")
        print(f"  理论加速比: {report.speedup:.2f}x")
        print()
        
        print("🔀 并行执行组:")
        for i, group in enumerate(report.parallel_groups, 1):
            print(f"  组{i} ({len(group)}个任务): {', '.join(group)}")
        print()
        
        if report.bottleneck_tasks:
            print("⚠️  瓶颈任务:")
            for task in report.bottleneck_tasks:
                print(f"  - {task}")
            print()
        
        print("💡 优化建议:")
        for rec in report.recommendations:
            print(rec)
        print()
        
        print("="*80)
    
    def save_report(self, report: DAGOptimizationReport, filepath: str):
        """保存优化报告"""
        report_data = {
            "timestamp": report.timestamp,
            "total_tasks": report.total_tasks,
            "performance": {
                "sequential_time_ms": report.sequential_time,
                "parallel_time_ms": report.parallel_time,
                "speedup": report.speedup
            },
            "parallel_groups": report.parallel_groups,
            "bottleneck_tasks": report.bottleneck_tasks,
            "recommendations": report.recommendations
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"优化报告已保存到: {filepath}")


async def main():
    """主函数"""
    import sys
    import os
    
    # 添加项目路径
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
    
    from applications.fitness.dag_template_system import DAGTemplateManager
    
    # 创建优化器
    optimizer = DAGParallelismOptimizer()
    
    # 加载DAG模板系统
    template_system = DAGTemplateManager()
    
    # 分析所有模板
    all_reports = []
    
    for template_name, template in template_system.templates.items():
        logger.info(f"\n{'='*80}")
        logger.info(f"分析模板: {template_name}")
        logger.info(f"{'='*80}")
        
        report = optimizer.analyze_dag_template(template)
        optimizer.print_report(report)
        
        all_reports.append({
            "template_name": template_name,
            "report": report
        })
        
        # 重置优化器状态
        optimizer.dependency_graph = {}
    
    # 保存所有报告
    reports_dir = "reports/performance"
    os.makedirs(reports_dir, exist_ok=True)
    
    for item in all_reports:
        template_name = item["template_name"]
        report = item["report"]
        filepath = f"{reports_dir}/dag_parallelism_{template_name}.json"
        optimizer.save_report(report, filepath)
    
    logger.info(f"\n✅ 所有DAG模板分析完成，共 {len(all_reports)} 个模板")


if __name__ == "__main__":
    asyncio.run(main())
