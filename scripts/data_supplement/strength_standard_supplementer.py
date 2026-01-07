"""
力量标准导入器

功能：
1. 读取strength-standards.json
2. 创建StrengthStandard节点
3. 创建Exercise -[:HAS_STRENGTH_STANDARD]-> StrengthStandard关系
4. 实现幂等性：检查节点ID是否已存在

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


class StrengthStandardSupplementer:
    """力量标准补充器"""
    
    def __init__(self, neo4j_driver: AsyncDriver, data_dir: str = "data/training_knowledge"):
        """
        初始化补充器
        
        Args:
            neo4j_driver: Neo4j异步驱动
            data_dir: 数据文件目录
        """
        self.driver = neo4j_driver
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "strength-standards.json"
        
        # 动作名称映射（英文 -> 中文）
        self.exercise_name_mapping = {
            "squat": "杠铃深蹲",
            "bench": "杠铃卧推",
            "deadlift": "杠铃硬拉",
            "press": "杠铃推举"
        }
        
        # 训练水平映射（英文 -> 中文）
        self.level_mapping = {
            "beginner": "初学者",
            "novice": "新手",
            "intermediate": "中级",
            "advanced": "高级",
            "elite": "精英"
        }
    
    async def supplement(self) -> SupplementResult:
        """
        执行力量标准补充流程
        
        Returns:
            SupplementResult: 补充结果
        """
        start_time = time.time()
        logger.info("开始力量标准补充")
        
        try:
            # 1. 读取数据文件
            logger.info(f"读取数据文件: {self.data_file}")
            standards_data = self._load_standards_data()
            
            if not standards_data:
                logger.error("力量标准数据为空")
                return SupplementResult(
                    total_nodes=0,
                    created_nodes=0,
                    errors=[{"stage": "load_data", "error": "力量标准数据为空"}],
                    execution_time=time.time() - start_time
                )
            
            # 2. 创建StrengthStandard节点和关系
            async with self.driver.session() as session:
                created_count = 0
                skipped_count = 0
                errors = []
                
                # 处理男性标准
                male_standards = standards_data.get('male_standards_kg', {})
                for exercise_key, bodyweight_data in male_standards.items():
                    result = await self._process_exercise_standards(
                        session,
                        exercise_key,
                        bodyweight_data,
                        gender='male'
                    )
                    created_count += result['created']
                    skipped_count += result['skipped']
                    errors.extend(result['errors'])
                
                # 处理女性标准
                female_standards = standards_data.get('female_standards_kg', {})
                for exercise_key, bodyweight_data in female_standards.items():
                    result = await self._process_exercise_standards(
                        session,
                        exercise_key,
                        bodyweight_data,
                        gender='female'
                    )
                    created_count += result['created']
                    skipped_count += result['skipped']
                    errors.extend(result['errors'])
                
                execution_time = time.time() - start_time
                
                logger.info(f"力量标准补充完成")
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
            logger.error(f"力量标准补充失败: {e}", exc_info=True)
            execution_time = time.time() - start_time
            return SupplementResult(
                total_nodes=0,
                created_nodes=0,
                errors=[{"stage": "strength_standard_supplement", "error": str(e)}],
                execution_time=execution_time
            )
    
    def _load_standards_data(self) -> Dict[str, Any]:
        """
        加载力量标准数据
        
        Returns:
            Dict: 力量标准数据
        """
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"成功加载力量标准数据")
            return data
        
        except FileNotFoundError:
            logger.error(f"数据文件不存在: {self.data_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return {}
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return {}
    
    async def _process_exercise_standards(
        self,
        session,
        exercise_key: str,
        bodyweight_data: Dict[str, Dict[str, int]],
        gender: str
    ) -> Dict[str, Any]:
        """
        处理单个动作的力量标准
        
        Args:
            session: Neo4j会话
            exercise_key: 动作英文名称
            bodyweight_data: 体重-力量标准数据
            gender: 性别（male/female）
            
        Returns:
            Dict: 处理结果 {created, skipped, errors}
        """
        result = {
            'created': 0,
            'skipped': 0,
            'errors': []
        }
        
        # 获取动作中文名称
        exercise_name_zh = self.exercise_name_mapping.get(exercise_key, exercise_key)
        
        # 查找Exercise节点
        exercise_id = await self._find_exercise_id(session, exercise_name_zh)
        
        if not exercise_id:
            logger.warning(f"未找到Exercise节点: {exercise_name_zh}")
            result['errors'].append({
                "stage": "find_exercise",
                "exercise": exercise_name_zh,
                "error": "未找到Exercise节点"
            })
            return result
        
        # 遍历体重和训练水平
        for bodyweight_str, levels in bodyweight_data.items():
            bodyweight_kg = float(bodyweight_str)
            
            for level_key, weight_kg in levels.items():
                try:
                    # 生成唯一ID
                    standard_id = self._generate_standard_id(
                        exercise_key,
                        gender,
                        bodyweight_kg,
                        level_key
                    )
                    
                    # 检查是否已存在（幂等性）
                    exists = await self._check_standard_exists(session, standard_id)
                    
                    if exists:
                        result['skipped'] += 1
                        continue
                    
                    # 创建StrengthStandard节点
                    created = await self._create_strength_standard(
                        session,
                        standard_id,
                        exercise_id,
                        exercise_key,
                        exercise_name_zh,
                        gender,
                        bodyweight_kg,
                        level_key,
                        weight_kg
                    )
                    
                    if created:
                        result['created'] += 1
                
                except Exception as e:
                    error_msg = f"创建力量标准失败: {exercise_key}, {gender}, {bodyweight_kg}kg, {level_key}"
                    logger.error(f"{error_msg}: {e}")
                    result['errors'].append({
                        "stage": "create_standard",
                        "exercise": exercise_key,
                        "gender": gender,
                        "bodyweight": bodyweight_kg,
                        "level": level_key,
                        "error": str(e)
                    })
        
        return result
    
    async def _find_exercise_id(self, session, exercise_name_zh: str) -> Optional[str]:
        """
        查找Exercise节点ID
        
        Args:
            session: Neo4j会话
            exercise_name_zh: 动作中文名称
            
        Returns:
            Optional[str]: Exercise节点ID
        """
        query = """
        MATCH (e:Exercise)
        WHERE e.name_zh = $name_zh
        RETURN e.id as id
        LIMIT 1
        """
        result = await session.run(query, {"name_zh": exercise_name_zh})
        record = await result.single()
        return record["id"] if record else None
    
    def _generate_standard_id(
        self,
        exercise_key: str,
        gender: str,
        bodyweight_kg: float,
        level_key: str
    ) -> str:
        """
        生成力量标准唯一ID
        
        Args:
            exercise_key: 动作英文名称
            gender: 性别
            bodyweight_kg: 体重（公斤）
            level_key: 训练水平
            
        Returns:
            str: 唯一ID
        """
        return f"strength_std_{exercise_key}_{gender}_{bodyweight_kg}_{level_key}"
    
    async def _check_standard_exists(self, session, standard_id: str) -> bool:
        """
        检查StrengthStandard节点是否已存在（幂等性）
        
        Args:
            session: Neo4j会话
            standard_id: 力量标准ID
            
        Returns:
            bool: 是否已存在
        """
        query = """
        MATCH (s:StrengthStandard {id: $id})
        RETURN count(s) > 0 as exists
        """
        result = await session.run(query, {"id": standard_id})
        record = await result.single()
        return record["exists"] if record else False
    
    async def _create_strength_standard(
        self,
        session,
        standard_id: str,
        exercise_id: str,
        exercise_name: str,
        exercise_name_zh: str,
        gender: str,
        bodyweight_kg: float,
        level_key: str,
        weight_kg: int
    ) -> bool:
        """
        创建StrengthStandard节点和关系
        
        Args:
            session: Neo4j会话
            standard_id: 力量标准ID
            exercise_id: Exercise节点ID
            exercise_name: 动作英文名称
            exercise_name_zh: 动作中文名称
            gender: 性别
            bodyweight_kg: 体重（公斤）
            level_key: 训练水平英文
            weight_kg: 力量标准（公斤）
            
        Returns:
            bool: 是否创建成功
        """
        # 获取训练水平中文
        level_zh = self.level_mapping.get(level_key, level_key)
        
        # 计算相对体重百分比
        weight_percentage = (weight_kg / bodyweight_kg * 100) if bodyweight_kg > 0 else 0
        
        query = """
        MATCH (e:Exercise {id: $exercise_id})
        CREATE (s:StrengthStandard {
            id: $id,
            exercise_name: $exercise_name,
            exercise_name_zh: $exercise_name_zh,
            gender: $gender,
            bodyweight_kg: $bodyweight_kg,
            level: $level,
            level_zh: $level_zh,
            weight_kg: $weight_kg,
            weight_percentage: $weight_percentage,
            created_at: datetime(),
            data_source: 'strength-standards.json'
        })
        CREATE (e)-[:HAS_STRENGTH_STANDARD]->(s)
        RETURN count(s) as created_count
        """
        
        result = await session.run(query, {
            "id": standard_id,
            "exercise_id": exercise_id,
            "exercise_name": exercise_name,
            "exercise_name_zh": exercise_name_zh,
            "gender": gender,
            "bodyweight_kg": bodyweight_kg,
            "level": level_key,
            "level_zh": level_zh,
            "weight_kg": weight_kg,
            "weight_percentage": round(weight_percentage, 2)
        })
        
        record = await result.single()
        return record["created_count"] > 0 if record else False
