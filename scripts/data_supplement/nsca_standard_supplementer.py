"""
NSCA标准导入器

功能：
1. 读取nsca_standards/*.json文件
2. 创建NSCAStandard节点
3. 实现幂等性：检查节点ID是否已存在

作者：薛小川
日期：2025-12-19
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from neo4j import AsyncDriver

from .models import SupplementResult

logger = logging.getLogger(__name__)


class NSCAStandardSupplementer:
    """NSCA标准补充器"""
    
    def __init__(self, neo4j_driver: AsyncDriver, data_dir: str = "data/training_knowledge"):
        """
        初始化补充器
        
        Args:
            neo4j_driver: Neo4j异步驱动
            data_dir: 数据文件目录
        """
        self.driver = neo4j_driver
        self.data_dir = Path(data_dir)
        self.standards_dir = self.data_dir / "nsca_standards"
    
    async def supplement(self) -> SupplementResult:
        """
        执行NSCA标准补充流程
        
        Returns:
            SupplementResult: 补充结果
        """
        start_time = time.time()
        logger.info("开始NSCA标准补充")
        
        try:
            # 1. 检查目录是否存在
            if not self.standards_dir.exists():
                logger.error(f"NSCA标准目录不存在: {self.standards_dir}")
                return SupplementResult(
                    total_nodes=0,
                    created_nodes=0,
                    errors=[{"stage": "check_dir", "error": "NSCA标准目录不存在"}],
                    execution_time=time.time() - start_time
                )
            
            # 2. 读取所有JSON文件
            json_files = list(self.standards_dir.glob("*.json"))
            logger.info(f"找到 {len(json_files)} 个NSCA标准文件")
            
            if not json_files:
                logger.warning("未找到NSCA标准文件")
                return SupplementResult(
                    total_nodes=0,
                    created_nodes=0,
                    errors=[],
                    execution_time=time.time() - start_time
                )
            
            # 3. 创建NSCAStandard节点
            async with self.driver.session() as session:
                created_count = 0
                skipped_count = 0
                errors = []
                
                for json_file in json_files:
                    try:
                        # 读取文件
                        standard_data = self._load_standard_file(json_file)
                        
                        if not standard_data:
                            continue
                        
                        # 生成唯一ID
                        standard_id = self._generate_standard_id(json_file.stem)
                        
                        # 检查是否已存在（幂等性）
                        exists = await self._check_standard_exists(session, standard_id)
                        
                        if exists:
                            logger.debug(f"跳过已存在的NSCA标准: {json_file.name}")
                            skipped_count += 1
                            continue
                        
                        # 创建NSCAStandard节点
                        created = await self._create_nsca_standard(
                            session,
                            standard_id,
                            json_file.name,
                            standard_data
                        )
                        
                        if created:
                            created_count += 1
                            logger.info(f"✅ 创建成功: {json_file.name}")
                    
                    except Exception as e:
                        error_msg = f"处理文件 {json_file.name} 失败: {str(e)}"
                        logger.error(error_msg)
                        errors.append({
                            "stage": "process_file",
                            "file": json_file.name,
                            "error": str(e)
                        })
                
                execution_time = time.time() - start_time
                
                logger.info(f"NSCA标准补充完成")
                logger.info(f"  创建节点数: {created_count}")
                logger.info(f"  跳过节点数: {skipped_count}")
                logger.info(f"  执行时间: {execution_time:.2f}秒")
                
                return SupplementResult(
                    total_nodes=created_count + skipped_count,
                    created_nodes=created_count,
                    errors=errors,
                    execution_time=execution_time
                )
        
        except Exception as e:
            logger.error(f"NSCA标准补充失败: {e}", exc_info=True)
            execution_time = time.time() - start_time
            return SupplementResult(
                total_nodes=0,
                created_nodes=0,
                errors=[{"stage": "nsca_standard_supplement", "error": str(e)}],
                execution_time=execution_time
            )
    
    def _load_standard_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        加载NSCA标准文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            Optional[Dict]: 标准数据
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败 {file_path.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"加载文件失败 {file_path.name}: {e}")
            return None
    
    def _generate_standard_id(self, file_stem: str) -> str:
        """
        生成NSCA标准唯一ID
        
        Args:
            file_stem: 文件名（不含扩展名）
            
        Returns:
            str: 唯一ID
        """
        return f"nsca_std_{file_stem}"
    
    async def _check_standard_exists(self, session, standard_id: str) -> bool:
        """
        检查NSCAStandard节点是否已存在（幂等性）
        
        Args:
            session: Neo4j会话
            standard_id: 标准ID
            
        Returns:
            bool: 是否已存在
        """
        query = """
        MATCH (s:NSCAStandard {id: $id})
        RETURN count(s) > 0 as exists
        """
        result = await session.run(query, {"id": standard_id})
        record = await result.single()
        return record["exists"] if record else False
    
    async def _create_nsca_standard(
        self,
        session,
        standard_id: str,
        file_name: str,
        standard_data: Dict[str, Any]
    ) -> bool:
        """
        创建NSCAStandard节点
        
        Args:
            session: Neo4j会话
            standard_id: 标准ID
            file_name: 文件名
            standard_data: 标准数据
            
        Returns:
            bool: 是否创建成功
        """
        # 提取基本信息
        data_type = standard_data.get('data_type', 'unknown')
        content = standard_data.get('content', {})
        metadata = standard_data.get('metadata', {})
        reliability_score = standard_data.get('reliability_score', 0.0)
        
        # 将content转换为JSON字符串
        content_json = json.dumps(content, ensure_ascii=False)
        metadata_json = json.dumps(metadata, ensure_ascii=False)
        
        # 提取标题（从data_type或metadata）
        title = data_type.replace('_', ' ').title()
        title_zh = self._translate_title(data_type)
        
        # 提取描述（从content的第一个字段）
        description = self._extract_description(content)
        
        # 提取训练原则（如果存在）
        principles = self._extract_principles(content)
        principles_json = json.dumps(principles, ensure_ascii=False) if principles else None
        
        # 提取实施指南（如果存在）
        implementation_guide = self._extract_implementation_guide(content)
        
        query = """
        CREATE (s:NSCAStandard {
            id: $id,
            standard_type: $standard_type,
            title: $title,
            title_zh: $title_zh,
            description: $description,
            principles: $principles,
            implementation_guide: $implementation_guide,
            content: $content,
            metadata: $metadata,
            reliability_score: $reliability_score,
            created_at: datetime(),
            data_source: $data_source
        })
        RETURN count(s) as created_count
        """
        
        result = await session.run(query, {
            "id": standard_id,
            "standard_type": data_type,
            "title": title,
            "title_zh": title_zh,
            "description": description,
            "principles": principles_json,
            "implementation_guide": implementation_guide,
            "content": content_json,
            "metadata": metadata_json,
            "reliability_score": reliability_score,
            "data_source": file_name
        })
        
        record = await result.single()
        return record["created_count"] > 0 if record else False
    
    def _translate_title(self, data_type: str) -> str:
        """
        翻译标题为中文
        
        Args:
            data_type: 数据类型
            
        Returns:
            str: 中文标题
        """
        translations = {
            "strength_essentials": "力量训练基础",
            "periodization": "周期化训练",
            "program_design": "训练计划设计",
            "exercise_technique": "动作技术",
            "testing_evaluation": "测试与评估"
        }
        return translations.get(data_type, data_type)
    
    def _extract_description(self, content: Dict[str, Any]) -> str:
        """
        从content中提取描述
        
        Args:
            content: 内容字典
            
        Returns:
            str: 描述文本
        """
        # 尝试从常见字段提取描述
        if 'description' in content:
            return str(content['description'])
        
        # 如果没有description字段，使用第一个字段的值
        if content:
            first_key = list(content.keys())[0]
            first_value = content[first_key]
            
            if isinstance(first_value, dict):
                return json.dumps(first_value, ensure_ascii=False)[:200]
            else:
                return str(first_value)[:200]
        
        return "NSCA训练标准"
    
    def _extract_principles(self, content: Dict[str, Any]) -> Optional[List[str]]:
        """
        从content中提取训练原则
        
        Args:
            content: 内容字典
            
        Returns:
            Optional[List[str]]: 训练原则列表
        """
        # 查找包含"principles"的字段
        for key, value in content.items():
            if 'principle' in key.lower():
                if isinstance(value, dict):
                    return list(value.values())
                elif isinstance(value, list):
                    return value
        
        return None
    
    def _extract_implementation_guide(self, content: Dict[str, Any]) -> Optional[str]:
        """
        从content中提取实施指南
        
        Args:
            content: 内容字典
            
        Returns:
            Optional[str]: 实施指南文本
        """
        # 查找包含"guide"或"implementation"的字段
        for key, value in content.items():
            if 'guide' in key.lower() or 'implementation' in key.lower():
                if isinstance(value, str):
                    return value
                elif isinstance(value, dict):
                    return json.dumps(value, ensure_ascii=False)
        
        return None
