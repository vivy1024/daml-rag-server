# -*- coding: utf-8 -*-
"""
Neo4j数据层验证脚本

验证内容：
1. 节点类型完整性（ForceType, MechanicType, KineticChain, GripType, TrainingLevel）
2. 关系覆盖率（USES_FORCE, HAS_MECHANIC, HAS_KINETIC_CHAIN, USES_GRIP, SUITABLE_FOR_LEVEL）
3. 数据质量（双语属性、引用有效性）

版本: v1.0.0
日期: 2026-01-05
Requirements: 1.1-1.5, 2.1-2.6, 3.1-3.4
"""

import sys
import os
import logging
from typing import Dict, Any, List, Tuple
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
class ValidationResult:
    """验证结果"""
    name: str
    passed: bool
    message: str
    details: Dict[str, Any] = None


class Neo4jDataLayerValidator:
    """Neo4j数据层验证器"""
    
    # 预期的节点类型定义
    EXPECTED_NODE_TYPES = {
        "ForceType": ["push", "pull", "hold"],
        "MechanicType": ["compound", "isolation"],
        "KineticChain": ["open_chain", "closed_chain", "mixed"],
        "GripType": ["overhand", "underhand", "neutral", "mixed", "hook"],
        "TrainingLevel": ["novice", "beginner", "intermediate", "advanced"],
    }
    
    # 关系类型与Exercise属性的映射
    RELATIONSHIP_MAPPINGS = {
        "USES_FORCE": "force",
        "HAS_MECHANIC": "mechanic",
        "HAS_KINETIC_CHAIN": "kinetic_chain",
        "USES_GRIP": "grips",  # 数组属性
        "SUITABLE_FOR_LEVEL": "difficulty_level",
    }
    
    # 目标覆盖率
    TARGET_COVERAGE_RATE = 0.90  # 90%
    
    def __init__(self, neo4j_manager: Neo4jManager):
        """初始化验证器"""
        self.manager = neo4j_manager
        self.results: List[ValidationResult] = []
        
    def validate_all(self) -> Dict[str, Any]:
        """执行所有验证"""
        logger.info("=" * 70)
        logger.info("Neo4j数据层验证开始")
        logger.info("=" * 70)
        
        # 1. 验证节点类型
        self._validate_node_types()
        
        # 2. 验证双语属性
        self._validate_bilingual_properties()
        
        # 3. 验证关系覆盖率
        self._validate_relationship_coverage()
        
        # 4. 验证数据质量
        self._validate_data_quality()
        
        # 5. 汇总结果
        return self._summarize_results()
        
    def _validate_node_types(self):
        """验证节点类型完整性"""
        logger.info("\n" + "-" * 50)
        logger.info("1. 验证节点类型完整性")
        logger.info("-" * 50)
        
        for label, expected_names in self.EXPECTED_NODE_TYPES.items():
            query = f"""
            MATCH (n:{label})
            RETURN n.name as name, n.name_zh as name_zh
            ORDER BY n.name
            """
            
            results = self.manager.execute_query(query, {})
            actual_names = {r["name"] for r in results}
            expected_set = set(expected_names)
            
            missing = expected_set - actual_names
            extra = actual_names - expected_set
            
            if not missing and not extra:
                self.results.append(ValidationResult(
                    name=f"节点类型-{label}",
                    passed=True,
                    message=f"{label}: {len(results)}/{len(expected_names)} 节点完整",
                    details={"nodes": [r["name"] for r in results]}
                ))
                logger.info(f"  ✅ {label}: {len(results)}/{len(expected_names)} 节点完整")
            else:
                self.results.append(ValidationResult(
                    name=f"节点类型-{label}",
                    passed=False,
                    message=f"{label}: 缺失={missing}, 多余={extra}",
                    details={"missing": list(missing), "extra": list(extra)}
                ))
                logger.warning(f"  ❌ {label}: 缺失={missing}, 多余={extra}")
                
    def _validate_bilingual_properties(self):
        """验证双语属性完整性"""
        logger.info("\n" + "-" * 50)
        logger.info("2. 验证双语属性完整性")
        logger.info("-" * 50)
        
        for label in self.EXPECTED_NODE_TYPES.keys():
            query = f"""
            MATCH (n:{label})
            WHERE n.name_zh IS NULL OR n.name_zh = ''
            RETURN n.name as name
            """
            
            results = self.manager.execute_query(query, {})
            
            if not results:
                self.results.append(ValidationResult(
                    name=f"双语属性-{label}",
                    passed=True,
                    message=f"{label}: 所有节点都有中文名称"
                ))
                logger.info(f"  ✅ {label}: 所有节点都有中文名称")
            else:
                missing_zh = [r["name"] for r in results]
                self.results.append(ValidationResult(
                    name=f"双语属性-{label}",
                    passed=False,
                    message=f"{label}: {len(missing_zh)}个节点缺少中文名称",
                    details={"missing_name_zh": missing_zh}
                ))
                logger.warning(f"  ❌ {label}: {len(missing_zh)}个节点缺少中文名称: {missing_zh}")
                
    def _validate_relationship_coverage(self):
        """验证关系覆盖率"""
        logger.info("\n" + "-" * 50)
        logger.info("3. 验证关系覆盖率")
        logger.info("-" * 50)
        
        # 获取Exercise总数
        total_query = "MATCH (e:Exercise) RETURN count(e) as total"
        total_result = self.manager.execute_query(total_query, {})
        total_exercises = total_result[0]["total"] if total_result else 0
        
        logger.info(f"  Exercise总数: {total_exercises}")
        
        coverage_stats = {}
        
        for rel_type, attr_name in self.RELATIONSHIP_MAPPINGS.items():
            # 统计有该属性的Exercise数量
            if attr_name == "grips":
                # grips是数组属性
                attr_query = f"""
                MATCH (e:Exercise)
                WHERE e.{attr_name} IS NOT NULL AND size(e.{attr_name}) > 0
                RETURN count(e) as count
                """
            else:
                attr_query = f"""
                MATCH (e:Exercise)
                WHERE e.{attr_name} IS NOT NULL AND e.{attr_name} <> ''
                RETURN count(e) as count
                """
            attr_result = self.manager.execute_query(attr_query, {})
            exercises_with_attr = attr_result[0]["count"] if attr_result else 0
            
            # 统计已建立关系的Exercise数量
            rel_query = f"""
            MATCH (e:Exercise)-[:{rel_type}]->()
            RETURN count(DISTINCT e) as count
            """
            rel_result = self.manager.execute_query(rel_query, {})
            exercises_with_rel = rel_result[0]["count"] if rel_result else 0
            
            # 计算覆盖率
            if exercises_with_attr > 0:
                coverage_rate = exercises_with_rel / exercises_with_attr
            else:
                coverage_rate = 0.0
                
            coverage_stats[rel_type] = {
                "total_exercises": total_exercises,
                "exercises_with_attr": exercises_with_attr,
                "exercises_with_rel": exercises_with_rel,
                "coverage_rate": coverage_rate
            }
            
            passed = coverage_rate >= self.TARGET_COVERAGE_RATE
            
            self.results.append(ValidationResult(
                name=f"关系覆盖-{rel_type}",
                passed=passed,
                message=f"{rel_type}: {exercises_with_rel}/{exercises_with_attr} ({coverage_rate:.1%})",
                details=coverage_stats[rel_type]
            ))
            
            status = "✅" if passed else "⚠️"
            logger.info(f"  {status} {rel_type}: {exercises_with_rel}/{exercises_with_attr} ({coverage_rate:.1%})")
            
        # 计算总体覆盖率
        total_with_attr = sum(s["exercises_with_attr"] for s in coverage_stats.values())
        total_with_rel = sum(s["exercises_with_rel"] for s in coverage_stats.values())
        overall_rate = total_with_rel / total_with_attr if total_with_attr > 0 else 0.0
        
        logger.info(f"\n  总体关系覆盖率: {overall_rate:.1%} (目标: {self.TARGET_COVERAGE_RATE:.0%})")
        
        return coverage_stats
        
    def _validate_data_quality(self):
        """验证数据质量"""
        logger.info("\n" + "-" * 50)
        logger.info("4. 验证数据质量")
        logger.info("-" * 50)
        
        # 4.1 验证TrainingLevel命名统一性
        level_query = """
        MATCH (n:TrainingLevel)
        RETURN n.name as name, n.name_zh as name_zh
        ORDER BY n.name
        """
        levels = self.manager.execute_query(level_query, {})
        expected_levels = {"novice", "beginner", "intermediate", "advanced"}
        actual_levels = {l["name"] for l in levels}
        
        if actual_levels == expected_levels:
            self.results.append(ValidationResult(
                name="数据质量-TrainingLevel命名",
                passed=True,
                message="TrainingLevel命名统一"
            ))
            logger.info("  ✅ TrainingLevel命名统一")
        else:
            self.results.append(ValidationResult(
                name="数据质量-TrainingLevel命名",
                passed=False,
                message=f"TrainingLevel命名不统一: {actual_levels}",
                details={"expected": list(expected_levels), "actual": list(actual_levels)}
            ))
            logger.warning(f"  ❌ TrainingLevel命名不统一: {actual_levels}")
            
        # 4.2 验证InjuryType中文名称
        injury_query = """
        MATCH (n:InjuryType)
        WHERE n.name_zh IS NULL OR n.name_zh = ''
        RETURN n.name as name
        """
        injuries_missing_zh = self.manager.execute_query(injury_query, {})
        
        if not injuries_missing_zh:
            self.results.append(ValidationResult(
                name="数据质量-InjuryType中文名",
                passed=True,
                message="所有InjuryType都有中文名称"
            ))
            logger.info("  ✅ 所有InjuryType都有中文名称")
        else:
            missing = [i["name"] for i in injuries_missing_zh]
            self.results.append(ValidationResult(
                name="数据质量-InjuryType中文名",
                passed=False,
                message=f"{len(missing)}个InjuryType缺少中文名称",
                details={"missing": missing}
            ))
            logger.warning(f"  ⚠️ {len(missing)}个InjuryType缺少中文名称: {missing[:5]}...")
            
        # 4.3 验证Exercise引用有效性（检查孤立的Muscle引用）
        orphan_muscle_query = """
        MATCH (e:Exercise)
        WHERE e.target_muscles IS NOT NULL
        UNWIND e.target_muscles as muscle_name
        WITH muscle_name
        WHERE NOT EXISTS {
            MATCH (m:Muscle {name: muscle_name})
        } AND NOT EXISTS {
            MATCH (m:Muscle {name_zh: muscle_name})
        }
        RETURN DISTINCT muscle_name
        LIMIT 10
        """
        try:
            orphan_muscles = self.manager.execute_query(orphan_muscle_query, {})
            
            if not orphan_muscles:
                self.results.append(ValidationResult(
                    name="数据质量-Muscle引用",
                    passed=True,
                    message="所有Exercise的Muscle引用有效"
                ))
                logger.info("  ✅ 所有Exercise的Muscle引用有效")
            else:
                orphans = [m["muscle_name"] for m in orphan_muscles]
                self.results.append(ValidationResult(
                    name="数据质量-Muscle引用",
                    passed=False,
                    message=f"发现无效的Muscle引用",
                    details={"orphan_muscles": orphans}
                ))
                logger.warning(f"  ⚠️ 发现无效的Muscle引用: {orphans}")
        except Exception as e:
            logger.warning(f"  ⚠️ Muscle引用检查跳过: {str(e)}")
            
    def _summarize_results(self) -> Dict[str, Any]:
        """汇总验证结果"""
        logger.info("\n" + "=" * 70)
        logger.info("验证结果汇总")
        logger.info("=" * 70)
        
        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)
        
        # 按类别分组
        categories = {
            "节点类型": [],
            "双语属性": [],
            "关系覆盖": [],
            "数据质量": []
        }
        
        for result in self.results:
            for cat in categories.keys():
                if result.name.startswith(cat):
                    categories[cat].append(result)
                    break
                    
        # 输出各类别结果
        for cat_name, cat_results in categories.items():
            if cat_results:
                cat_passed = sum(1 for r in cat_results if r.passed)
                cat_total = len(cat_results)
                status = "✅" if cat_passed == cat_total else "⚠️"
                logger.info(f"\n{status} {cat_name}: {cat_passed}/{cat_total} 通过")
                for r in cat_results:
                    status = "  ✅" if r.passed else "  ❌"
                    logger.info(f"  {status} {r.message}")
                    
        # 总体结果
        all_passed = passed_count == total_count
        
        logger.info("\n" + "-" * 50)
        if all_passed:
            logger.info(f"🎉 所有验证通过！({passed_count}/{total_count})")
        else:
            logger.info(f"⚠️ 部分验证未通过 ({passed_count}/{total_count})")
        logger.info("-" * 50)
        
        return {
            "all_passed": all_passed,
            "passed_count": passed_count,
            "total_count": total_count,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ]
        }


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
        
        # 创建验证器并执行验证
        validator = Neo4jDataLayerValidator(manager)
        summary = validator.validate_all()
        
        # 返回退出码
        return 0 if summary["all_passed"] else 1
        
    except Exception as e:
        logger.error(f"❌ 验证失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        if manager:
            manager.close()
        logger.info("\n数据库连接已关闭")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
