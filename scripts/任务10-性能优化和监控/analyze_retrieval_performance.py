# -*- coding: utf-8 -*-
"""
三层检索性能分析工具

分析当前三层检索系统的性能瓶颈，并提供优化建议。

功能:
1. 分析Layer1向量检索性能
2. 分析Layer2图谱查询性能
3. 分析Layer3规则验证性能
4. 识别性能瓶颈
5. 生成优化建议

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-16
"""

import asyncio
import time
import statistics
import logging
from typing import Dict, List, Any
from dataclasses import dataclass, field
import json
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    operation: str
    samples: List[float] = field(default_factory=list)
    
    @property
    def avg_time(self) -> float:
        return statistics.mean(self.samples) if self.samples else 0.0
    
    @property
    def p50(self) -> float:
        return statistics.median(self.samples) if self.samples else 0.0
    
    @property
    def p95(self) -> float:
        if not self.samples or len(self.samples) < 20:
            return 0.0
        sorted_samples = sorted(self.samples)
        index = int(len(sorted_samples) * 0.95)
        return sorted_samples[index]
    
    @property
    def p99(self) -> float:
        if not self.samples or len(self.samples) < 100:
            return 0.0
        sorted_samples = sorted(self.samples)
        index = int(len(sorted_samples) * 0.99)
        return sorted_samples[index]
    
    @property
    def min_time(self) -> float:
        return min(self.samples) if self.samples else 0.0
    
    @property
    def max_time(self) -> float:
        return max(self.samples) if self.samples else 0.0


