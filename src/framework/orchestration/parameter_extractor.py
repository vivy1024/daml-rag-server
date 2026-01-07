"""
参数提取器 - Parameter Extractor

从上游任务结果中提取参数，支持JSONPath和复杂的数据转换。

核心功能：
1. 从上游任务结果中提取参数
2. 支持JSONPath表达式
3. 支持参数转换器（list, dict, first, join等）
4. 支持默认值
5. 详细的提取日志

版本: v1.0.0
日期: 2025-12-23
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
    参数提取器
    
    从上游任务结果中提取参数，支持复杂的数据转换。
    """
    
    def __init__(self):
        """初始化参数提取器"""
        self.logger = logger
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "default_value_used": 0
        }
    
    def extract_from_upstream(
        self,
        param_mappings: List[ParamMapping],
        upstream_results: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从上游任务结果中提取参数
        
        Args:
            param_mappings: 参数映射配置列表
            upstream_results: 上游任务结果字典 {task_name: result}
            context: 全局上下文
            
        Returns:
            提取的参数字典
        """
        extracted_params = {}
        
        self.logger.info(f"🔍 开始参数提取，共 {len(param_mappings)} 个映射")
        
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
    
    def reset_stats(self):
        """重置统计信息"""
        self.extraction_stats = {
            "total_extractions": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "default_value_used": 0
        }
