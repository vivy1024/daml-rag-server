# -*- coding: utf-8 -*-
"""
参数提取器 - Parameter Extractor

从上游任务结果中提取参数，支持JSONPath和复杂的数据转换。
支持workflow state回退功能。

核心功能：
1. 从上游任务结果中提取参数
2. 支持JSONPath表达式
3. 支持参数转换器（list, dict, first, join等）
4. 支持默认值
5. 支持workflow state回退（原EnhancedParameterExtractor功能）
6. 详细的提取日志

版本: v2.0.0
日期: 2026-01-12
Requirements: 1.1, 1.3, 1.4
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ParamMapping:
    """参数映射配置"""
    source_task: str  # 源任务名称
    source_path: str  # 源数据路径（支持JSONPath）
    target_param: str  # 目标参数名
    converter: Optional[str] = None  # 转换器类型
    default_value: Any = None  # 默认值


class ParameterExtractor:
    """
    参数提取器 - 支持workflow state回退
    
    从上游任务结果中提取参数，支持复杂的数据转换。
    当上游任务不在DAG执行结果中时，从workflow state提取参数。
    """
    
    # 标准workflow数据源映射（从EnhancedParameterExtractor迁移）
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
        """初始化参数提取器"""
        self.logger = logger
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "default_value_used": 0
        }
        # 新增：workflow state提取统计
        self.workflow_state_extractions = 0
    
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
            
        向后兼容：workflow_state参数可选，不传则使用原有逻辑
        """
        extracted_params = {}
        
        self.logger.info(f"🔍 开始参数提取，共 {len(param_mappings)} 个映射")
        
        # 如果提供了workflow_state，使用增强提取逻辑
        if workflow_state is not None:
            self.logger.debug(f"🔍 workflow_state已提供，启用回退提取")
            return self._extract_with_workflow_fallback(
                param_mappings, upstream_results, context, workflow_state
            )
        
        # 原有逻辑：不使用workflow state回退
        for mapping in param_mappings:
            self.extraction_stats["total_extractions"] += 1
            
            try:
                # 获取上游任务结果
                if mapping.source_task not in upstream_results:
                    self.logger.warning(
                        f"⚠️ 上游任务不存在: {mapping.source_task}\n"
                        f"   目标参数: {mapping.target_param}\n"
                        f"   使用默认值: {mapping.default_value}"
                    )
                    
                    if mapping.default_value is not None:
                        extracted_params[mapping.target_param] = mapping.default_value
                        self.extraction_stats["default_value_used"] += 1
                    
                    continue
                
                source_data = upstream_results[mapping.source_task]
                
                # 使用路径提取数据
                extracted_value = self._extract_by_path(source_data, mapping.source_path)
                
                # 应用转换器
                if mapping.converter:
                    extracted_value = self._apply_converter(extracted_value, mapping.converter)
                
                # 如果提取失败，使用默认值
                if extracted_value is None and mapping.default_value is not None:
                    self.logger.debug(
                        f"📋 使用默认值: {mapping.target_param} = {mapping.default_value}"
                    )
                    extracted_params[mapping.target_param] = mapping.default_value
                    self.extraction_stats["default_value_used"] += 1
                else:
                    self.logger.debug(
                        f"✅ 提取成功: {mapping.target_param} = {extracted_value} "
                        f"(来自 {mapping.source_task}.{mapping.source_path})"
                    )
                    extracted_params[mapping.target_param] = extracted_value
                    self.extraction_stats["successful_extractions"] += 1
                
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
            f"📊 参数提取完成: 成功 {self.extraction_stats['successful_extractions']}，"
            f"失败 {self.extraction_stats['failed_extractions']}，"
            f"使用默认值 {self.extraction_stats['default_value_used']}"
        )
        
        return extracted_params
    
    def _extract_with_workflow_fallback(
        self,
        param_mappings: List[ParamMapping],
        upstream_results: Dict[str, Any],
        context: Dict[str, Any],
        workflow_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用workflow state回退的增强提取逻辑
        
        Args:
            param_mappings: 参数映射配置列表
            upstream_results: 上游任务结果字典
            context: 全局上下文
            workflow_state: workflow状态
            
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
                    self.logger.debug(
                        f"🔍 尝试从workflow_state提取: source_task={mapping.source_task}, "
                        f"source_path={mapping.source_path}"
                    )
                    
                    if workflow_state:
                        # 从workflow state提取
                        state_mapping = self.WORKFLOW_STATE_MAPPINGS[mapping.source_task]
                        
                        # 获取source_path的第一部分作为key
                        source_key = mapping.source_path.split('.')[0]
                        self.logger.debug(
                            f"🔍 source_key={source_key}, state_mapping keys={list(state_mapping.keys())}"
                        )
                        
                        if source_key in state_mapping:
                            state_path = state_mapping[source_key]
                            value = self._extract_by_path(workflow_state, state_path)
                            self.logger.debug(f"🔍 state_path={state_path}, extracted_value={value}")
                            
                            if value is not None:
                                extraction_source = f"workflow_state:{state_path}"
                                self.workflow_state_extractions += 1
                                self.logger.info(
                                    f"✅ 从workflow state提取: {mapping.target_param} = "
                                    f"{self._truncate_value(value)} (路径: {state_path})"
                                )
                        else:
                            # 尝试直接从workflow state提取完整路径
                            full_path = f"{mapping.source_task}.{mapping.source_path}"
                            value = self._extract_by_path(workflow_state, full_path)
                            if value is not None:
                                extraction_source = f"workflow_state:{full_path}"
                                self.workflow_state_extractions += 1
                                self.logger.info(
                                    f"✅ 从workflow state提取（完整路径）: {mapping.target_param} = "
                                    f"{self._truncate_value(value)}"
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
    
    def _extract_by_path(self, data: Any, path: str) -> Any:
        """
        使用路径提取数据
        
        支持的路径格式：
        - "field" - 直接字段
        - "field.nested" - 嵌套字段
        - "field[0]" - 数组索引
        - "field[*]" - 数组所有元素
        - "field[*].subfield" - 数组元素的子字段
        
        Args:
            data: 源数据
            path: 提取路径
            
        Returns:
            提取的值
        """
        if not path or path == ".":
            return data
        
        # 分割路径
        parts = self._parse_path(path)
        
        current = data
        for part in parts:
            if current is None:
                return None
            
            # 处理数组通配符 [*]
            if part == "[*]":
                if not isinstance(current, list):
                    self.logger.warning(f"⚠️ 路径 {path} 期望列表，但得到 {type(current)}")
                    return None
                # 返回整个列表，后续部分将在列表的每个元素上应用
                continue
            
            # 处理数组索引 [0]
            if part.startswith("[") and part.endswith("]"):
                try:
                    index = int(part[1:-1])
                    if isinstance(current, list) and 0 <= index < len(current):
                        current = current[index]
                    else:
                        return None
                except (ValueError, IndexError):
                    return None
            
            # 处理字段访问
            elif isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                # 如果当前是列表，对每个元素应用字段访问
                current = [item.get(part) if isinstance(item, dict) else None for item in current]
            else:
                return None
        
        return current
    
    def _parse_path(self, path: str) -> List[str]:
        """
        解析路径字符串
        
        Args:
            path: 路径字符串，如 "field.nested[0].subfield"
            
        Returns:
            路径部分列表
        """
        parts = []
        current = ""
        in_bracket = False
        
        for char in path:
            if char == "[":
                if current:
                    parts.append(current)
                    current = ""
                in_bracket = True
                current = "["
            elif char == "]":
                current += "]"
                parts.append(current)
                current = ""
                in_bracket = False
            elif char == "." and not in_bracket:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
        
        if current:
            parts.append(current)
        
        return parts
    
    def _apply_converter(self, value: Any, converter: str) -> Any:
        """
        应用转换器
        
        支持的转换器：
        - "list" - 转换为列表
        - "first" - 取第一个元素
        - "join" - 连接列表为字符串
        - "dict" - 转换为字典
        - "count" - 计数
        
        Args:
            value: 原始值
            converter: 转换器类型
            
        Returns:
            转换后的值
        """
        if value is None:
            return None
        
        try:
            if converter == "list":
                if isinstance(value, list):
                    return value
                return [value]
            
            elif converter == "first":
                if isinstance(value, list) and len(value) > 0:
                    return value[0]
                return value
            
            elif converter == "join":
                if isinstance(value, list):
                    return ", ".join(str(v) for v in value)
                return str(value)
            
            elif converter == "dict":
                if isinstance(value, dict):
                    return value
                return {}
            
            elif converter == "count":
                if isinstance(value, (list, dict, str)):
                    return len(value)
                return 0
            
            else:
                self.logger.warning(f"⚠️ 未知的转换器: {converter}")
                return value
                
        except Exception as e:
            self.logger.error(f"❌ 转换器应用失败: {converter}\n   错误: {str(e)}")
            return value
    
    def get_extraction_stats(self) -> Dict[str, int]:
        """获取提取统计信息"""
        return self.extraction_stats.copy()
    
    def get_workflow_state_extraction_stats(self) -> Dict[str, Any]:
        """获取workflow state提取统计"""
        return {
            **self.get_extraction_stats(),
            "workflow_state_extractions": self.workflow_state_extractions
        }
    
    def reset_stats(self):
        """重置统计信息"""
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "default_value_used": 0
        }
        self.workflow_state_extractions = 0
    
    @classmethod
    def get_supported_workflow_tasks(cls) -> List[str]:
        """获取支持的workflow任务列表"""
        return list(cls.WORKFLOW_STATE_MAPPINGS.keys())
    
    @classmethod
    def get_workflow_task_mappings(cls, task_name: str) -> Optional[Dict[str, str]]:
        """获取指定workflow任务的映射配置"""
        return cls.WORKFLOW_STATE_MAPPINGS.get(task_name)


# 向后兼容别名
EnhancedParameterExtractor = ParameterExtractor
