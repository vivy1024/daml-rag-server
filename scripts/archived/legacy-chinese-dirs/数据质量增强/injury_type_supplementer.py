#!/usr/bin/env python3
"""
InjuryType节点数据补充器

功能：
1. 补充严重程度分级 (severity_level)
2. 基于损伤类型分类为mild/moderate/severe

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


class InjuryTypeSupplementer:
    """InjuryType节点补充器"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        """
        初始化补充器
        
        Args:
            neo4j_uri: Neo4j连接URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
        """
        self.driver = AsyncGraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        # 严重程度映射规则
        self.severity_mapping = self._load_severity_mapping()
    
    def _load_severity_mapping(self) -> Dict[str, str]:
        """
        加载严重程度映射规则
        
        基于医学标准和康复实践，将损伤类型分为三个等级：
        - mild（轻度）：轻微不适，可继续训练但需调整
        - moderate（中度）：明显疼痛，需要休息和康复训练
        - severe（重度）：严重损伤，需要医疗干预和长期康复
        
        Returns:
            Dict: 损伤名称到严重程度的映射
        """
        return {
            # 轻度损伤 (mild)
            "肌肉酸痛": "mild",
            "轻度肌肉拉伤": "mild",
            "轻度关节扭伤": "mild",
            "肌肉紧张": "mild",
            "轻度肌腱炎": "mild",
            "延迟性肌肉酸痛": "mild",
            "DOMS": "mild",
            
            # 中度损伤 (moderate)
            "肌肉拉伤": "moderate",
            "关节扭伤": "moderate",
            "肌腱炎": "moderate",
            "滑囊炎": "moderate",
            "筋膜炎": "moderate",
            "肩袖损伤": "moderate",
            "网球肘": "moderate",
            "高尔夫球肘": "moderate",
            "髌骨肌腱炎": "moderate",
            "跟腱炎": "moderate",
            "腰肌劳损": "moderate",
            "颈椎劳损": "moderate",
            
            # 重度损伤 (severe)
            "肌肉撕裂": "severe",
            "韧带断裂": "severe",
            "骨折": "severe",
            "椎间盘突出": "severe",
            "半月板撕裂": "severe",
            "前交叉韧带损伤": "severe",
            "后交叉韧带损伤": "severe",
            "肩关节脱位": "severe",
            "跟腱断裂": "severe",
            "应力性骨折": "severe",
            "腰椎间盘突出": "severe",
            "颈椎间盘突出": "severe"
        }
    
    async def close(self):
        """关闭连接"""
        await self.driver.close()
    
    async def supplement(self) -> SupplementResult:
        """
        执行InjuryType节点的严重程度补充
        
        Returns:
            SupplementResult: 补充结果
        """
        logger.info("=" * 60)
        logger.info("开始InjuryType节点数据补充")
        logger.info("=" * 60)
        
        try:
            async with self.driver.session() as session:
                # 1. 获取所有InjuryType节点
                logger.info("\n步骤1：获取所有InjuryType节点")
                injury_types = await self._get_all_injury_types(session)
                logger.info(f"   找到 {len(injury_types)} 个InjuryType节点")
                
                # 2. 补充严重程度
                logger.info("\n步骤2：补充严重程度分级")
                updated_count = await self._supplement_severity_level(session)
                
                # 3. 验证结果
                logger.info("\n步骤3：验证补充结果")
                validation_result = await self._validate_severity_levels(session)
                
                logger.info("\n" + "=" * 60)
                logger.info("InjuryType节点数据补充完成")
                logger.info(f"总节点数: {len(injury_types)}")
                logger.info(f"已更新节点数: {updated_count}")
                logger.info(f"验证结果: {validation_result}")
                logger.info("=" * 60)
                
                return SupplementResult(
                    total_nodes=len(injury_types),
                    updated_nodes=updated_count,
                    errors=[]
                )
        
        except Exception as e:
            logger.error(f"InjuryType节点补充失败: {e}", exc_info=True)
            return SupplementResult(
                total_nodes=0,
                updated_nodes=0,
                errors=[{"stage": "injury_type_supplement", "error": str(e)}]
            )
    
    async def _get_all_injury_types(self, session) -> List[Dict[str, Any]]:
        """
        获取所有InjuryType节点
        
        Args:
            session: Neo4j会话
            
        Returns:
            List: InjuryType节点列表
        """
        query = """
        MATCH (it:InjuryType)
        RETURN it.id as id,
               it.name as name_en,
               it.name_zh as name_zh,
               it.severity_level as current_severity
        ORDER BY it.id
        """
        result = await session.run(query)
        injury_types = await result.data()
        
        # 打印当前状态
        for it in injury_types:
            current = it.get('current_severity', 'NULL')
            logger.info(f"   - {it['name_zh']} ({it['name_en']}): {current}")
        
        return injury_types
    
    async def _supplement_severity_level(self, session) -> int:
        """
        补充严重程度分级
        
        Args:
            session: Neo4j会话
            
        Returns:
            int: 更新的节点数量
        """
        total_updated = 0
        
        # 按严重程度分类更新
        for severity_level in ['mild', 'moderate', 'severe']:
            # 获取该严重程度的损伤名称列表
            injury_names = [
                name for name, level in self.severity_mapping.items()
                if level == severity_level
            ]
            
            if not injury_names:
                continue
            
            logger.info(f"\n   更新 {severity_level} 级别损伤...")
            
            # 使用中文名称匹配
            for injury_name in injury_names:
                query = """
                MATCH (it:InjuryType)
                WHERE it.name_zh CONTAINS $injury_name
                   OR it.name CONTAINS $injury_name
                SET it.severity_level = $severity_level,
                    it.severity_updated_at = datetime()
                RETURN count(it) as updated_count, 
                       collect(it.name_zh) as updated_names
                """
                result = await session.run(query, {
                    "injury_name": injury_name,
                    "severity_level": severity_level
                })
                record = await result.single()
                
                if record and record["updated_count"] > 0:
                    updated_names = record["updated_names"]
                    logger.info(f"      ✅ {injury_name}: {updated_names}")
                    total_updated += record["updated_count"]
            
            logger.info(f"   {severity_level} 级别: 已更新")
        
        # 对于未匹配的节点，使用默认规则
        logger.info("\n   处理未分类的损伤...")
        default_query = """
        MATCH (it:InjuryType)
        WHERE it.severity_level IS NULL
        SET it.severity_level = 'moderate',
            it.severity_updated_at = datetime(),
            it.severity_note = '默认分类，需人工审核'
        RETURN count(it) as updated_count,
               collect(it.name_zh) as updated_names
        """
        result = await session.run(default_query)
        record = await result.single()
        
        if record and record["updated_count"] > 0:
            logger.info(f"      ⚠️ 默认分类为moderate: {record['updated_names']}")
            total_updated += record["updated_count"]
        
        return total_updated
    
    async def _validate_severity_levels(self, session) -> Dict[str, Any]:
        """
        验证严重程度分级结果
        
        Args:
            session: Neo4j会话
            
        Returns:
            Dict: 验证结果
        """
        # 1. 检查是否所有节点都有severity_level
        query_all = """
        MATCH (it:InjuryType)
        RETURN count(it) as total_count
        """
        result_all = await session.run(query_all)
        record_all = await result_all.single()
        total_count = record_all["total_count"]
        
        # 2. 检查有severity_level的节点数
        query_with_severity = """
        MATCH (it:InjuryType)
        WHERE it.severity_level IS NOT NULL
        RETURN count(it) as with_severity_count
        """
        result_with = await session.run(query_with_severity)
        record_with = await result_with.single()
        with_severity_count = record_with["with_severity_count"]
        
        # 3. 按严重程度统计
        query_by_level = """
        MATCH (it:InjuryType)
        WHERE it.severity_level IS NOT NULL
        RETURN it.severity_level as level, 
               count(it) as count,
               collect(it.name_zh) as names
        ORDER BY level
        """
        result_by_level = await session.run(query_by_level)
        records_by_level = await result_by_level.data()
        
        # 4. 检查枚举值是否合法
        query_invalid = """
        MATCH (it:InjuryType)
        WHERE it.severity_level IS NOT NULL
          AND NOT (it.severity_level IN ['mild', 'moderate', 'severe'])
        RETURN count(it) as invalid_count,
               collect(it.name_zh) as invalid_names
        """
        result_invalid = await session.run(query_invalid)
        record_invalid = await result_invalid.single()
        invalid_count = record_invalid["invalid_count"]
        
        # 构建验证结果
        validation_result = {
            "total_nodes": total_count,
            "nodes_with_severity": with_severity_count,
            "coverage_percentage": round(with_severity_count / total_count * 100, 2) if total_count > 0 else 0,
            "by_severity_level": {
                record["level"]: {
                    "count": record["count"],
                    "names": record["names"]
                }
                for record in records_by_level
            },
            "invalid_count": invalid_count,
            "is_valid": invalid_count == 0 and with_severity_count == total_count
        }
        
        # 打印验证结果
        logger.info(f"   总节点数: {total_count}")
        logger.info(f"   已补充节点数: {with_severity_count}")
        logger.info(f"   覆盖率: {validation_result['coverage_percentage']}%")
        logger.info(f"   非法值数量: {invalid_count}")
        
        for level, data in validation_result["by_severity_level"].items():
            logger.info(f"   {level}: {data['count']} 个 - {data['names']}")
        
        if validation_result["is_valid"]:
            logger.info("   ✅ 验证通过：所有节点都有合法的severity_level")
        else:
            logger.warning("   ⚠️ 验证失败：存在未补充或非法的severity_level")
        
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
    
    # 创建补充器
    supplementer = InjuryTypeSupplementer(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        # 执行补充
        result = await supplementer.supplement()
        
        # 输出结果
        print("\n" + "=" * 60)
        print("📊 补充结果")
        print("=" * 60)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        
    finally:
        await supplementer.close()


if __name__ == "__main__":
    asyncio.run(main())
