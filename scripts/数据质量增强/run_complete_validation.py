"""
完整数据验证脚本

功能：
1. 验证Exercise节点的所有新增字段
2. 验证Food节点的所有新增字段
3. 验证InjuryType节点的severity_level字段
4. 验证RehabilitationPhase节点
5. 验证REHAB_PROGRESSION关系
6. 生成完整的验证报告

作者：薛小川
日期：2025-12-15
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from neo4j import AsyncGraphDatabase

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompleteDataValidator:
    """完整数据验证器"""
    
    def __init__(self, uri: str, user: str, password: str):
        """初始化验证器"""
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "exercise": {},
            "food": {},
            "injury_type": {},
            "rehab_phase": {},
            "rehab_progression": {},
            "summary": {}
        }
    
    async def close(self):
        """关闭驱动"""
        await self.driver.close()
    
    async def validate_exercise_nodes(self) -> Dict[str, Any]:
        """验证Exercise节点"""
        logger.info("=" * 60)
        logger.info("验证Exercise节点")
        logger.info("=" * 60)
        
        async with self.driver.session() as session:
            results = {}
            
            # 1. 验证kinetic_chain_type字段
            logger.info("\n1. 验证kinetic_chain_type字段...")
            query = """
            MATCH (e:Exercise)
            WITH count(e) as total,
                 count(e.kinetic_chain_type) as with_field,
                 sum(CASE WHEN e.kinetic_chain_type IN ['open_chain', 'closed_chain', 'mixed'] THEN 1 ELSE 0 END) as valid_values
            RETURN total, with_field, valid_values, (with_field - valid_values) as invalid_values
            """
            result = await session.run(query)
            record = await result.single()
            
            kinetic_chain_result = {
                "total_nodes": record["total"],
                "with_field": record["with_field"],
                "valid_values": record["valid_values"],
                "invalid_values": record["invalid_values"],
                "coverage": f"{record['with_field'] / record['total'] * 100:.2f}%",
                "is_valid": record["invalid_values"] == 0 and record["with_field"] == record["total"]
            }
            results["kinetic_chain_type"] = kinetic_chain_result
            
            logger.info(f"  总节点数: {kinetic_chain_result['total_nodes']}")
            logger.info(f"  有字段的节点: {kinetic_chain_result['with_field']}")
            logger.info(f"  有效值数量: {kinetic_chain_result['valid_values']}")
            logger.info(f"  无效值数量: {kinetic_chain_result['invalid_values']}")
            logger.info(f"  覆盖率: {kinetic_chain_result['coverage']}")
            logger.info(f"  ✅ 验证通过" if kinetic_chain_result['is_valid'] else "  ❌ 验证失败")
            
            # 2. 验证technique_checkpoints字段
            logger.info("\n2. 验证technique_checkpoints字段...")
            query = """
            MATCH (e:Exercise)
            WHERE e.technique_checkpoints IS NOT NULL
            RETURN 
                count(e) as total_with_checkpoints,
                sum(CASE WHEN size(e.technique_checkpoints) > 0 THEN 1 ELSE 0 END) as non_empty
            """
            result = await session.run(query)
            record = await result.single()
            
            checkpoints_result = {
                "total_with_checkpoints": record["total_with_checkpoints"],
                "non_empty": record["non_empty"],
                "is_valid": record["total_with_checkpoints"] > 0
            }
            results["technique_checkpoints"] = checkpoints_result
            
            logger.info(f"  有技术检查点的节点: {checkpoints_result['total_with_checkpoints']}")
            logger.info(f"  非空检查点: {checkpoints_result['non_empty']}")
            logger.info(f"  ✅ 验证通过" if checkpoints_result['is_valid'] else "  ❌ 验证失败")
            
            # 3. 验证rom_requirements字段
            logger.info("\n3. 验证rom_requirements字段...")
            query = """
            MATCH (e:Exercise)
            RETURN 
                count(e) as total,
                count(e.rom_requirements) as with_rom
            """
            result = await session.run(query)
            record = await result.single()
            
            rom_result = {
                "total_nodes": record["total"],
                "with_rom": record["with_rom"],
                "coverage": f"{record['with_rom'] / record['total'] * 100:.2f}%",
                "is_valid": record["with_rom"] == record["total"]
            }
            results["rom_requirements"] = rom_result
            
            logger.info(f"  总节点数: {rom_result['total_nodes']}")
            logger.info(f"  有ROM字段的节点: {rom_result['with_rom']}")
            logger.info(f"  覆盖率: {rom_result['coverage']}")
            logger.info(f"  ✅ 验证通过" if rom_result['is_valid'] else "  ❌ 验证失败")
            
            return results
    
    async def validate_food_nodes(self) -> Dict[str, Any]:
        """验证Food节点"""
        logger.info("\n" + "=" * 60)
        logger.info("验证Food节点")
        logger.info("=" * 60)
        
        async with self.driver.session() as session:
            results = {}
            
            # 1. 验证glycemic_index字段
            logger.info("\n1. 验证glycemic_index字段...")
            query = """
            MATCH (f:Food)
            RETURN 
                count(f) as total,
                count(f.glycemic_index) as with_gi,
                sum(CASE WHEN f.glycemic_index >= 0 AND f.glycemic_index <= 100 THEN 1 ELSE 0 END) as valid_range,
                sum(CASE WHEN f.glycemic_index < 0 OR f.glycemic_index > 100 THEN 1 ELSE 0 END) as invalid_range
            """
            result = await session.run(query)
            record = await result.single()
            
            gi_result = {
                "total_nodes": record["total"],
                "with_gi": record["with_gi"],
                "valid_range": record["valid_range"],
                "invalid_range": record["invalid_range"],
                "coverage": f"{record['with_gi'] / record['total'] * 100:.2f}%",
                "is_valid": record["invalid_range"] == 0
            }
            results["glycemic_index"] = gi_result
            
            logger.info(f"  总节点数: {gi_result['total_nodes']}")
            logger.info(f"  有GI字段的节点: {gi_result['with_gi']}")
            logger.info(f"  有效范围(0-100): {gi_result['valid_range']}")
            logger.info(f"  无效范围: {gi_result['invalid_range']}")
            logger.info(f"  覆盖率: {gi_result['coverage']}")
            logger.info(f"  ✅ 验证通过" if gi_result['is_valid'] else "  ❌ 验证失败")
            
            # 2. 验证glycemic_load字段
            logger.info("\n2. 验证glycemic_load字段...")
            query = """
            MATCH (f:Food)
            WHERE f.glycemic_load IS NOT NULL
            RETURN 
                count(f) as with_gl,
                sum(CASE WHEN f.glycemic_load >= 0 THEN 1 ELSE 0 END) as valid_gl
            """
            result = await session.run(query)
            record = await result.single()
            
            gl_result = {
                "with_gl": record["with_gl"],
                "valid_gl": record["valid_gl"],
                "is_valid": record["with_gl"] == record["valid_gl"]
            }
            results["glycemic_load"] = gl_result
            
            logger.info(f"  有GL字段的节点: {gl_result['with_gl']}")
            logger.info(f"  有效GL值: {gl_result['valid_gl']}")
            logger.info(f"  ✅ 验证通过" if gl_result['is_valid'] else "  ❌ 验证失败")
            
            # 3. 验证digestion_time_minutes字段
            logger.info("\n3. 验证digestion_time_minutes字段...")
            query = """
            MATCH (f:Food)
            WHERE f.digestion_time_minutes IS NOT NULL
            RETURN 
                count(f) as with_digestion,
                sum(CASE WHEN f.digestion_time_minutes >= 30 AND f.digestion_time_minutes <= 240 THEN 1 ELSE 0 END) as valid_range
            """
            result = await session.run(query)
            record = await result.single()
            
            digestion_result = {
                "with_digestion": record["with_digestion"],
                "valid_range": record["valid_range"],
                "is_valid": record["with_digestion"] == record["valid_range"]
            }
            results["digestion_time_minutes"] = digestion_result
            
            logger.info(f"  有消化时间字段的节点: {digestion_result['with_digestion']}")
            logger.info(f"  有效范围(30-240分钟): {digestion_result['valid_range']}")
            logger.info(f"  ✅ 验证通过" if digestion_result['is_valid'] else "  ❌ 验证失败")
            
            # 4. 验证allergens字段
            logger.info("\n4. 验证allergens字段...")
            query = """
            MATCH (f:Food)
            WHERE f.allergens IS NOT NULL
            RETURN count(f) as with_allergens
            """
            result = await session.run(query)
            record = await result.single()
            
            allergens_result = {
                "with_allergens": record["with_allergens"],
                "is_valid": record["with_allergens"] > 0
            }
            results["allergens"] = allergens_result
            
            logger.info(f"  有过敏原字段的节点: {allergens_result['with_allergens']}")
            logger.info(f"  ✅ 验证通过" if allergens_result['is_valid'] else "  ❌ 验证失败")
            
            return results
    
    async def validate_injury_type_nodes(self) -> Dict[str, Any]:
        """验证InjuryType节点"""
        logger.info("\n" + "=" * 60)
        logger.info("验证InjuryType节点")
        logger.info("=" * 60)
        
        async with self.driver.session() as session:
            results = {}
            
            logger.info("\n验证severity_level字段...")
            query = """
            MATCH (i:InjuryType)
            WITH count(i) as total,
                 count(i.severity_level) as with_severity,
                 sum(CASE WHEN i.severity_level IN ['mild', 'moderate', 'severe'] THEN 1 ELSE 0 END) as valid_values
            RETURN total, with_severity, valid_values, (with_severity - valid_values) as invalid_values
            """
            result = await session.run(query)
            record = await result.single()
            
            severity_result = {
                "total_nodes": record["total"],
                "with_severity": record["with_severity"],
                "valid_values": record["valid_values"],
                "invalid_values": record["invalid_values"],
                "coverage": f"{record['with_severity'] / record['total'] * 100:.2f}%",
                "is_valid": record["invalid_values"] == 0 and record["with_severity"] == record["total"]
            }
            results["severity_level"] = severity_result
            
            logger.info(f"  总节点数: {severity_result['total_nodes']}")
            logger.info(f"  有severity_level字段的节点: {severity_result['with_severity']}")
            logger.info(f"  有效值数量: {severity_result['valid_values']}")
            logger.info(f"  无效值数量: {severity_result['invalid_values']}")
            logger.info(f"  覆盖率: {severity_result['coverage']}")
            logger.info(f"  ✅ 验证通过" if severity_result['is_valid'] else "  ❌ 验证失败")
            
            return results
    
    async def validate_rehab_phase_nodes(self) -> Dict[str, Any]:
        """验证RehabilitationPhase节点"""
        logger.info("\n" + "=" * 60)
        logger.info("验证RehabilitationPhase节点")
        logger.info("=" * 60)
        
        async with self.driver.session() as session:
            results = {}
            
            logger.info("\n验证康复阶段节点...")
            query = """
            MATCH (rp:RehabilitationPhase)
            RETURN 
                count(rp) as total,
                collect(rp.phase_id) as phase_ids,
                collect(rp.name_zh) as names
            """
            result = await session.run(query)
            record = await result.single()
            
            expected_phases = ['acute', 'subacute', 'recovery']
            phase_ids = record["phase_ids"]
            
            rehab_result = {
                "total_nodes": record["total"],
                "phase_ids": phase_ids,
                "names": record["names"],
                "expected_phases": expected_phases,
                "is_valid": record["total"] == 3 and set(phase_ids) == set(expected_phases)
            }
            results["rehab_phases"] = rehab_result
            
            logger.info(f"  总节点数: {rehab_result['total_nodes']}")
            logger.info(f"  阶段ID: {rehab_result['phase_ids']}")
            logger.info(f"  阶段名称: {rehab_result['names']}")
            logger.info(f"  ✅ 验证通过" if rehab_result['is_valid'] else "  ❌ 验证失败")
            
            return results
    
    async def validate_rehab_progression_relationships(self) -> Dict[str, Any]:
        """验证REHAB_PROGRESSION关系"""
        logger.info("\n" + "=" * 60)
        logger.info("验证REHAB_PROGRESSION关系")
        logger.info("=" * 60)
        
        async with self.driver.session() as session:
            results = {}
            
            logger.info("\n验证康复渐进关系...")
            query = """
            MATCH ()-[r:REHAB_PROGRESSION]->()
            RETURN 
                count(r) as total,
                sum(CASE WHEN r.progression_order IS NOT NULL THEN 1 ELSE 0 END) as with_order,
                sum(CASE WHEN r.criteria IS NOT NULL THEN 1 ELSE 0 END) as with_criteria,
                sum(CASE WHEN r.estimated_weeks IS NOT NULL THEN 1 ELSE 0 END) as with_weeks
            """
            result = await session.run(query)
            record = await result.single()
            
            progression_result = {
                "total_relationships": record["total"],
                "with_order": record["with_order"],
                "with_criteria": record["with_criteria"],
                "with_weeks": record["with_weeks"],
                "is_valid": (record["total"] > 0 and 
                           record["with_order"] == record["total"] and
                           record["with_criteria"] == record["total"] and
                           record["with_weeks"] == record["total"])
            }
            results["rehab_progression"] = progression_result
            
            logger.info(f"  总关系数: {progression_result['total_relationships']}")
            logger.info(f"  有progression_order的关系: {progression_result['with_order']}")
            logger.info(f"  有criteria的关系: {progression_result['with_criteria']}")
            logger.info(f"  有estimated_weeks的关系: {progression_result['with_weeks']}")
            logger.info(f"  ✅ 验证通过" if progression_result['is_valid'] else "  ❌ 验证失败")
            
            # 检查循环依赖
            logger.info("\n检查循环依赖...")
            query = """
            MATCH path = (e1:Exercise)-[:REHAB_PROGRESSION*]->(e1)
            RETURN count(path) as cycles
            """
            result = await session.run(query)
            record = await result.single()
            
            cycle_result = {
                "cycles_found": record["cycles"],
                "is_valid": record["cycles"] == 0
            }
            results["cycle_check"] = cycle_result
            
            logger.info(f"  发现的循环: {cycle_result['cycles_found']}")
            logger.info(f"  ✅ 无循环依赖" if cycle_result['is_valid'] else "  ❌ 发现循环依赖")
            
            return results
    
    async def generate_summary(self):
        """生成验证摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("验证摘要")
        logger.info("=" * 60)
        
        all_valid = True
        
        # Exercise节点验证
        exercise_valid = all(
            result.get("is_valid", False) 
            for result in self.validation_results["exercise"].values()
        )
        logger.info(f"\nExercise节点: {'✅ 通过' if exercise_valid else '❌ 失败'}")
        all_valid = all_valid and exercise_valid
        
        # Food节点验证
        food_valid = all(
            result.get("is_valid", False) 
            for result in self.validation_results["food"].values()
        )
        logger.info(f"Food节点: {'✅ 通过' if food_valid else '❌ 失败'}")
        all_valid = all_valid and food_valid
        
        # InjuryType节点验证
        injury_valid = all(
            result.get("is_valid", False) 
            for result in self.validation_results["injury_type"].values()
        )
        logger.info(f"InjuryType节点: {'✅ 通过' if injury_valid else '❌ 失败'}")
        all_valid = all_valid and injury_valid
        
        # RehabilitationPhase节点验证
        rehab_valid = all(
            result.get("is_valid", False) 
            for result in self.validation_results["rehab_phase"].values()
        )
        logger.info(f"RehabilitationPhase节点: {'✅ 通过' if rehab_valid else '❌ 失败'}")
        all_valid = all_valid and rehab_valid
        
        # REHAB_PROGRESSION关系验证
        progression_valid = all(
            result.get("is_valid", False) 
            for result in self.validation_results["rehab_progression"].values()
        )
        logger.info(f"REHAB_PROGRESSION关系: {'✅ 通过' if progression_valid else '❌ 失败'}")
        all_valid = all_valid and progression_valid
        
        self.validation_results["summary"] = {
            "all_valid": all_valid,
            "exercise_valid": exercise_valid,
            "food_valid": food_valid,
            "injury_type_valid": injury_valid,
            "rehab_phase_valid": rehab_valid,
            "rehab_progression_valid": progression_valid
        }
        
        logger.info("\n" + "=" * 60)
        logger.info(f"总体验证结果: {'✅ 全部通过' if all_valid else '❌ 存在失败项'}")
        logger.info("=" * 60)
    
    async def save_report(self, output_file: str = "validation_report.json"):
        """保存验证报告"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.validation_results, f, ensure_ascii=False, indent=2)
        logger.info(f"\n验证报告已保存到: {output_file}")
    
    async def run_all_validations(self):
        """运行所有验证"""
        try:
            # 1. 验证Exercise节点
            self.validation_results["exercise"] = await self.validate_exercise_nodes()
            
            # 2. 验证Food节点
            self.validation_results["food"] = await self.validate_food_nodes()
            
            # 3. 验证InjuryType节点
            self.validation_results["injury_type"] = await self.validate_injury_type_nodes()
            
            # 4. 验证RehabilitationPhase节点
            self.validation_results["rehab_phase"] = await self.validate_rehab_phase_nodes()
            
            # 5. 验证REHAB_PROGRESSION关系
            self.validation_results["rehab_progression"] = await self.validate_rehab_progression_relationships()
            
            # 6. 生成摘要
            await self.generate_summary()
            
            # 7. 保存报告
            await self.save_report()
            
        except Exception as e:
            logger.error(f"验证过程中发生错误: {e}", exc_info=True)
            raise


async def main():
    """主函数"""
    # Neo4j连接配置
    NEO4J_URI = "bolt://fitness_neo4j:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "build_body_2024"
    
    validator = CompleteDataValidator(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        await validator.run_all_validations()
    finally:
        await validator.close()


if __name__ == "__main__":
    asyncio.run(main())
