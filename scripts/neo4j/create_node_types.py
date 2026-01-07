# -*- coding: utf-8 -*-
"""
Neo4j节点类型创建脚本

创建新的分类节点类型：
- ForceType: 力的方向（推力/拉力/保持）
- MechanicType: 动作机制（复合/单关节）
- KineticChain: 动力链类型（开链/闭链/混合）
- GripType: 握法类型（正手握/反手握/对握等）
- TrainingLevel: 训练等级（初学者/新手/中级/高级/精英）

版本: v1.0.0
日期: 2026-01-05
Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
"""

import sys
import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from framework.retrieval.graph.neo4j_manager import Neo4jManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class NodeTypeDefinition:
    """节点类型定义"""
    label: str
    nodes: List[Dict[str, str]]
    description: str


class NodeTypeCreator:
    """节点类型创建器"""
    
    # 节点类型定义
    NODE_TYPES = [
        NodeTypeDefinition(
            label="ForceType",
            description="力的方向类型",
            nodes=[
                {"name": "push", "name_zh": "推力"},
                {"name": "pull", "name_zh": "拉力"},
                {"name": "hold", "name_zh": "保持"},
            ]
        ),
        NodeTypeDefinition(
            label="MechanicType",
            description="动作机制类型",
            nodes=[
                {"name": "compound", "name_zh": "复合"},
                {"name": "isolation", "name_zh": "单关节"},
            ]
        ),
        NodeTypeDefinition(
            label="KineticChain",
            description="动力链类型",
            nodes=[
                {"name": "open_chain", "name_zh": "开链"},
                {"name": "closed_chain", "name_zh": "闭链"},
                {"name": "mixed", "name_zh": "混合"},
            ]
        ),
        NodeTypeDefinition(
            label="GripType",
            description="握法类型",
            nodes=[
                {"name": "overhand", "name_zh": "正手握"},
                {"name": "underhand", "name_zh": "反手握"},
                {"name": "neutral", "name_zh": "对握"},
                {"name": "mixed", "name_zh": "混合握"},
                {"name": "hook", "name_zh": "钩握"},
            ]
        ),
        NodeTypeDefinition(
            label="TrainingLevel",
            description="训练等级",
            nodes=[
                {"name": "novice", "name_zh": "零基础"},
                {"name": "beginner", "name_zh": "初级"},
                {"name": "intermediate", "name_zh": "中级"},
                {"name": "advanced", "name_zh": "高级"},
            ]
        ),
    ]
    
    def __init__(self, neo4j_manager: Neo4jManager):
        """
        初始化节点类型创建器
        
        Args:
            neo4j_manager: Neo4j管理器实例
        """
        self.manager = neo4j_manager
        
    def create_node_type(self, node_def: NodeTypeDefinition) -> Dict[str, Any]:
        """
        创建单个节点类型的所有节点
        
        Args:
            node_def: 节点类型定义
            
        Returns:
            创建结果统计
        """
        label = node_def.label
        created_count = 0
        existing_count = 0
        updated_count = 0
        errors = []
        
        logger.info(f"开始创建 {label} 节点类型 ({node_def.description})...")
        
        for node_data in node_def.nodes:
            try:
                # 检查节点是否已存在
                check_query = f"""
                MATCH (n:{label} {{name: $name}})
                RETURN n
                """
                existing = self.manager.execute_query(check_query, {"name": node_data["name"]})
                
                if existing:
                    logger.debug(f"  节点已存在: {label}({node_data['name']})")
                    existing_count += 1
                    
                    # 更新name_zh属性（如果需要）
                    update_query = f"""
                    MATCH (n:{label} {{name: $name}})
                    SET n.name_zh = $name_zh
                    RETURN n
                    """
                    self.manager.execute_write(update_query, node_data)
                    updated_count += 1
                    logger.info(f"  🔄 更新节点: {label}({node_data['name']}, {node_data['name_zh']})")
                else:
                    # 创建新节点
                    create_query = f"""
                    CREATE (n:{label} {{name: $name, name_zh: $name_zh}})
                    RETURN n
                    """
                    self.manager.execute_write(create_query, node_data)
                    logger.info(f"  ✅ 创建节点: {label}({node_data['name']}, {node_data['name_zh']})")
                    created_count += 1
                    
            except Exception as e:
                error_msg = f"创建节点 {label}({node_data['name']}) 失败: {str(e)}"
                logger.error(f"  ❌ {error_msg}")
                errors.append(error_msg)
                
        return {
            "label": label,
            "description": node_def.description,
            "created": created_count,
            "existing": existing_count,
            "updated": updated_count,
            "total": len(node_def.nodes),
            "errors": errors
        }
        
    def create_all_node_types(self) -> Dict[str, Any]:
        """
        创建所有节点类型
        
        Returns:
            创建结果汇总
        """
        results = []
        total_created = 0
        total_existing = 0
        total_updated = 0
        total_errors = []
        
        logger.info("=" * 60)
        logger.info("开始创建Neo4j节点类型")
        logger.info("=" * 60)
        
        for node_def in self.NODE_TYPES:
            result = self.create_node_type(node_def)
            results.append(result)
            total_created += result["created"]
            total_existing += result["existing"]
            total_updated += result.get("updated", 0)
            total_errors.extend(result["errors"])
            
        logger.info("=" * 60)
        logger.info("节点类型创建完成")
        logger.info(f"  新创建: {total_created}")
        logger.info(f"  已存在: {total_existing}")
        logger.info(f"  已更新: {total_updated}")
        logger.info(f"  错误数: {len(total_errors)}")
        logger.info("=" * 60)
        
        return {
            "results": results,
            "summary": {
                "total_created": total_created,
                "total_existing": total_existing,
                "total_updated": total_updated,
                "total_errors": len(total_errors),
                "errors": total_errors
            }
        }
        
    def verify_node_types(self) -> Dict[str, Any]:
        """
        验证所有节点类型是否正确创建
        
        Returns:
            验证结果
        """
        logger.info("\n验证节点类型...")
        verification = {}
        
        for node_def in self.NODE_TYPES:
            label = node_def.label
            
            # 查询该类型的所有节点
            query = f"""
            MATCH (n:{label})
            RETURN n.name as name, n.name_zh as name_zh
            ORDER BY n.name
            """
            
            results = self.manager.execute_query(query, {})
            
            # 检查完整性
            expected_names = {n["name"] for n in node_def.nodes}
            actual_names = {r["name"] for r in results}
            
            # 检查双语属性
            missing_name_zh = [r for r in results if not r.get("name_zh")]
            
            verification[label] = {
                "expected_count": len(node_def.nodes),
                "actual_count": len(results),
                "missing_nodes": list(expected_names - actual_names),
                "extra_nodes": list(actual_names - expected_names),
                "missing_name_zh": [r["name"] for r in missing_name_zh],
                "is_complete": expected_names == actual_names and len(missing_name_zh) == 0,
                "nodes": results
            }
            
            status = "✅" if verification[label]["is_complete"] else "❌"
            logger.info(f"  {status} {label}: {len(results)}/{len(node_def.nodes)} 节点")
            
            if verification[label]["missing_nodes"]:
                logger.warning(f"      缺失节点: {verification[label]['missing_nodes']}")
            if verification[label]["missing_name_zh"]:
                logger.warning(f"      缺失中文名: {verification[label]['missing_name_zh']}")
                
        return verification
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取节点类型统计信息
        
        Returns:
            统计信息
        """
        stats = {}
        
        for node_def in self.NODE_TYPES:
            label = node_def.label
            
            query = f"""
            MATCH (n:{label})
            RETURN count(n) as count
            """
            
            result = self.manager.execute_query(query, {})
            stats[label] = result[0]["count"] if result else 0
            
        return stats


def main():
    """主函数"""
    # 从环境变量获取Neo4j配置
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "build_body_2024")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    manager = None
    
    try:
        # 创建Neo4j管理器
        logger.info("连接Neo4j数据库...")
        manager = Neo4jManager(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            database=neo4j_database
        )
        logger.info("✅ 数据库连接成功")
        
        # 创建节点类型创建器
        creator = NodeTypeCreator(manager)
        
        # 创建所有节点类型
        creation_result = creator.create_all_node_types()
        
        # 验证创建结果
        verification = creator.verify_node_types()
        
        # 获取统计信息
        stats = creator.get_statistics()
        
        # 输出最终统计
        logger.info("\n" + "=" * 60)
        logger.info("最终统计:")
        logger.info("=" * 60)
        for label, count in stats.items():
            logger.info(f"  {label}: {count} 个节点")
            
        # 检查是否全部成功
        all_complete = all(v["is_complete"] for v in verification.values())
        
        if all_complete:
            logger.info("\n🎉 所有节点类型创建成功！")
            return 0
        else:
            logger.warning("\n⚠️ 部分节点类型创建不完整，请检查日志")
            return 1
            
    except Exception as e:
        logger.error(f"❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        # 断开连接
        if manager:
            manager.close()
        logger.info("数据库连接已关闭")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
