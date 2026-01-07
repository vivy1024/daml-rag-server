# -*- coding: utf-8 -*-
"""
增强参数提取器 - Enhanced Parameter Extractor

继承ParameterExtractor，添加workflow state回退支持。
当上游任务不在DAG执行结果中时，从workflow state提取参数。

核心功能：
1. 从上游任务结果中提取参数（继承自ParameterExtractor）
2. 支持workflow state回退（新增）
3. 消除"上游任务不存在"警告（对于标准workflow数据）
4. 支持context和query_analysis的通用映射

版本: v1.0.0
日期: 2025-12-29
Requirements: 7.1, 7.2, 7.3
"""

import logging
from typing import Dict, List, Any, Optional

from .parameter_extractor import ParameterExtractor, ParamMapping

logger = logging.getLogger(__name__)


class EnhancedParameterExtractor(ParameterExtractor):
    """
    增强参数提取器 - 支持workflow state回退
    
    当上游任务不在DAG执行结果中时，从workflow state提取参数。
    这解决了"上游任务不存在"警告问题，特别是对于context和query_analysis。
    """
    
    # 标准workflow数据源映射
    # 定义从workflow state中提取参数的路径
    WORKFLOW_STATE_MAPPINGS: Dict[str, Dict[str, str]] = {
        "context": {
            # context任务的参数映射到workflow state的路径
            "user_id": "user_id",
            "query": "query",
            "session_id": "session_id",
            "user_profile": "user_profile",
        },
        "query_analysis": {
            # query_analysis任务的参数映射到workflow state的路径
            "intent": "query_analysis.intent",
            "entities": "query_analysis.entities",
            "constraints": "query_analysis.constraints",
            "complexity": "query_analysis.complexity",
            "confidence": "query_analysis.confidence",
        }
    }
    
    def __init__(self):
        """初始化增强参数提取器"""
        super().__init__()
        self.workflow_state_extractions = 0
        self.logger = logger
    
    def extract_from_upstream(
        self,
        param_mappings: List[ParamMapping],
        upstream_results: Dict[str, Any],
        context: Dict[str, Any],
        workflow_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        从上游任务结果中提取参数，支持workflow state回退
        
        Args:
            param_mappings: 参数映射配置列表
            upstream_results: 上游任务结果字典 {task_name: result}
            context: 全局上下文
            workflow_state: workflow状态（可选，用于回退提取）
            
        Returns:
            提取的参数字典
        """
        extracted_params = {}
        
        self.logger.info(f"🔍 开始增强参数提取，共 {len(param_mappings)} 个映射")
        self.logger.debug(f"🔍 workflow_state: {workflow_state}")
        
        for mapping in param_mappings:
            self.extraction_stats["total_extractions"] += 1
            
            try:
                value = None
                extraction_source = None
                
                # 1. 首先尝试从上游任务结果提取（排除标准workflow数据源）
                # 对于context和query_analysis，优先从workflow_state提取
                is_workflow_source = mapping.source_task in self.WORKFLOW_STATE_MAPPINGS
                
                if not is_workflow_source and mapping.source_task in upstream_results:
                    source_data = upstream_results[mapping.source_task]
                    if source_data:  # 确保source_data不为空
                        value = self._extract_by_path(source_data, mapping.source_path)
                        if value is not None:
                            extraction_source = f"upstream:{mapping.source_task}"
                            self.logger.debug(
                                f"✅ 从上游任务提取: {mapping.target_param} = {self._truncate_value(value)} "
                                f"(来自 {mapping.source_task})"
                            )
                
                # 2. 对于标准workflow数据源（context/query_analysis），从workflow_state提取
                if value is None and is_workflow_source:
                    self.logger.debug(f"🔍 尝试从workflow_state提取: source_task={mapping.source_task}, source_path={mapping.source_path}")
                    
                    if workflow_state:
                        # 从workflow state提取
                        state_mapping = self.WORKFLOW_STATE_MAPPINGS[mapping.source_task]
                        
                        # 获取source_path的第一部分作为key
                        source_key = mapping.source_path.split('.')[0]
                        self.logger.debug(f"🔍 source_key={source_key}, state_mapping keys={list(state_mapping.keys())}")
                        
                        if source_key in state_mapping:
                            state_path = state_mapping[source_key]
                            value = self._extract_by_path(workflow_state, state_path)
                            self.logger.debug(f"🔍 state_path={state_path}, extracted_value={value}")
                            
                            if value is not None:
                                extraction_source = f"workflow_state:{state_path}"
                                self.workflow_state_extractions += 1
                                self.logger.info(
                                    f"✅ 从workflow state提取: {mapping.target_param} = {self._truncate_value(value)} "
                                    f"(路径: {state_path})"
                                )
                        else:
                            # 尝试直接从workflow state提取完整路径
                            full_path = f"{mapping.source_task}.{mapping.source_path}"
                            value = self._extract_by_path(workflow_state, full_path)
                            if value is not None:
                                extraction_source = f"workflow_state:{full_path}"
                                self.workflow_state_extractions += 1
                                self.logger.info(
                                    f"✅ 从workflow state提取（完整路径）: {mapping.target_param} = {self._truncate_value(value)}"
                                )
                    else:
                        self.logger.warning(f"⚠️ workflow_state为空，无法提取 {mapping.target_param}")
                    
                    # 不记录警告，因为这是标准workflow数据的正常情况
                    if value is None and mapping.default_value is not None:
                        value = mapping.default_value
                        extraction_source = "default"
                        self.extraction_stats["default_value_used"] += 1
                        self.logger.debug(
                            f"📋 使用默认值（标准workflow数据）: {mapping.target_param} = {mapping.default_value}"
                        )
                
                # 3. 如果不是标准workflow数据且上游任务不存在，记录警告
                elif value is None and not is_workflow_source and mapping.source_task not in upstream_results:
                    self.logger.warning(
                        f"⚠️ 上游任务不存在: {mapping.source_task}\n"
                        f"   目标参数: {mapping.target_param}\n"
                        f"   使用默认值: {mapping.default_value}"
                    )
                    
                    if mapping.default_value is not None:
                        value = mapping.default_value
                        extraction_source = "default"
                        self.extraction_stats["default_value_used"] += 1
                
                # 4. 应用转换器
                if value is not None and mapping.converter:
                    value = self._apply_converter(value, mapping.converter)
                
                # 5. 设置提取的参数
                if value is not None:
                    extracted_params[mapping.target_param] = value
                    if extraction_source and extraction_source.startswith("upstream"):
                        self.extraction_stats["successful_extractions"] += 1
                    elif extraction_source and extraction_source.startswith("workflow_state"):
                        self.extraction_stats["successful_extractions"] += 1
                elif mapping.default_value is not None:
                    extracted_params[mapping.target_param] = mapping.default_value
                    self.extraction_stats["default_value_used"] += 1
                
            except Exception as e:
                self.extraction_stats["failed_extractions"] += 1
                self.logger.error(
                    f"❌ 参数提取失败: {mapping.target_param}\n"
                    f"   源任务: {mapping.source_task}\n"
                    f"   源路径: {mapping.source_path}\n"
                    f"   错误: {str(e)}"
                )
                
                # 使用默认值
                if mapping.default_value is not None:
                    extracted_params[mapping.target_param] = mapping.default_value
                    self.extraction_stats["default_value_used"] += 1
        
        self.logger.info(
            f"📊 增强参数提取完成: 成功 {self.extraction_stats['successful_extractions']}，"
            f"workflow state回退 {self.workflow_state_extractions}，"
            f"失败 {self.extraction_stats['failed_extractions']}，"
            f"使用默认值 {self.extraction_stats['default_value_used']}"
        )
        
        return extracted_params
    
    def _truncate_value(self, value: Any, max_length: int = 50) -> str:
        """截断值用于日志显示"""
        str_value = str(value)
        if len(str_value) > max_length:
            return str_value[:max_length] + "..."
        return str_value
    
    def extract_from_workflow_state(
        self,
        source_task: str,
        source_path: str,
        workflow_state: Dict[str, Any]
    ) -> Optional[Any]:
        """
        直接从workflow state提取参数
        
        Args:
            source_task: 源任务名称（context或query_analysis）
            source_path: 源数据路径
            workflow_state: workflow状态
            
        Returns:
            提取的值，如果不存在则返回None
        """
        if source_task not in self.WORKFLOW_STATE_MAPPINGS:
            return None
        
        state_mapping = self.WORKFLOW_STATE_MAPPINGS[source_task]
        source_key = source_path.split('.')[0]
        
        if source_key in state_mapping:
            state_path = state_mapping[source_key]
            return self._extract_by_path(workflow_state, state_path)
        
        # 尝试直接路径
        full_path = f"{source_task}.{source_path}"
        return self._extract_by_path(workflow_state, full_path)
    
    def get_workflow_state_extraction_stats(self) -> Dict[str, Any]:
        """获取workflow state提取统计"""
        return {
            **self.get_extraction_stats(),
            "workflow_state_extractions": self.workflow_state_extractions
        }
    
    def reset_stats(self):
        """重置统计信息"""
        super().reset_stats()
        self.workflow_state_extractions = 0
    
    @classmethod
    def get_supported_workflow_tasks(cls) -> List[str]:
        """获取支持的workflow任务列表"""
        return list(cls.WORKFLOW_STATE_MAPPINGS.keys())
    
    @classmethod
    def get_workflow_task_mappings(cls, task_name: str) -> Optional[Dict[str, str]]:
        """获取指定workflow任务的映射配置"""
        return cls.WORKFLOW_STATE_MAPPINGS.get(task_name)
