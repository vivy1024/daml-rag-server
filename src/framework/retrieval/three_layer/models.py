# -*- coding: utf-8 -*-
"""
三层检索引擎 - 数据模型定义
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class LayerExecutionResult:
    """单层检索执行结果"""
    layer_name: str
    success: bool
    results: List[Dict[str, Any]]
    execution_time_ms: float
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ThreeLayerResult:
    """三层检索最终结果"""
    query: str
    domain: str
    final_results: List[Dict[str, Any]]
    layer_1_result: LayerExecutionResult
    layer_2_result: LayerExecutionResult
    layer_3_result: LayerExecutionResult
    total_confidence: float
    total_execution_time_ms: float
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def final_recommendations(self) -> List[Dict[str, Any]]:
        """Framework层兼容性属性"""
        return self.final_results
