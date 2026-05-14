#!/usr/bin/env python3
"""
RehabilitationPhase节点创建器

功能：
1. 创建康复阶段节点（acute、subacute、recovery）
2. 创建REHAB_PROGRESSION关系（康复渐进路径）

作者：薛小川
日期：2025-12-15
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from neo4j import AsyncGraphDatabase

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SupplementResult:
    """数据补充结果"""
    
    def __init__(
        self,
        total_nodes: int = 0,
        updated_nodes: int = 0,
        errors: List[Dict[str, Any]] = None
    ):
        self.total_nodes = total_nodes
        self.updated_nodes = updated_nodes
        self.errors = errors or []
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_nodes": self.total_nodes,
            "updated_nodes": self.updated_nodes,
            "errors": self.errors,
            "timestamp": self.timestamp
        }


class RehabilitationPhaseCreator:
    """康复阶段创建器"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """
        初始化创建器
        
        Args:
            neo4j_uri: Neo4j连接URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
        """
        self.driver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
    
    async def close(self):
        """关闭连接"""
        await self.driver.close()
    
    async def create_phases(self) -> SupplementResult:
        """
        创建康复阶段节点
        
        Returns:
            SupplementResult: 创建结果
        """
        logger.info("=" * 60)
        logger.info("开始创建RehabilitationPhase节点")
        logger.info("=" * 60)
        
        try:
            async with self.driver.session() as session:
                # 定义三个康复阶段
                phases = [
                    {
                        "phase_id": "acute",
                        "name_zh": "急性期",
                        "name_en": "Acute Phase",
                        "duration_days": 7,
                        "goals": json.dumps(["减轻疼痛", "控制炎症", "保护受伤组织"], ensure_ascii=False),
                        "allowed_activities": json.dumps(["被动活动", "等长收缩", "冰敷", "休息"], ensure_ascii=False),
                        "contraindicated_activities": json.dumps(["负重训练", "爆发力训练", "高强度运动", "拉伸受伤部位"], ensure_ascii=False),
                        "description": "损伤后的初期阶段，主要目标是控制炎症和疼痛，保护受伤组织免受进一步损伤"
                    },
                    {
                        "phase_id": "subacute",
                        "name_zh": "亚急性期",
                        "name_en": "Subacute Phase",
                        "duration_days": 14,
                        "goals": json.dumps(["恢复活动度", "增强肌力", "改善功能", "减少代偿"], ensure_ascii=False),
                        "allowed_activities": json.dumps(["主动活动", "轻负荷训练", "本体感觉训练", "渐进性拉伸"], ensure_ascii=False),
                        "contraindicated_activities": json.dumps(["高强度训练", "冲击性动作", "过度拉伸", "疼痛性动作"], ensure_ascii=False),
                        "description": "炎症逐渐消退，开始恢复关节活动度和肌肉力量，为功能性训练做准备"
                    },
                    {
                        "phase_id": "recovery",
                        "name_zh": "恢复期",
                        "name_en": "Recovery Phase",
                        "duration_days": 30,
                        "goals": json.dumps(["恢复运动表现", "预防再次受伤", "恢复运动专项能力", "建立长期训练习惯"], ensure_ascii=False),
                        "allowed_activities": json.dumps(["渐进负荷训练", "运动专项训练", "功能性训练", "爆发力训练"], ensure_ascii=False),
                        "contraindicated_activities": json.dumps(["过早恢复竞技", "忽视热身", "过度训练"], ensure_ascii=False),
                        "description": "功能基本恢复，逐步恢复到损伤前的运动水平，并建立预防再次受伤的训练模式"
                    }
                ]
                
                logger.info(f"\n准备创建 {len(phases)} 个康复阶段节点")
                
                created_count = 0
                for phase in phases:
                    logger.info(f"\n创建阶段: {phase['name_zh']} ({phase['phase_id']})")
                    
                    # 使用MERGE确保幂等性
                    query = """
                    MERGE (rp:RehabilitationPhase {phase_id: $phase_id})
                    SET rp.name_zh = $name_zh,
                        rp.name_en = $name_en,
                        rp.duration_days = $duration_days,
                        rp.goals = $goals,
                        rp.allowed_activities = $allowed_activities,
                        rp.contraindicated_activities = $contraindicated_activities,
                        rp.description = $description,
                        rp.created_at = CASE 
                            WHEN rp.created_at IS NULL THEN datetime()
                            ELSE rp.created_at
                        END,
                        rp.updated_at = datetime()
                    RETURN rp.phase_id as phase_id, rp.name_zh as name_zh
                    """
                    
                    result = await session.run(query, phase)
                    record = await result.single()
                    
                    if record:
                        logger.info(f"   ✅ 成功创建/更新: {record['name_zh']} (ID: {record['phase_id']})")
                        logger.info(f"      - 持续时间: {phase['duration_days']} 天")
                        logger.info(f"      - 目标: {json.loads(phase['goals'])}")
                        created_count += 1
                    else:
                        logger.warning(f"   ⚠️ 创建失败: {phase['name_zh']}")
                
                # 验证创建结果
                logger.info("\n验证康复阶段节点...")
                validation_result = await self._validate_phases(session)
                
                logger.info("\n" + "=" * 60)
                logger.info("RehabilitationPhase节点创建完成")
                logger.info(f"预期节点数: {len(phases)}")
                logger.info(f"实际创建数: {created_count}")
                logger.info(f"验证结果: {validation_result}")
                logger.info("=" * 60)
                
                return SupplementResult(
                    total_nodes=len(phases),
                    updated_nodes=created_count,
                    errors=[]
                )
        
        except Exception as e:
            logger.error(f"创建RehabilitationPhase节点失败: {e}", exc_info=True)
            return SupplementResult(
                total_nodes=0,
                updated_nodes=0,
                errors=[{"stage": "create_rehab_phases", "error": str(e)}]
            )
    
    async def create_progressions(self) -> SupplementResult:
        """
        创建康复渐进关系
        
        Returns:
            SupplementResult: 创建结果
        """
        logger.info("\n" + "=" * 60)
        logger.info("开始创建REHAB_PROGRESSION关系")
        logger.info("=" * 60)
        
        try:
            async with self.driver.session() as session:
                # 定义康复渐进路径
                # 每个路径包含：起始动作、目标动作、进阶标准、预计周数
                progressions = [
                    # 深蹲康复路径
                    {
                        "from_exercise": "靠墙静蹲",
                        "to_exercise": "徒手深蹲",
                        "progression_order": 1,
                        "criteria": "无痛完成3组×30秒靠墙静蹲，膝关节无肿胀",
                        "estimated_weeks": 2,
                        "phase": "subacute",
                        "notes": "从等长收缩过渡到动态动作"
                    },
                    {
                        "from_exercise": "徒手深蹲",
                        "to_exercise": "杠铃深蹲",
                        "progression_order": 2,
                        "criteria": "完成3组×15次徒手深蹲，动作标准无代偿",
                        "estimated_weeks": 4,
                        "phase": "recovery",
                        "notes": "从自重过渡到负重训练"
                    },
                    
                    # 卧推康复路径
                    {
                        "from_exercise": "俯卧撑",
                        "to_exercise": "哑铃卧推",
                        "progression_order": 1,
                        "criteria": "完成3组×10次标准俯卧撑，肩关节无疼痛",
                        "estimated_weeks": 3,
                        "phase": "subacute",
                        "notes": "从闭链动作过渡到开链动作"
                    },
                    {
                        "from_exercise": "哑铃卧推",
                        "to_exercise": "杠铃卧推",
                        "progression_order": 2,
                        "criteria": "完成3组×12次哑铃卧推，重量达到体重的30%",
                        "estimated_weeks": 4,
                        "phase": "recovery",
                        "notes": "从单侧控制过渡到双侧协同"
                    },
                    
                    # 硬拉康复路径
                    {
                        "from_exercise": "罗马尼亚硬拉",
                        "to_exercise": "传统硬拉",
                        "progression_order": 1,
                        "criteria": "完成3组×10次罗马尼亚硬拉，腰部无不适",
                        "estimated_weeks": 3,
                        "phase": "subacute",
                        "notes": "从髋主导动作过渡到全身复合动作"
                    },
                    
                    # 引体向上康复路径
                    {
                        "from_exercise": "弹力带辅助引体向上",
                        "to_exercise": "引体向上",
                        "progression_order": 1,
                        "criteria": "完成3组×8次辅助引体向上，肩关节稳定",
                        "estimated_weeks": 4,
                        "phase": "recovery",
                        "notes": "从辅助过渡到自重"
                    },
                    
                    # 腿部康复路径
                    {
                        "from_exercise": "腿举",
                        "to_exercise": "杠铃深蹲",
                        "progression_order": 1,
                        "criteria": "完成3组×12次腿举，膝关节无疼痛",
                        "estimated_weeks": 3,
                        "phase": "subacute",
                        "notes": "从固定轨迹过渡到自由重量"
                    }
                ]
                
                logger.info(f"\n准备创建 {len(progressions)} 个康复渐进关系")
                
                created_count = 0
                skipped_count = 0
                
                for prog in progressions:
                    logger.info(f"\n创建渐进关系: {prog['from_exercise']} → {prog['to_exercise']}")
                    
                    # 查找起始和目标动作
                    query = """
                    MATCH (e1:Exercise)
                    WHERE e1.name_zh CONTAINS $from_exercise
                       OR e1.name_en CONTAINS $from_exercise
                    WITH e1 LIMIT 1
                    MATCH (e2:Exercise)
                    WHERE e2.name_zh CONTAINS $to_exercise
                       OR e2.name_en CONTAINS $to_exercise
                    WITH e1, e2 LIMIT 1
                    MERGE (e1)-[r:REHAB_PROGRESSION]->(e2)
                    SET r.progression_order = $progression_order,
                        r.criteria = $criteria,
                        r.estimated_weeks = $estimated_weeks,
                        r.phase = $phase,
                        r.notes = $notes,
                        r.created_at = CASE 
                            WHEN r.created_at IS NULL THEN datetime()
                            ELSE r.created_at
                        END,
                        r.updated_at = datetime()
                    RETURN e1.name_zh as from_name, 
                           e2.name_zh as to_name,
                           r.progression_order as order
                    """
                    
                    result = await session.run(query, prog)
                    record = await result.single()
                    
                    if record:
                        logger.info(f"   ✅ 成功创建: {record['from_name']} → {record['to_name']}")
                        logger.info(f"      - 顺序: {record['order']}")
                        logger.info(f"      - 标准: {prog['criteria']}")
                        logger.info(f"      - 预计: {prog['estimated_weeks']} 周")
                        created_count += 1
                    else:
                        logger.warning(f"   ⚠️ 跳过（动作未找到）: {prog['from_exercise']} → {prog['to_exercise']}")
                        skipped_count += 1
                
                # 验证创建结果
                logger.info("\n验证REHAB_PROGRESSION关系...")
                validation_result = await self._validate_progressions(session)
                
                logger.info("\n" + "=" * 60)
                logger.info("REHAB_PROGRESSION关系创建完成")
                logger.info(f"预期关系数: {len(progressions)}")
                logger.info(f"实际创建数: {created_count}")
                logger.info(f"跳过数量: {skipped_count}")
                logger.info(f"验证结果: {validation_result}")
                logger.info("=" * 60)
                
                return SupplementResult(
                    total_nodes=len(progressions),
                    updated_nodes=created_count,
                    errors=[] if skipped_count == 0 else [
                        {"stage": "create_progressions", "warning": f"{skipped_count} 个关系因动作未找到而跳过"}
                    ]
                )
        
        except Exception as e:
            logger.error(f"创建REHAB_PROGRESSION关系失败: {e}", exc_info=True)
            return SupplementResult(
                total_nodes=0,
                updated_nodes=0,
                errors=[{"stage": "create_progressions", "error": str(e)}]
            )
    
    async def _validate_phases(self, session) -> Dict[str, Any]:
        """
        验证康复阶段节点
        
        Args:
            session: Neo4j会话
            
        Returns:
            Dict: 验证结果
        """
        # 检查节点数量
        query_count = """
        MATCH (rp:RehabilitationPhase)
        RETURN count(rp) as total_count,
               collect(rp.phase_id) as phase_ids,
               collect(rp.name_zh) as names
        """
        result = await session.run(query_count)
        record = await result.single()
        
        total_count = record["total_count"]
        phase_ids = record["phase_ids"]
        names = record["names"]
        
        # 检查必需的三个阶段是否都存在
        required_phases = {"acute", "subacute", "recovery"}
        existing_phases = set(phase_ids)
        missing_phases = required_phases - existing_phases
        
        validation_result = {
            "total_nodes": total_count,
            "phase_ids": phase_ids,
            "names": names,
            "has_all_required": len(missing_phases) == 0,
            "missing_phases": list(missing_phases),
            "is_valid": total_count == 3 and len(missing_phases) == 0
        }
        
        logger.info(f"   总节点数: {total_count}")
        logger.info(f"   阶段ID: {phase_ids}")
        logger.info(f"   阶段名称: {names}")
        
        if validation_result["is_valid"]:
            logger.info("   ✅ 验证通过：所有必需的康复阶段都已创建")
        else:
            logger.warning(f"   ⚠️ 验证失败：缺少阶段 {missing_phases}")
        
        return validation_result
    
    async def _validate_progressions(self, session) -> Dict[str, Any]:
        """
        验证REHAB_PROGRESSION关系
        
        Args:
            session: Neo4j会话
            
        Returns:
            Dict: 验证结果
        """
        # 1. 统计关系数量
        query_count = """
        MATCH ()-[r:REHAB_PROGRESSION]->()
        RETURN count(r) as total_count
        """
        result_count = await session.run(query_count)
        record_count = await result_count.single()
        total_count = record_count["total_count"]
        
        # 2. 检查关系属性完整性
        query_attrs = """
        MATCH (e1:Exercise)-[r:REHAB_PROGRESSION]->(e2:Exercise)
        RETURN e1.name_zh as from_exercise,
               e2.name_zh as to_exercise,
               r.progression_order as order,
               r.criteria as criteria,
               r.estimated_weeks as weeks,
               r.phase as phase
        ORDER BY r.progression_order
        """
        result_attrs = await session.run(query_attrs)
        records_attrs = await result_attrs.data()
        
        # 3. 检查是否有循环依赖（简单检查：同一动作不应既是起点又是终点指向自己）
        query_cycle = """
        MATCH (e:Exercise)-[r:REHAB_PROGRESSION]->(e)
        RETURN count(r) as self_loop_count
        """
        result_cycle = await session.run(query_cycle)
        record_cycle = await result_cycle.single()
        self_loop_count = record_cycle["self_loop_count"]
        
        # 4. 检查必需属性是否完整
        incomplete_count = sum(
            1 for r in records_attrs
            if not all([r.get("order"), r.get("criteria"), r.get("weeks")])
        )
        
        validation_result = {
            "total_relationships": total_count,
            "relationships": records_attrs,
            "has_self_loops": self_loop_count > 0,
            "incomplete_attributes": incomplete_count,
            "is_valid": total_count > 0 and self_loop_count == 0 and incomplete_count == 0
        }
        
        logger.info(f"   总关系数: {total_count}")
        logger.info(f"   自循环数: {self_loop_count}")
        logger.info(f"   属性不完整数: {incomplete_count}")
        
        if validation_result["is_valid"]:
            logger.info("   ✅ 验证通过：所有关系都有完整的属性且无循环依赖")
        else:
            logger.warning("   ⚠️ 验证失败：存在问题")
        
        # 打印关系详情
        logger.info("\n   康复渐进路径:")
        for r in records_attrs:
            logger.info(f"      {r['from_exercise']} → {r['to_exercise']}")
            logger.info(f"         顺序: {r['order']}, 周数: {r['weeks']}, 阶段: {r['phase']}")
        
        return validation_result


async def main():
    """主函数"""
    import os
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # Neo4j配置
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    # 创建创建器
    creator = RehabilitationPhaseCreator(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        # 1. 创建康复阶段节点
        phases_result = await creator.create_phases()
        print("\n" + "=" * 60)
        print("📊 康复阶段节点创建结果")
        print("=" * 60)
        print(json.dumps(phases_result.to_dict(), indent=2, ensure_ascii=False))
        
        # 2. 创建康复渐进关系
        progressions_result = await creator.create_progressions()
        print("\n" + "=" * 60)
        print("📊 康复渐进关系创建结果")
        print("=" * 60)
        print(json.dumps(progressions_result.to_dict(), indent=2, ensure_ascii=False))
        
    finally:
        await creator.close()


if __name__ == "__main__":
    asyncio.run(main())