@dataclass
class PerformanceReport:
    """性能报告"""
    layer1_metrics: PerformanceMetrics
    layer2_metrics: PerformanceMetrics
    layer3_metrics: PerformanceMetrics
    total_metrics: PerformanceMetrics
    bottlenecks: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RetrievalPerformanceAnalyzer:
    """三层检索性能分析器"""
    
    def __init__(self):
        self.layer1_metrics = PerformanceMetrics(operation="Layer1-Vector")
        self.layer2_metrics = PerformanceMetrics(operation="Layer2-Graph")
        self.layer3_metrics = PerformanceMetrics(operation="Layer3-Rules")
        self.total_metrics = PerformanceMetrics(operation="Total-Retrieval")
        
        # 性能目标
        self.targets = {
            "layer1": 30.0,  # 30ms
            "layer2": 50.0,  # 50ms
            "layer3": 20.0,  # 20ms
            "total": 100.0   # 100ms
        }
    
    async def analyze_performance(
        self,
        test_queries: List[str],
        engine
    ) -> PerformanceReport:
        """
        分析三层检索性能
        
        Args:
            test_queries: 测试查询列表
            engine: 三层检索引擎实例
            
        Returns:
            PerformanceReport: 性能报告
        """
        logger.info(f"开始性能分析，测试查询数: {len(test_queries)}")
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"执行测试 {i}/{len(test_queries)}: {query}")
            
            try:
                # 执行查询并记录性能
                start_time = time.time()
                result = await engine.execute_three_layer_query(
                    query=query,
                    domain="fitness_exercises",
                    top_k=10
                )
                total_time = (time.time() - start_time) * 1000  # 转换为毫秒
                
                # 记录各层性能
                self.layer1_metrics.samples.append(result.layer_1_result.execution_time_ms)
                self.layer2_metrics.samples.append(result.layer_2_result.execution_time_ms)
                self.layer3_metrics.samples.append(result.layer_3_result.execution_time_ms)
                self.total_metrics.samples.append(total_time)
                
                logger.info(
                    f"  Layer1: {result.layer_1_result.execution_time_ms:.1f}ms, "
                    f"Layer2: {result.layer_2_result.execution_time_ms:.1f}ms, "
                    f"Layer3: {result.layer_3_result.execution_time_ms:.1f}ms, "
                    f"Total: {total_time:.1f}ms"
                )
                
            except Exception as e:
                logger.error(f"查询失败: {query}, 错误: {e}")
                continue
        
        # 生成报告
        report = self._generate_report()
        return report
    
    def _generate_report(self) -> PerformanceReport:
        """生成性能报告"""
        report = PerformanceReport(
            layer1_metrics=self.layer1_metrics,
            layer2_metrics=self.layer2_metrics,
            layer3_metrics=self.layer3_metrics,
            total_metrics=self.total_metrics
        )
        
        # 识别瓶颈
        report.bottlenecks = self._identify_bottlenecks()
        
        # 生成优化建议
        report.recommendations = self._generate_recommendations(report.bottlenecks)
        
        return report
    
    def _identify_bottlenecks(self) -> List[Dict[str, Any]]:
        """识别性能瓶颈"""
        bottlenecks = []
        
        # 检查Layer1
        if self.layer1_metrics.avg_time > self.targets["layer1"]:
            bottlenecks.append({
                "layer": "Layer1-Vector",
                "avg_time": self.layer1_metrics.avg_time,
                "target": self.targets["layer1"],
                "severity": "high" if self.layer1_metrics.avg_time > self.targets["layer1"] * 2 else "medium",
                "percentage": (self.layer1_metrics.avg_time / self.total_metrics.avg_time) * 100
            })
        
        # 检查Layer2
        if self.layer2_metrics.avg_time > self.targets["layer2"]:
            bottlenecks.append({
                "layer": "Layer2-Graph",
                "avg_time": self.layer2_metrics.avg_time,
                "target": self.targets["layer2"],
                "severity": "high" if self.layer2_metrics.avg_time > self.targets["layer2"] * 2 else "medium",
                "percentage": (self.layer2_metrics.avg_time / self.total_metrics.avg_time) * 100
            })
        
        # 检查Layer3
        if self.layer3_metrics.avg_time > self.targets["layer3"]:
            bottlenecks.append({
                "layer": "Layer3-Rules",
                "avg_time": self.layer3_metrics.avg_time,
                "target": self.targets["layer3"],
                "severity": "high" if self.layer3_metrics.avg_time > self.targets["layer3"] * 2 else "medium",
                "percentage": (self.layer3_metrics.avg_time / self.total_metrics.avg_time) * 100
            })
        
        # 检查总体性能
        if self.total_metrics.avg_time > self.targets["total"]:
            bottlenecks.append({
                "layer": "Total-Retrieval",
                "avg_time": self.total_metrics.avg_time,
                "target": self.targets["total"],
                "severity": "critical" if self.total_metrics.avg_time > self.targets["total"] * 2 else "high",
                "percentage": 100.0
            })
        
        # 按严重程度排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        bottlenecks.sort(key=lambda x: severity_order.get(x["severity"], 99))
        
        return bottlenecks
    
    def _generate_recommendations(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        for bottleneck in bottlenecks:
            layer = bottleneck["layer"]
            
            if layer == "Layer1-Vector":
                recommendations.extend([
                    "🔧 Layer1优化建议:",
                    "  1. 优化Qdrant向量索引配置（HNSW参数调优）",
                    "  2. 减少top_k召回数量（当前3倍，可降至2倍）",
                    "  3. 启用向量查询缓存",
                    "  4. 考虑使用更小的向量维度（当前1024维）",
                    "  5. 优化网络连接（使用连接池）"
                ])
            
            elif layer == "Layer2-Graph":
                recommendations.extend([
                    "🔧 Layer2优化建议:",
                    "  1. 为Neo4j查询添加索引（Muscle.name_zh, Exercise.name_zh）",
                    "  2. 优化Cypher查询语句（减少MATCH次数）",
                    "  3. 限制图谱遍历深度",
                    "  4. 启用Neo4j查询缓存",
                    "  5. 使用Neo4j连接池（已实现，检查配置）",
                    "  6. 考虑预计算常用图谱路径"
                ])
            
            elif layer == "Layer3-Rules":
                recommendations.extend([
                    "🔧 Layer3优化建议:",
                    "  1. 优化规则验证逻辑（减少循环次数）",
                    "  2. 缓存用户档案数据",
                    "  3. 并行执行独立的规则检查",
                    "  4. 提前终止（达到top_k后立即返回）",
                    "  5. 简化安全性检查逻辑"
                ])
            
            elif layer == "Total-Retrieval":
                recommendations.extend([
                    "🔧 总体优化建议:",
                    "  1. 启用Layer1和Layer2的并行执行（如果可能）",
                    "  2. 实现智能缓存预加载",
                    "  3. 优化数据序列化/反序列化",
                    "  4. 减少日志输出（生产环境）",
                    "  5. 使用异步I/O优化网络请求"
                ])
        
        # 添加通用建议
        if recommendations:
            recommendations.extend([
                "",
                "📊 监控建议:",
                "  1. 添加性能监控指标（Prometheus）",
                "  2. 设置性能告警阈值",
                "  3. 定期生成性能报告",
                "  4. 追踪慢查询日志"
            ])
        
        return recommendations
    
    def print_report(self, report: PerformanceReport):
        """打印性能报告"""
        print("\n" + "="*80)
        print("三层检索性能分析报告")
        print("="*80)
        print(f"生成时间: {report.timestamp}")
        print(f"测试样本数: {len(report.total_metrics.samples)}")
        print()
        
        # Layer1性能
        print("📊 Layer1 (向量检索) 性能:")
        print(f"  平均耗时: {report.layer1_metrics.avg_time:.2f}ms (目标: {self.targets['layer1']:.0f}ms)")
        print(f"  P50: {report.layer1_metrics.p50:.2f}ms")
        print(f"  P95: {report.layer1_metrics.p95:.2f}ms")
        print(f"  P99: {report.layer1_metrics.p99:.2f}ms")
        print(f"  最小/最大: {report.layer1_metrics.min_time:.2f}ms / {report.layer1_metrics.max_time:.2f}ms")
        print()
        
        # Layer2性能
        print("📊 Layer2 (图谱查询) 性能:")
        print(f"  平均耗时: {report.layer2_metrics.avg_time:.2f}ms (目标: {self.targets['layer2']:.0f}ms)")
        print(f"  P50: {report.layer2_metrics.p50:.2f}ms")
        print(f"  P95: {report.layer2_metrics.p95:.2f}ms")
        print(f"  P99: {report.layer2_metrics.p99:.2f}ms")
        print(f"  最小/最大: {report.layer2_metrics.min_time:.2f}ms / {report.layer2_metrics.max_time:.2f}ms")
        print()
        
        # Layer3性能
        print("📊 Layer3 (规则验证) 性能:")
        print(f"  平均耗时: {report.layer3_metrics.avg_time:.2f}ms (目标: {self.targets['layer3']:.0f}ms)")
        print(f"  P50: {report.layer3_metrics.p50:.2f}ms")
        print(f"  P95: {report.layer3_metrics.p95:.2f}ms")
        print(f"  P99: {report.layer3_metrics.p99:.2f}ms")
        print(f"  最小/最大: {report.layer3_metrics.min_time:.2f}ms / {report.layer3_metrics.max_time:.2f}ms")
        print()
        
        # 总体性能
        print("📊 总体检索性能:")
        print(f"  平均耗时: {report.total_metrics.avg_time:.2f}ms (目标: {self.targets['total']:.0f}ms)")
        print(f"  P50: {report.total_metrics.p50:.2f}ms")
        print(f"  P95: {report.total_metrics.p95:.2f}ms")
        print(f"  P99: {report.total_metrics.p99:.2f}ms")
        print(f"  最小/最大: {report.total_metrics.min_time:.2f}ms / {report.total_metrics.max_time:.2f}ms")
        print()
        
        # 性能瓶颈
        if report.bottlenecks:
            print("⚠️  性能瓶颈:")
            for bottleneck in report.bottlenecks:
                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }
                emoji = severity_emoji.get(bottleneck["severity"], "⚪")
                print(f"  {emoji} {bottleneck['layer']}: {bottleneck['avg_time']:.2f}ms "
                      f"(目标: {bottleneck['target']:.0f}ms, "
                      f"占比: {bottleneck['percentage']:.1f}%, "
                      f"严重程度: {bottleneck['severity']})")
            print()
        else:
            print("✅ 未发现性能瓶颈，所有指标均达标！")
            print()
        
        # 优化建议
        if report.recommendations:
            print("💡 优化建议:")
            for rec in report.recommendations:
                print(rec)
            print()
        
        print("="*80)
    
    def save_report(self, report: PerformanceReport, filepath: str):
        """保存性能报告到文件"""
        report_data = {
            "timestamp": report.timestamp,
            "metrics": {
                "layer1": {
                    "avg_time": report.layer1_metrics.avg_time,
                    "p50": report.layer1_metrics.p50,
                    "p95": report.layer1_metrics.p95,
                    "p99": report.layer1_metrics.p99,
                    "min": report.layer1_metrics.min_time,
                    "max": report.layer1_metrics.max_time,
                    "samples": len(report.layer1_metrics.samples)
                },
                "layer2": {
                    "avg_time": report.layer2_metrics.avg_time,
                    "p50": report.layer2_metrics.p50,
                    "p95": report.layer2_metrics.p95,
                    "p99": report.layer2_metrics.p99,
                    "min": report.layer2_metrics.min_time,
                    "max": report.layer2_metrics.max_time,
                    "samples": len(report.layer2_metrics.samples)
                },
                "layer3": {
                    "avg_time": report.layer3_metrics.avg_time,
                    "p50": report.layer3_metrics.p50,
                    "p95": report.layer3_metrics.p95,
                    "p99": report.layer3_metrics.p99,
                    "min": report.layer3_metrics.min_time,
                    "max": report.layer3_metrics.max_time,
                    "samples": len(report.layer3_metrics.samples)
                },
                "total": {
                    "avg_time": report.total_metrics.avg_time,
                    "p50": report.total_metrics.p50,
                    "p95": report.total_metrics.p95,
                    "p99": report.total_metrics.p99,
                    "min": report.total_metrics.min_time,
                    "max": report.total_metrics.max_time,
                    "samples": len(report.total_metrics.samples)
                }
            },
            "bottlenecks": report.bottlenecks,
            "recommendations": report.recommendations
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"性能报告已保存到: {filepath}")


async def main():
    """主函数"""
    import sys
    import os
    
    # 添加项目路径
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))
    
    from framework.retrieval.true_three_layer_engine import TrueThreeLayerEngine
    
    # 创建分析器
    analyzer = RetrievalPerformanceAnalyzer()
    
    # 测试查询
    test_queries = [
        "推荐胸部训练动作",
        "适合新手的腿部训练",
        "高级背部训练计划",
        "肩部力量训练动作",
        "核心稳定性训练",
        "手臂肌肉增长训练",
        "全身性训练动作",
        "适合家庭的训练动作",
        "增肌训练计划",
        "减脂训练动作"
    ]
    
    # 创建三层检索引擎
    engine = TrueThreeLayerEngine(
        graphrag_api_port="8001",
        enable_neo4j_direct=True
    )
    
    try:
        # 执行性能分析
        report = await analyzer.analyze_performance(test_queries, engine)
        
        # 打印报告
        analyzer.print_report(report)
        
        # 保存报告
        report_path = "daml-rag-server/reports/performance/retrieval_performance_report.json"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        analyzer.save_report(report, report_path)
        
    finally:
        # 关闭引擎
        engine.close()


if __name__ == "__main__":
    asyncio.run(main())
