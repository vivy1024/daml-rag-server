"""
数据验证器

功能：
1. 验证Exercise节点数据
2. 验证Food节点数据
3. 验证InjuryType节点数据
4. 验证RehabilitationPhase节点数据
5. 验证REHAB_PROGRESSION关系数据
6. 验证训练知识数据（训练量标准、力量标准、训练计划模板、ACSM/NSCA标准）

作者：薛小川
日期：2025-12-19
版本：v1.1.0
"""

import logging
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from neo4j import AsyncDriver

try:
    from .models import ValidationResult
except ImportError:
    # 支持独立导入
    from models import ValidationResult

logger = logging.getLogger(__name__)


class DataValidator:
    """数据验证器"""
    
    def __init__(self, neo4j_driver: AsyncDriver):
        """
        初始化验证器
        
        Args:
            neo4j_driver: Neo4j异步驱动
        """
        self.driver = neo4j_driver
    
    async def validate_all(self) -> Dict[str, ValidationResult]:
        """
        验证所有补充的数据
        
        Returns:
            Dict[str, ValidationResult]: 验证结果字典
        """
        logger.info("开始数据验证")
        
        results = {}
        
        try:
            # TODO: 实现数据验证逻辑
            logger.info("数据验证功能待实现")
            
        except Exception as e:
            logger.error(f"数据验证失败: {e}", exc_info=True)
        
        return results
    
    async def validate_training_knowledge(self) -> Dict[str, ValidationResult]:
        """
        验证训练知识数据
        
        验证内容：
        1. Muscle节点的MEV/MAV/MRV属性
        2. StrengthStandard节点和关系
        3. WorkoutProgram节点和关系
        4. ACSMStandard节点
        5. NSCAStandard节点
        
        Returns:
            Dict[str, ValidationResult]: 验证结果字典
        """
        logger.info("开始训练知识数据验证")
        
        results = {}
        
        try:
            async with self.driver.session() as session:
                # 1. 验证Muscle节点的训练量属性
                muscle_result = await self._validate_muscle_volume_data(session)
                results["muscle_volume"] = muscle_result
                
                # 2. 验证StrengthStandard节点
                strength_result = await self._validate_strength_standards(session)
                results["strength_standards"] = strength_result
                
                # 3. 验证WorkoutProgram节点
                program_result = await self._validate_workout_programs(session)
                results["workout_programs"] = program_result
                
                # 4. 验证ACSMStandard节点
                acsm_result = await self._validate_acsm_standards(session)
                results["acsm_standards"] = acsm_result
                
                # 5. 验证NSCAStandard节点
                nsca_result = await self._validate_nsca_standards(session)
                results["nsca_standards"] = nsca_result
            
            logger.info("训练知识数据验证完成")
            
        except Exception as e:
            logger.error(f"训练知识数据验证失败: {e}", exc_info=True)
        
        return results
    
    async def _validate_muscle_volume_data(self, session) -> ValidationResult:
        """验证Muscle节点的训练量数据"""
        result = ValidationResult(field_name="muscle_volume")
        
        try:
            # 查询所有Muscle节点
            query = """
            MATCH (m:Muscle)
            RETURN m.name_zh as name_zh, m.mev as mev, m.mav as mav, m.mrv as mrv
            """
            records = await session.run(query)
            
            async for record in records:
                result.total_checked += 1
                
                name_zh = record["name_zh"]
                mev = record["mev"]
                mav = record["mav"]
                mrv = record["mrv"]
                
                # 检查是否有训练量数据
                if mev is None or mev == "N/A":
                    result.invalid_count += 1
                    result.errors.append({
                        "error": "missing_volume_data",
                        "muscle": name_zh,
                        "message": f"{name_zh} 缺少训练量数据"
                    })
                    continue
                
                # 验证数值关系：mev < mav < mrv
                try:
                    mev_val = int(mev)
                    mav_val = int(mav)
                    mrv_val = int(mrv)
                    
                    if not (mev_val < mav_val < mrv_val):
                        result.invalid_count += 1
                        result.errors.append({
                            "error": "invalid_relationship",
                            "muscle": name_zh,
                            "values": {"mev": mev_val, "mav": mav_val, "mrv": mrv_val},
                            "message": f"{name_zh} 数值关系错误: mev({mev_val}) < mav({mav_val}) < mrv({mrv_val})"
                        })
                        continue
                    
                    result.valid_count += 1
                
                except (ValueError, TypeError) as e:
                    result.invalid_count += 1
                    result.errors.append({
                        "error": "invalid_format",
                        "muscle": name_zh,
                        "message": f"{name_zh} 数值格式错误: {str(e)}"
                    })
            
            logger.info(
                f"Muscle训练量数据验证完成: {result.valid_count}/{result.total_checked} 有效"
            )
            
        except Exception as e:
            logger.error(f"Muscle训练量数据验证失败: {e}", exc_info=True)
            result.errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
        
        return result
    
    async def _validate_strength_standards(self, session) -> ValidationResult:
        """验证StrengthStandard节点"""
        result = ValidationResult(field_name="strength_standards")
        
        try:
            # 查询所有StrengthStandard节点
            query = """
            MATCH (s:StrengthStandard)
            RETURN count(s) as total
            """
            record = await (await session.run(query)).single()
            result.total_checked = record["total"] if record else 0
            
            # 验证每个节点都有Exercise关系
            query_with_relation = """
            MATCH (e:Exercise)-[:HAS_STRENGTH_STANDARD]->(s:StrengthStandard)
            RETURN count(s) as valid_count
            """
            record = await (await session.run(query_with_relation)).single()
            result.valid_count = record["valid_count"] if record else 0
            
            result.invalid_count = result.total_checked - result.valid_count
            
            if result.invalid_count > 0:
                result.errors.append({
                    "error": "missing_exercise_relation",
                    "count": result.invalid_count,
                    "message": f"{result.invalid_count}个StrengthStandard节点缺少Exercise关系"
                })
            
            logger.info(
                f"StrengthStandard节点验证完成: {result.valid_count}/{result.total_checked} 有效"
            )
            
        except Exception as e:
            logger.error(f"StrengthStandard节点验证失败: {e}", exc_info=True)
            result.errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
        
        return result
    
    async def _validate_workout_programs(self, session) -> ValidationResult:
        """验证WorkoutProgram节点"""
        result = ValidationResult(field_name="workout_programs")
        
        try:
            # 查询所有WorkoutProgram节点
            query = """
            MATCH (p:WorkoutProgram)
            RETURN count(p) as total
            """
            record = await (await session.run(query)).single()
            result.total_checked = record["total"] if record else 0
            
            # 验证每个节点都有Exercise和Muscle关系
            query_with_relations = """
            MATCH (p:WorkoutProgram)-[:INCLUDES_EXERCISE]->(e:Exercise)
            WITH p, count(e) as exercise_count
            MATCH (p)-[:TARGETS_MUSCLE]->(m:Muscle)
            WITH p, exercise_count, count(m) as muscle_count
            WHERE exercise_count > 0 AND muscle_count > 0
            RETURN count(p) as valid_count
            """
            record = await (await session.run(query_with_relations)).single()
            result.valid_count = record["valid_count"] if record else 0
            
            result.invalid_count = result.total_checked - result.valid_count
            
            if result.invalid_count > 0:
                result.errors.append({
                    "error": "missing_relations",
                    "count": result.invalid_count,
                    "message": f"{result.invalid_count}个WorkoutProgram节点缺少Exercise或Muscle关系"
                })
            
            logger.info(
                f"WorkoutProgram节点验证完成: {result.valid_count}/{result.total_checked} 有效"
            )
            
        except Exception as e:
            logger.error(f"WorkoutProgram节点验证失败: {e}", exc_info=True)
            result.errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
        
        return result
    
    async def _validate_acsm_standards(self, session) -> ValidationResult:
        """验证ACSMStandard节点"""
        result = ValidationResult(field_name="acsm_standards")
        
        try:
            # 查询所有ACSMStandard节点
            query = """
            MATCH (s:ACSMStandard)
            RETURN count(s) as total
            """
            record = await (await session.run(query)).single()
            result.total_checked = record["total"] if record else 0
            result.valid_count = result.total_checked  # 假设所有节点都有效
            
            logger.info(
                f"ACSMStandard节点验证完成: {result.valid_count}/{result.total_checked} 有效"
            )
            
        except Exception as e:
            logger.error(f"ACSMStandard节点验证失败: {e}", exc_info=True)
            result.errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
        
        return result
    
    async def _validate_nsca_standards(self, session) -> ValidationResult:
        """验证NSCAStandard节点"""
        result = ValidationResult(field_name="nsca_standards")
        
        try:
            # 查询所有NSCAStandard节点
            query = """
            MATCH (s:NSCAStandard)
            RETURN count(s) as total
            """
            record = await (await session.run(query)).single()
            result.total_checked = record["total"] if record else 0
            result.valid_count = result.total_checked  # 假设所有节点都有效
            
            logger.info(
                f"NSCAStandard节点验证完成: {result.valid_count}/{result.total_checked} 有效"
            )
            
        except Exception as e:
            logger.error(f"NSCAStandard节点验证失败: {e}", exc_info=True)
            result.errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
        
        return result
    
    def validate_training_volume(self, data: Dict[str, Any]) -> ValidationResult:
        """
        验证训练量标准数据格式
        
        验证规则：
        1. 检查必需字段：muscle_name、mev、mav、mrv
        2. 验证数值关系：mev < mav < mrv
        3. 验证数值为正数
        
        Args:
            data: 训练量数据字典
            
        Returns:
            ValidationResult: 验证结果
        """
        logger.info("开始验证训练量标准数据")
        
        result = ValidationResult(field_name="training_volume")
        errors = []
        
        try:
            # 检查是否有volume_landmarks字段
            if "volume_landmarks" not in data:
                errors.append({
                    "error": "missing_field",
                    "field": "volume_landmarks",
                    "message": "缺少volume_landmarks字段"
                })
                result.errors = errors
                result.invalid_count = 1
                return result
            
            volume_landmarks = data["volume_landmarks"]
            
            # 遍历每个肌群
            for muscle_name, muscle_data in volume_landmarks.items():
                result.total_checked += 1
                
                # 处理嵌套结构（如shoulders）
                if isinstance(muscle_data, dict) and any(
                    key in muscle_data for key in ["front_delts", "side_delts", "rear_delts"]
                ):
                    # 肩部有子分类
                    for sub_muscle, sub_data in muscle_data.items():
                        if sub_muscle == "optimal_frequency":
                            continue
                        
                        result.total_checked += 1
                        is_valid, error = self._validate_volume_entry(
                            f"{muscle_name}.{sub_muscle}", sub_data
                        )
                        
                        if is_valid:
                            result.valid_count += 1
                        else:
                            result.invalid_count += 1
                            errors.append(error)
                else:
                    # 普通肌群
                    is_valid, error = self._validate_volume_entry(muscle_name, muscle_data)
                    
                    if is_valid:
                        result.valid_count += 1
                    else:
                        result.invalid_count += 1
                        errors.append(error)
            
            result.errors = errors
            logger.info(
                f"训练量数据验证完成: {result.valid_count}/{result.total_checked} 有效 "
                f"({result.validity_rate:.1f}%)"
            )
            
        except Exception as e:
            logger.error(f"训练量数据验证失败: {e}", exc_info=True)
            errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
            result.errors = errors
            result.invalid_count = result.total_checked
        
        return result
    
    def _validate_volume_entry(
        self, muscle_name: str, muscle_data: Dict[str, Any]
    ) -> tuple[bool, Optional[Dict[str, Any]]]:
        """
        验证单个肌群的训练量数据
        
        Args:
            muscle_name: 肌群名称
            muscle_data: 肌群数据
            
        Returns:
            (is_valid, error): 是否有效和错误信息
        """
        # 检查必需字段
        required_fields = ["MV", "MEV", "MAV", "MRV"]
        missing_fields = [f for f in required_fields if f not in muscle_data]
        
        if missing_fields:
            return False, {
                "error": "missing_fields",
                "muscle": muscle_name,
                "missing": missing_fields,
                "message": f"{muscle_name} 缺少必需字段: {', '.join(missing_fields)}"
            }
        
        # 提取数值（从"8-10"这样的字符串中提取最小值）
        try:
            mv = self._extract_volume_number(muscle_data["MV"]["sets_per_week"])
            mev = self._extract_volume_number(muscle_data["MEV"]["sets_per_week"])
            mav = self._extract_volume_number(muscle_data["MAV"]["sets_per_week"])
            mrv = self._extract_volume_number(muscle_data["MRV"]["sets_per_week"])
        except (ValueError, KeyError) as e:
            return False, {
                "error": "invalid_format",
                "muscle": muscle_name,
                "message": f"{muscle_name} 数值格式错误: {str(e)}"
            }
        
        # 验证数值关系：MV <= MEV < MAV < MRV
        # 注意：MV可能为0（如abs、front_delts）
        if not (mv <= mev < mav < mrv):
            return False, {
                "error": "invalid_relationship",
                "muscle": muscle_name,
                "values": {"MV": mv, "MEV": mev, "MAV": mav, "MRV": mrv},
                "message": f"{muscle_name} 数值关系错误: MV({mv}) <= MEV({mev}) < MAV({mav}) < MRV({mrv})"
            }
        
        # 验证数值为非负数
        if any(v < 0 for v in [mv, mev, mav, mrv]):
            return False, {
                "error": "negative_value",
                "muscle": muscle_name,
                "values": {"MV": mv, "MEV": mev, "MAV": mav, "MRV": mrv},
                "message": f"{muscle_name} 包含负数值"
            }
        
        return True, None
    
    def _extract_volume_number(self, volume_str: str) -> int:
        """
        从训练量字符串中提取数值
        
        支持格式：
        - "8-10" -> 8
        - "22+" -> 22
        - "0" -> 0
        
        Args:
            volume_str: 训练量字符串
            
        Returns:
            int: 提取的数值
        """
        volume_str = str(volume_str).strip()
        
        # 处理"22+"格式
        if "+" in volume_str:
            return int(volume_str.replace("+", ""))
        
        # 处理"8-10"格式，取最小值
        if "-" in volume_str:
            return int(volume_str.split("-")[0])
        
        # 处理纯数字
        return int(volume_str)
    
    def validate_strength_standards(self, data: Dict[str, Any]) -> ValidationResult:
        """
        验证力量标准数据格式
        
        验证规则：
        1. 检查必需字段：exercise_name、gender、bodyweight_kg、level、weight_kg
        2. 验证数值合理性（体重和力量值为正数）
        3. 验证gender字段值（male/female）
        4. 验证level字段值（beginner/novice/intermediate/advanced/elite）
        
        Args:
            data: 力量标准数据字典
            
        Returns:
            ValidationResult: 验证结果
        """
        logger.info("开始验证力量标准数据")
        
        result = ValidationResult(field_name="strength_standards")
        errors = []
        
        try:
            valid_genders = ["male", "female"]
            valid_levels = ["beginner", "novice", "intermediate", "advanced", "elite"]
            
            # 检查male_standards_kg和female_standards_kg
            for gender_key in ["male_standards_kg", "female_standards_kg"]:
                if gender_key not in data:
                    errors.append({
                        "error": "missing_field",
                        "field": gender_key,
                        "message": f"缺少{gender_key}字段"
                    })
                    continue
                
                gender = "male" if "male" in gender_key else "female"
                standards = data[gender_key]
                
                # 遍历每个动作
                for exercise_name, bodyweight_data in standards.items():
                    # 遍历每个体重级别
                    for bodyweight_str, level_data in bodyweight_data.items():
                        result.total_checked += 1
                        
                        try:
                            bodyweight_kg = float(bodyweight_str)
                            
                            # 验证体重为正数
                            if bodyweight_kg <= 0:
                                result.invalid_count += 1
                                errors.append({
                                    "error": "invalid_bodyweight",
                                    "exercise": exercise_name,
                                    "gender": gender,
                                    "bodyweight": bodyweight_kg,
                                    "message": f"{exercise_name} 体重值必须为正数: {bodyweight_kg}"
                                })
                                continue
                            
                            # 验证每个训练水平的力量值
                            all_levels_valid = True
                            for level, weight_kg in level_data.items():
                                if level not in valid_levels:
                                    result.invalid_count += 1
                                    errors.append({
                                        "error": "invalid_level",
                                        "exercise": exercise_name,
                                        "gender": gender,
                                        "bodyweight": bodyweight_kg,
                                        "level": level,
                                        "message": f"无效的训练水平: {level}"
                                    })
                                    all_levels_valid = False
                                    break
                                
                                # 验证力量值为正数
                                if weight_kg <= 0:
                                    result.invalid_count += 1
                                    errors.append({
                                        "error": "invalid_weight",
                                        "exercise": exercise_name,
                                        "gender": gender,
                                        "bodyweight": bodyweight_kg,
                                        "level": level,
                                        "weight": weight_kg,
                                        "message": f"力量值必须为正数: {weight_kg}"
                                    })
                                    all_levels_valid = False
                                    break
                            
                            if all_levels_valid:
                                result.valid_count += 1
                        
                        except ValueError as e:
                            result.invalid_count += 1
                            errors.append({
                                "error": "invalid_format",
                                "exercise": exercise_name,
                                "gender": gender,
                                "bodyweight": bodyweight_str,
                                "message": f"体重格式错误: {str(e)}"
                            })
            
            result.errors = errors
            logger.info(
                f"力量标准数据验证完成: {result.valid_count}/{result.total_checked} 有效 "
                f"({result.validity_rate:.1f}%)"
            )
            
        except Exception as e:
            logger.error(f"力量标准数据验证失败: {e}", exc_info=True)
            errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
            result.errors = errors
            result.invalid_count = result.total_checked
        
        return result
    
    def validate_workout_programs(self, data: Dict[str, Any]) -> ValidationResult:
        """
        验证训练计划模板数据格式
        
        验证规则：
        1. 检查必需字段：name、experience_level、frequency_per_week
        2. 验证训练天数范围（1-7天）
        3. 验证experience_level字段值（beginner/intermediate/advanced）
        
        Args:
            data: 训练计划数据字典
            
        Returns:
            ValidationResult: 验证结果
        """
        logger.info("开始验证训练计划模板数据")
        
        result = ValidationResult(field_name="workout_programs")
        errors = []
        
        try:
            valid_levels = ["beginner", "intermediate", "advanced"]
            
            # 检查是否有programs字段
            if "programs" not in data:
                errors.append({
                    "error": "missing_field",
                    "field": "programs",
                    "message": "缺少programs字段"
                })
                result.errors = errors
                result.invalid_count = 1
                return result
            
            programs = data["programs"]
            
            # 遍历每个训练计划
            for program_id, program_data in programs.items():
                result.total_checked += 1
                
                # 检查必需字段
                required_fields = ["name", "experience_level"]
                missing_fields = [f for f in required_fields if f not in program_data]
                
                if missing_fields:
                    result.invalid_count += 1
                    errors.append({
                        "error": "missing_fields",
                        "program": program_id,
                        "missing": missing_fields,
                        "message": f"{program_id} 缺少必需字段: {', '.join(missing_fields)}"
                    })
                    continue
                
                # 验证experience_level
                experience_level = program_data.get("experience_level")
                if experience_level not in valid_levels:
                    result.invalid_count += 1
                    errors.append({
                        "error": "invalid_experience_level",
                        "program": program_id,
                        "level": experience_level,
                        "message": f"{program_id} 无效的训练水平: {experience_level}"
                    })
                    continue
                
                # 验证frequency_per_week（如果存在）
                frequency = program_data.get("frequency_per_week")
                if frequency is not None:
                    # 处理"4-6"这样的范围格式
                    if isinstance(frequency, str):
                        if "-" in frequency:
                            try:
                                min_freq = int(frequency.split("-")[0])
                                max_freq = int(frequency.split("-")[1])
                                if not (1 <= min_freq <= 7 and 1 <= max_freq <= 7):
                                    result.invalid_count += 1
                                    errors.append({
                                        "error": "invalid_frequency",
                                        "program": program_id,
                                        "frequency": frequency,
                                        "message": f"{program_id} 训练频率超出范围(1-7天): {frequency}"
                                    })
                                    continue
                            except ValueError:
                                result.invalid_count += 1
                                errors.append({
                                    "error": "invalid_frequency_format",
                                    "program": program_id,
                                    "frequency": frequency,
                                    "message": f"{program_id} 训练频率格式错误: {frequency}"
                                })
                                continue
                    else:
                        # 数字格式
                        try:
                            freq_num = int(frequency)
                            if not (1 <= freq_num <= 7):
                                result.invalid_count += 1
                                errors.append({
                                    "error": "invalid_frequency",
                                    "program": program_id,
                                    "frequency": freq_num,
                                    "message": f"{program_id} 训练频率超出范围(1-7天): {freq_num}"
                                })
                                continue
                        except ValueError:
                            result.invalid_count += 1
                            errors.append({
                                "error": "invalid_frequency_format",
                                "program": program_id,
                                "frequency": frequency,
                                "message": f"{program_id} 训练频率格式错误: {frequency}"
                            })
                            continue
                
                # 所有验证通过
                result.valid_count += 1
            
            result.errors = errors
            logger.info(
                f"训练计划模板数据验证完成: {result.valid_count}/{result.total_checked} 有效 "
                f"({result.validity_rate:.1f}%)"
            )
            
        except Exception as e:
            logger.error(f"训练计划模板数据验证失败: {e}", exc_info=True)
            errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
            result.errors = errors
            result.invalid_count = result.total_checked
        
        return result
    
    def validate_acsm_standards(self, data: Dict[str, Any]) -> ValidationResult:
        """
        验证ACSM标准数据格式
        
        验证规则：
        1. 检查必需字段：data_type、content
        2. 验证content字段不为空
        3. 验证metadata字段存在
        
        Args:
            data: ACSM标准数据字典
            
        Returns:
            ValidationResult: 验证结果
        """
        logger.info("开始验证ACSM标准数据")
        
        result = ValidationResult(field_name="acsm_standards")
        errors = []
        
        try:
            result.total_checked = 1
            
            # 检查必需字段
            required_fields = ["data_type", "content"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                result.invalid_count = 1
                errors.append({
                    "error": "missing_fields",
                    "missing": missing_fields,
                    "message": f"缺少必需字段: {', '.join(missing_fields)}"
                })
                result.errors = errors
                return result
            
            # 验证content不为空
            content = data.get("content")
            if not content or not isinstance(content, dict):
                result.invalid_count = 1
                errors.append({
                    "error": "invalid_content",
                    "message": "content字段为空或格式错误"
                })
                result.errors = errors
                return result
            
            # 验证metadata存在
            if "metadata" not in data:
                result.invalid_count = 1
                errors.append({
                    "error": "missing_metadata",
                    "message": "缺少metadata字段"
                })
                result.errors = errors
                return result
            
            # 所有验证通过
            result.valid_count = 1
            result.errors = errors
            logger.info("ACSM标准数据验证完成: 有效")
            
        except Exception as e:
            logger.error(f"ACSM标准数据验证失败: {e}", exc_info=True)
            errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
            result.errors = errors
            result.invalid_count = 1
        
        return result
    
    def validate_nsca_standards(self, data: Dict[str, Any]) -> ValidationResult:
        """
        验证NSCA标准数据格式
        
        验证规则：
        1. 检查必需字段：data_type、content
        2. 验证content字段不为空
        3. 验证metadata字段存在
        
        Args:
            data: NSCA标准数据字典
            
        Returns:
            ValidationResult: 验证结果
        """
        logger.info("开始验证NSCA标准数据")
        
        result = ValidationResult(field_name="nsca_standards")
        errors = []
        
        try:
            result.total_checked = 1
            
            # 检查必需字段
            required_fields = ["data_type", "content"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                result.invalid_count = 1
                errors.append({
                    "error": "missing_fields",
                    "missing": missing_fields,
                    "message": f"缺少必需字段: {', '.join(missing_fields)}"
                })
                result.errors = errors
                return result
            
            # 验证content不为空
            content = data.get("content")
            if not content or not isinstance(content, dict):
                result.invalid_count = 1
                errors.append({
                    "error": "invalid_content",
                    "message": "content字段为空或格式错误"
                })
                result.errors = errors
                return result
            
            # 验证metadata存在
            if "metadata" not in data:
                result.invalid_count = 1
                errors.append({
                    "error": "missing_metadata",
                    "message": "缺少metadata字段"
                })
                result.errors = errors
                return result
            
            # 所有验证通过
            result.valid_count = 1
            result.errors = errors
            logger.info("NSCA标准数据验证完成: 有效")
            
        except Exception as e:
            logger.error(f"NSCA标准数据验证失败: {e}", exc_info=True)
            errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
            result.errors = errors
            result.invalid_count = 1
        
        return result
