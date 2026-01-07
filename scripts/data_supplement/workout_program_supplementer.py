"""
训练计划模板导入器

功能：
1. 读取workout-programs.json
2. 创建WorkoutProgram节点
3. 创建WorkoutProgram -[:INCLUDES_EXERCISE]-> Exercise关系
4. 创建WorkoutProgram -[:TARGETS_MUSCLE]-> Muscle关系
5. 创建WorkoutProgram -[:SUITABLE_FOR]-> TrainingLevel关系
6. 创建WorkoutProgram -[:RECOMMENDED_FOR]-> TrainingGoal关系
7. 实现幂等性：检查节点ID是否已存在

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


class WorkoutProgramSupplementer:
    """训练计划模板补充器"""
    
    def __init__(self, neo4j_driver: AsyncDriver, data_dir: str = "data/training_knowledge"):
        """
        初始化补充器
        
        Args:
            neo4j_driver: Neo4j异步驱动
            data_dir: 数据文件目录
        """
        self.driver = neo4j_driver
        self.data_dir = Path(data_dir)
        self.data_file = self.data_dir / "workout-programs.json"
        
        # 训练水平映射
        self.level_mapping = {
            "beginner": "初学者",
            "intermediate": "中级",
            "advanced": "高级"
        }
        
        # 核心动作映射（英文 -> 中文）
        self.core_lifts_mapping = {
            "squat": "深蹲",
            "bench": "卧推",
            "deadlift": "硬拉",
            "press": "推举"
        }
    
    async def supplement(self) -> SupplementResult:
        """
        执行训练计划模板补充流程
        
        Returns:
            SupplementResult: 补充结果
        """
        start_time = time.time()
        logger.info("开始训练计划模板补充")
        
        try:
            # 1. 读取数据文件
            logger.info(f"读取数据文件: {self.data_file}")
            programs_data = self._load_programs_data()
            
            if not programs_data:
                logger.error("训练计划模板数据为空")
                return SupplementResult(
                    total_nodes=0,
                    created_nodes=0,
                    errors=[{"stage": "load_data", "error": "训练计划模板数据为空"}],
                    execution_time=time.time() - start_time
                )
            
            # 2. 创建WorkoutProgram节点和关系
            async with self.driver.session() as session:
                created_count = 0
                skipped_count = 0
                errors = []
                
                programs = programs_data.get('programs', {})
                
                for program_key, program_info in programs.items():
                    try:
                        # 生成唯一ID
                        program_id = f"workout_program_{program_key}"
                        
                        # 检查是否已存在（幂等性）
                        exists = await self._check_program_exists(session, program_id)
                        
                        if exists:
                            logger.debug(f"跳过已存在的训练计划: {program_key}")
                            skipped_count += 1
                            continue
                        
                        # 创建WorkoutProgram节点
                        created = await self._create_workout_program(
                            session,
                            program_id,
                            program_key,
                            program_info
                        )
                        
                        if created:
                            created_count += 1
                            logger.info(f"✅ 创建成功: {program_info.get('name', program_key)}")
                            
                            # 创建关系
                            await self._create_program_relationships(
                                session,
                                program_id,
                                program_info
                            )
                    
                    except Exception as e:
                        error_msg = f"创建训练计划 {program_key} 失败: {str(e)}"
                        logger.error(error_msg)
                        errors.append({
                            "stage": "create_program",
                            "program": program_key,
                            "error": str(e)
                        })
                
                execution_time = time.time() - start_time
                
                logger.info(f"训练计划模板补充完成")
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
            logger.error(f"训练计划模板补充失败: {e}", exc_info=True)
            execution_time = time.time() - start_time
            return SupplementResult(
                total_nodes=0,
                created_nodes=0,
                errors=[{"stage": "workout_program_supplement", "error": str(e)}],
                execution_time=execution_time
            )
    
    def _load_programs_data(self) -> Dict[str, Any]:
        """
        加载训练计划模板数据
        
        Returns:
            Dict: 训练计划模板数据
        """
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"成功加载训练计划模板数据")
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
    
    async def _check_program_exists(self, session, program_id: str) -> bool:
        """
        检查WorkoutProgram节点是否已存在（幂等性）
        
        Args:
            session: Neo4j会话
            program_id: 训练计划ID
            
        Returns:
            bool: 是否已存在
        """
        query = """
        MATCH (p:WorkoutProgram {id: $id})
        RETURN count(p) > 0 as exists
        """
        result = await session.run(query, {"id": program_id})
        record = await result.single()
        return record["exists"] if record else False
    
    async def _create_workout_program(
        self,
        session,
        program_id: str,
        program_key: str,
        program_info: Dict[str, Any]
    ) -> bool:
        """
        创建WorkoutProgram节点
        
        Args:
            session: Neo4j会话
            program_id: 训练计划ID
            program_key: 训练计划键名
            program_info: 训练计划信息
            
        Returns:
            bool: 是否创建成功
        """
        # 提取基本信息
        name = program_info.get('name', program_key)
        author = program_info.get('author', 'Unknown')
        experience_level = program_info.get('experience_level', 'beginner')
        experience_level_zh = self.level_mapping.get(experience_level, experience_level)
        duration_weeks = program_info.get('duration_weeks', 4)
        frequency_per_week = program_info.get('frequency_per_week', 3)
        description = program_info.get('description', '')
        
        # 提取训练分化类型（从structure或workouts推断）
        training_split = self._infer_training_split(program_info)
        
        # 提取训练目标（从description推断）
        goal = self._infer_training_goal(program_info)
        
        query = """
        CREATE (p:WorkoutProgram {
            id: $id,
            name: $name,
            name_zh: $name,
            author: $author,
            experience_level: $experience_level,
            experience_level_zh: $experience_level_zh,
            duration_weeks: $duration_weeks,
            frequency_per_week: $frequency_per_week,
            description: $description,
            training_split: $training_split,
            goal: $goal,
            created_at: datetime(),
            data_source: 'workout-programs.json'
        })
        RETURN count(p) as created_count
        """
        
        result = await session.run(query, {
            "id": program_id,
            "name": name,
            "author": author,
            "experience_level": experience_level,
            "experience_level_zh": experience_level_zh,
            "duration_weeks": duration_weeks,
            "frequency_per_week": frequency_per_week,
            "description": description,
            "training_split": training_split,
            "goal": goal
        })
        
        record = await result.single()
        return record["created_count"] > 0 if record else False
    
    def _infer_training_split(self, program_info: Dict[str, Any]) -> str:
        """
        推断训练分化类型
        
        Args:
            program_info: 训练计划信息
            
        Returns:
            str: 训练分化类型
        """
        # 检查是否有workouts字段
        workouts = program_info.get('workouts', {})
        
        if workouts:
            num_workouts = len(workouts)
            if num_workouts == 2:
                return "上下肢分化"
            elif num_workouts == 3:
                return "全身训练"
            elif num_workouts == 4:
                return "上下肢分化"
            else:
                return "自定义分化"
        
        # 检查frequency
        frequency = program_info.get('frequency_per_week', 3)
        if frequency <= 3:
            return "全身训练"
        elif frequency == 4:
            return "上下肢分化"
        else:
            return "推拉腿分化"
    
    def _infer_training_goal(self, program_info: Dict[str, Any]) -> str:
        """
        推断训练目标
        
        Args:
            program_info: 训练计划信息
            
        Returns:
            str: 训练目标
        """
        description = program_info.get('description', '').lower()
        name = program_info.get('name', '').lower()
        
        # 关键词匹配
        if 'strength' in description or 'strength' in name or '力量' in description:
            return "力量提升"
        elif 'hypertrophy' in description or 'muscle' in description or '增肌' in description:
            return "肌肉增长"
        elif 'beginner' in description or '初学者' in description:
            return "基础训练"
        else:
            return "综合训练"
    
    async def _create_program_relationships(
        self,
        session,
        program_id: str,
        program_info: Dict[str, Any]
    ):
        """
        创建训练计划的关系
        
        Args:
            session: Neo4j会话
            program_id: 训练计划ID
            program_info: 训练计划信息
        """
        # 1. 创建与Exercise的关系
        await self._create_exercise_relationships(session, program_id, program_info)
        
        # 2. 创建与TrainingLevel的关系
        await self._create_level_relationship(session, program_id, program_info)
        
        # 3. 创建与TrainingGoal的关系
        await self._create_goal_relationship(session, program_id, program_info)
    
    async def _create_exercise_relationships(
        self,
        session,
        program_id: str,
        program_info: Dict[str, Any]
    ):
        """
        创建与Exercise的关系
        
        Args:
            session: Neo4j会话
            program_id: 训练计划ID
            program_info: 训练计划信息
        """
        # 提取核心动作
        core_lifts = program_info.get('core_lifts', [])
        
        for lift in core_lifts:
            # 获取中文动作名称
            lift_zh = self.core_lifts_mapping.get(lift, lift)
            
            # 查找Exercise节点
            exercise_id = await self._find_exercise_by_name(session, lift_zh)
            
            if exercise_id:
                # 创建关系
                query = """
                MATCH (p:WorkoutProgram {id: $program_id})
                MATCH (e:Exercise {exercise_id: $exercise_id})
                MERGE (p)-[:INCLUDES_EXERCISE]->(e)
                """
                await session.run(query, {
                    "program_id": program_id,
                    "exercise_id": exercise_id
                })
                logger.debug(f"创建关系: {program_id} -> {lift_zh}")
    
    async def _find_exercise_by_name(self, session, exercise_name: str) -> Optional[str]:
        """
        根据名称查找Exercise节点
        
        Args:
            session: Neo4j会话
            exercise_name: 动作名称
            
        Returns:
            Optional[str]: Exercise节点ID
        """
        query = """
        MATCH (e:Exercise)
        WHERE e.name_zh CONTAINS $name
        RETURN e.exercise_id as id
        LIMIT 1
        """
        result = await session.run(query, {"name": exercise_name})
        record = await result.single()
        return record["id"] if record else None
    
    async def _create_level_relationship(
        self,
        session,
        program_id: str,
        program_info: Dict[str, Any]
    ):
        """
        创建与TrainingLevel的关系
        
        Args:
            session: Neo4j会话
            program_id: 训练计划ID
            program_info: 训练计划信息
        """
        experience_level = program_info.get('experience_level', 'beginner')
        level_zh = self.level_mapping.get(experience_level, experience_level)
        
        # 查找TrainingLevel节点
        query_find = """
        MATCH (t:TrainingLevel)
        WHERE t.name_zh = $level_zh OR t.name_en = $level_en
        RETURN t.id as id
        LIMIT 1
        """
        result = await session.run(query_find, {
            "level_zh": level_zh,
            "level_en": experience_level
        })
        record = await result.single()
        
        if record:
            level_id = record["id"]
            
            # 创建关系
            query_create = """
            MATCH (p:WorkoutProgram {id: $program_id})
            MATCH (t:TrainingLevel {id: $level_id})
            MERGE (p)-[:SUITABLE_FOR]->(t)
            """
            await session.run(query_create, {
                "program_id": program_id,
                "level_id": level_id
            })
            logger.debug(f"创建关系: {program_id} -> TrainingLevel({level_zh})")
    
    async def _create_goal_relationship(
        self,
        session,
        program_id: str,
        program_info: Dict[str, Any]
    ):
        """
        创建与TrainingGoal的关系
        
        Args:
            session: Neo4j会话
            program_id: 训练计划ID
            program_info: 训练计划信息
        """
        goal = self._infer_training_goal(program_info)
        
        # 查找TrainingGoal节点
        query_find = """
        MATCH (g:TrainingGoal)
        WHERE g.name_zh = $goal OR g.name_zh CONTAINS $goal
        RETURN g.id as id
        LIMIT 1
        """
        result = await session.run(query_find, {"goal": goal})
        record = await result.single()
        
        if record:
            goal_id = record["id"]
            
            # 创建关系
            query_create = """
            MATCH (p:WorkoutProgram {id: $program_id})
            MATCH (g:TrainingGoal {id: $goal_id})
            MERGE (p)-[:RECOMMENDED_FOR]->(g)
            """
            await session.run(query_create, {
                "program_id": program_id,
                "goal_id": goal_id
            })
            logger.debug(f"创建关系: {program_id} -> TrainingGoal({goal})")
