"""
数据补充管理器

协调整个数据补充流程
"""

import logging
from typing import Optional
from neo4j import AsyncGraphDatabase, AsyncDriver

from .models import SupplementReport, SupplementResult
from .exercise_supplementer import ExerciseSupplementer
from .food_supplementer import FoodSupplementer
from .injury_supplementer import InjuryTypeSupplementer
from .rehab_creator import RehabilitationPhaseCreator
from .validator import DataValidator
from .training_volume_supplementer import TrainingVolumeSupplementer
from .strength_standard_supplementer import StrengthStandardSupplementer
from .workout_program_supplementer import WorkoutProgramSupplementer
from .acsm_standard_supplementer import ACSMStandardSupplementer
from .nsca_standard_supplementer import NSCAStandardSupplementer

logger = logging.getLogger(__name__)


class DataSupplementManager:
    """数据补充管理器"""
    
    def __init__(self, neo4j_driver: AsyncDriver):
        """
        初始化管理器
        
        Args:
            neo4j_driver: Neo4j异步驱动
        """
        self.driver = neo4j_driver
        self.exercise_supplementer = ExerciseSupplementer(neo4j_driver)
        self.food_supplementer = FoodSupplementer(neo4j_driver)
        self.injury_supplementer = InjuryTypeSupplementer(neo4j_driver)
        self.rehab_creator = RehabilitationPhaseCreator(neo4j_driver)
        self.validator = DataValidator(neo4j_driver)
        
        # 训练知识导入器
        self.training_volume_supplementer = TrainingVolumeSupplementer(neo4j_driver)
        self.strength_standard_supplementer = StrengthStandardSupplementer(neo4j_driver)
        self.workout_program_supplementer = WorkoutProgramSupplementer(neo4j_driver)
        self.acsm_standard_supplementer = ACSMStandardSupplementer(neo4j_driver)
        self.nsca_standard_supplementer = NSCAStandardSupplementer(neo4j_driver)
    
    async def execute_full_supplement(
        self,
        skip_exercise: bool = False,
        skip_food: bool = False,
        skip_injury: bool = False,
        skip_rehab: bool = False,
        skip_validation: bool = False
    ) -> SupplementReport:
        """
        执行完整的数据补充流程
        
        Args:
            skip_exercise: 跳过Exercise节点补充
            skip_food: 跳过Food节点补充
            skip_injury: 跳过InjuryType节点补充
            skip_rehab: 跳过康复相关创建
            skip_validation: 跳过数据验证
        
        Returns:
            SupplementReport: 执行报告
        """
        report = SupplementReport()
        logger.info("=" * 60)
        logger.info("开始执行Neo4j数据补充")
        logger.info("=" * 60)
        
        try:
            # 阶段1：Exercise节点补充
            if not skip_exercise:
                logger.info("\n[阶段1/5] 补充Exercise节点...")
                exercise_result = await self.exercise_supplementer.supplement()
                report.add_result("exercise", exercise_result)
                logger.info(f"✅ Exercise节点补充完成: {exercise_result.updated_nodes}/{exercise_result.total_nodes}")
            
            # 阶段2：Food节点补充
            if not skip_food:
                logger.info("\n[阶段2/5] 补充Food节点...")
                food_result = await self.food_supplementer.supplement()
                report.add_result("food", food_result)
                logger.info(f"✅ Food节点补充完成: {food_result.updated_nodes}/{food_result.total_nodes}")
            
            # 阶段3：InjuryType节点补充
            if not skip_injury:
                logger.info("\n[阶段3/5] 补充InjuryType节点...")
                injury_result = await self.injury_supplementer.supplement()
                report.add_result("injury_type", injury_result)
                logger.info(f"✅ InjuryType节点补充完成: {injury_result.updated_nodes}/{injury_result.total_nodes}")
            
            # 阶段4：RehabilitationPhase节点创建
            if not skip_rehab:
                logger.info("\n[阶段4/5] 创建RehabilitationPhase节点...")
                rehab_result = await self.rehab_creator.create_phases()
                report.add_result("rehab_phases", rehab_result)
                logger.info(f"✅ RehabilitationPhase节点创建完成: {rehab_result.created_nodes}个")
                
                # 阶段5：REHAB_PROGRESSION关系创建
                logger.info("\n[阶段5/5] 创建REHAB_PROGRESSION关系...")
                progression_result = await self.rehab_creator.create_progressions()
                report.add_result("rehab_progressions", progression_result)
                logger.info(f"✅ REHAB_PROGRESSION关系创建完成: {progression_result.created_nodes}个")
            
            # 阶段6：数据验证
            if not skip_validation:
                logger.info("\n[验证阶段] 验证补充的数据...")
                validation_results = await self.validator.validate_all()
                for field_name, result in validation_results.items():
                    report.add_validation(field_name, result)
                    status = "✅" if result.is_valid else "❌"
                    logger.info(f"{status} {field_name}: {result.valid_count}/{result.total_checked}")
            
            report.finalize()
            
            logger.info("\n" + "=" * 60)
            logger.info(f"数据补充完成！总耗时: {report.total_execution_time:.2f}秒")
            logger.info(f"总体状态: {'✅ 成功' if report.is_successful else '❌ 有错误'}")
            logger.info("=" * 60)
            
            return report
            
        except Exception as e:
            logger.error(f"❌ 数据补充过程中发生错误: {e}", exc_info=True)
            report.finalize()
            report.total_errors.append({
                "stage": "overall",
                "error": str(e),
                "type": type(e).__name__
            })
            return report
    
    async def execute_exercise_only(self) -> SupplementReport:
        """仅执行Exercise节点补充"""
        return await self.execute_full_supplement(
            skip_food=True,
            skip_injury=True,
            skip_rehab=True,
            skip_validation=False
        )
    
    async def execute_food_only(self) -> SupplementReport:
        """仅执行Food节点补充"""
        return await self.execute_full_supplement(
            skip_exercise=True,
            skip_injury=True,
            skip_rehab=True,
            skip_validation=False
        )
    
    async def execute_injury_only(self) -> SupplementReport:
        """仅执行InjuryType节点补充"""
        return await self.execute_full_supplement(
            skip_exercise=True,
            skip_food=True,
            skip_rehab=True,
            skip_validation=False
        )
    
    async def execute_rehab_only(self) -> SupplementReport:
        """仅执行康复相关创建"""
        return await self.execute_full_supplement(
            skip_exercise=True,
            skip_food=True,
            skip_injury=True,
            skip_validation=False
        )
    
    async def execute_training_knowledge(
        self,
        skip_training_volume: bool = False,
        skip_strength_standards: bool = False,
        skip_workout_programs: bool = False,
        skip_acsm_standards: bool = False,
        skip_nsca_standards: bool = False,
        skip_validation: bool = False
    ) -> SupplementReport:
        """
        执行训练知识导入流程
        
        Args:
            skip_training_volume: 跳过训练量标准导入
            skip_strength_standards: 跳过力量标准导入
            skip_workout_programs: 跳过训练计划模板导入
            skip_acsm_standards: 跳过ACSM标准导入
            skip_nsca_standards: 跳过NSCA标准导入
            skip_validation: 跳过数据验证
        
        Returns:
            SupplementReport: 执行报告
        """
        report = SupplementReport()
        logger.info("=" * 60)
        logger.info("开始执行训练知识导入")
        logger.info("=" * 60)
        
        try:
            # 阶段1：训练量标准导入
            if not skip_training_volume:
                logger.info("\n[阶段1/5] 导入训练量标准...")
                training_volume_result = await self.training_volume_supplementer.supplement()
                report.add_result("training_volume", training_volume_result)
                logger.info(f"✅ 训练量标准导入完成: {training_volume_result.updated_nodes}/{training_volume_result.total_nodes}")
            
            # 阶段2：力量标准导入
            if not skip_strength_standards:
                logger.info("\n[阶段2/5] 导入力量标准...")
                strength_standard_result = await self.strength_standard_supplementer.supplement()
                report.add_result("strength_standard", strength_standard_result)
                logger.info(f"✅ 力量标准导入完成: {strength_standard_result.created_nodes}个节点")
            
            # 阶段3：训练计划模板导入
            if not skip_workout_programs:
                logger.info("\n[阶段3/5] 导入训练计划模板...")
                workout_program_result = await self.workout_program_supplementer.supplement()
                report.add_result("workout_program", workout_program_result)
                logger.info(f"✅ 训练计划模板导入完成: {workout_program_result.created_nodes}个节点")
            
            # 阶段4：ACSM标准导入
            if not skip_acsm_standards:
                logger.info("\n[阶段4/5] 导入ACSM标准...")
                acsm_standard_result = await self.acsm_standard_supplementer.supplement()
                report.add_result("acsm_standard", acsm_standard_result)
                logger.info(f"✅ ACSM标准导入完成: {acsm_standard_result.created_nodes}个节点")
            
            # 阶段5：NSCA标准导入
            if not skip_nsca_standards:
                logger.info("\n[阶段5/5] 导入NSCA标准...")
                nsca_standard_result = await self.nsca_standard_supplementer.supplement()
                report.add_result("nsca_standard", nsca_standard_result)
                logger.info(f"✅ NSCA标准导入完成: {nsca_standard_result.created_nodes}个节点")
            
            # 阶段6：数据验证
            if not skip_validation:
                logger.info("\n[验证阶段] 验证导入的训练知识数据...")
                validation_results = await self.validator.validate_training_knowledge()
                for field_name, result in validation_results.items():
                    report.add_validation(field_name, result)
                    status = "✅" if result.is_valid else "❌"
                    logger.info(f"{status} {field_name}: {result.valid_count}/{result.total_checked}")
            
            report.finalize()
            
            logger.info("\n" + "=" * 60)
            logger.info(f"训练知识导入完成！总耗时: {report.total_execution_time:.2f}秒")
            logger.info(f"总体状态: {'✅ 成功' if report.is_successful else '❌ 有错误'}")
            logger.info("=" * 60)
            
            return report
            
        except Exception as e:
            logger.error(f"❌ 训练知识导入过程中发生错误: {e}", exc_info=True)
            report.finalize()
            report.total_errors.append({
                "stage": "overall",
                "error": str(e),
                "type": type(e).__name__
            })
            return report
    
    async def execute_training_volume_only(self) -> SupplementReport:
        """仅执行训练量标准导入"""
        return await self.execute_training_knowledge(
            skip_strength_standards=True,
            skip_workout_programs=True,
            skip_acsm_standards=True,
            skip_nsca_standards=True,
            skip_validation=False
        )
    
    async def execute_strength_standards_only(self) -> SupplementReport:
        """仅执行力量标准导入"""
        return await self.execute_training_knowledge(
            skip_training_volume=True,
            skip_workout_programs=True,
            skip_acsm_standards=True,
            skip_nsca_standards=True,
            skip_validation=False
        )
    
    async def execute_workout_programs_only(self) -> SupplementReport:
        """仅执行训练计划模板导入"""
        return await self.execute_training_knowledge(
            skip_training_volume=True,
            skip_strength_standards=True,
            skip_acsm_standards=True,
            skip_nsca_standards=True,
            skip_validation=False
        )
    
    async def execute_acsm_standards_only(self) -> SupplementReport:
        """仅执行ACSM标准导入"""
        return await self.execute_training_knowledge(
            skip_training_volume=True,
            skip_strength_standards=True,
            skip_workout_programs=True,
            skip_nsca_standards=True,
            skip_validation=False
        )
    
    async def execute_nsca_standards_only(self) -> SupplementReport:
        """仅执行NSCA标准导入"""
        return await self.execute_training_knowledge(
            skip_training_volume=True,
            skip_strength_standards=True,
            skip_workout_programs=True,
            skip_acsm_standards=True,
            skip_validation=False
        )
