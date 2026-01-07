#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建增强版CONTRAINDICATED_FOR关系

基于医学损伤专家、运动学教授和康复学专家的讨论
参考: docs/运动损伤禁忌症专家讨论.md

版本: v2.0.0
日期: 2025-12-15

使用说明:
    docker exec fitness_daml_rag python scripts/create_enhanced_contraindications.py [--phase 1|2|3|all] [--dry-run]

参数:
    --phase: 实施阶段 (1=核心损伤, 2=重要损伤, 3=补充损伤, all=全部)
    --dry-run: 预览模式
"""

import os
import argparse
from datetime import datetime
from typing import List, Dict
from neo4j import GraphDatabase

# 导入增强规则
from enhanced_contraindication_rules import (
    PHASE1_CONTRAINDICATION_RULES,
    PHASE2_CONTRAINDICATION_RULES,
    PHASE3_CONTRAINDICATION_RULES,
    SPECIAL_POPULATION_RULES,
    ALL_CONTRAINDICATION_RULES,
    RULES_STATS
)

os.environ['NO_PROXY'] = 'localhost,127.0.0.1,fitness_neo4j'


class EnhancedContraindicationCreator:
    """增强版禁忌关系创建器"""

    def __init__(
        self,
        uri: str = "bolt://fitness_neo4j:7687",
        user: str = "neo4j",
        password: str = "build_body_2024"
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.dry_run = False
        self.stats = {
            "created_by_injury": {},
            "created_by_severity": {"absolute": 0, "relative": 0, "caution": 0},
            "total_created": 0,
            "errors": []
        }

    def close(self):
        self.driver.close()

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def set_dry_run(self, enabled: bool = True):
        self.dry_run = enabled
        if enabled:
            self.log("🔍 [DRY-RUN MODE] 预览模式", "WARN")

    def check_injury_types(self):
        """检查数据库中的InjuryType节点"""
        self.log("\n📊 检查InjuryType节点...")
        
        with self.driver.session() as session:
            result = session.run("MATCH (i:InjuryType) RETURN i.name as name ORDER BY name")
            existing = [r["name"] for r in result]
            self.log(f"  现有InjuryType: {len(existing)} 个")
            for name in existing:
                self.log(f"    - {name}")
            return existing

    def create_missing_injury_types(self, rules: Dict):
        """创建缺失的InjuryType节点"""
        self.log("\n🔧 检查并创建缺失的InjuryType节点...")
        
        existing = self.check_injury_types()
        missing = [name for name in rules.keys() if name not in existing]
        
        if not missing:
            self.log("  ✅ 所有InjuryType节点已存在")
            return
        
        self.log(f"  需要创建 {len(missing)} 个新节点:")
        for name in missing:
            self.log(f"    - {name}")
        
        if self.dry_run:
            self.log("  [DRY-RUN] 跳过创建")
            return
        
        with self.driver.session() as session:
            for name in missing:
                query = """
                CREATE (i:InjuryType {
                    name: $name,
                    created_at: datetime(),
                    source: 'expert_discussion_v2'
                })
                """
                session.run(query, {"name": name})
                self.log(f"  ✅ 创建: {name}")

    def create_contraindications(
        self,
        injury_name: str,
        rules: Dict
    ) -> int:
        """为特定损伤创建禁忌关系"""
        
        self.log(f"\n🔗 处理 {injury_name}...")
        self.log(f"  严重程度: {rules.get('severity', 'relative')}")
        self.log(f"  规则: {rules['description']}")
        
        # 构建查询条件
        where_clauses = []
        
        # 关键词匹配
        if rules.get("keywords_zh"):
            kw_conditions = [f"e.name_zh CONTAINS '{kw}'" for kw in rules["keywords_zh"]]
            where_clauses.append(f"({' OR '.join(kw_conditions)})")
        
        if rules.get("keywords_en"):
            kw_conditions = [f"toLower(e.name_en) CONTAINS '{kw.lower()}'" for kw in rules["keywords_en"]]
            where_clauses.append(f"({' OR '.join(kw_conditions)})")
        
        # 主要肌群匹配
        if rules.get("primary_muscles"):
            muscle_conditions = [f"e.primary_muscle_zh = '{m}'" for m in rules["primary_muscles"]]
            where_clauses.append(f"({' OR '.join(muscle_conditions)})")
        
        if not where_clauses:
            self.log("  ⚠️  没有匹配条件，跳过")
            return 0
        
        where_clause = " OR ".join(where_clauses)
        
        # 构建创建关系的查询
        severity = rules.get('severity', 'relative')
        query = f"""
        MATCH (e:Exercise)
        WHERE {where_clause}
        WITH e
        MATCH (i:InjuryType {{name: $injury_name}})
        MERGE (e)-[r:CONTRAINDICATED_FOR]->(i)
        ON CREATE SET 
            r.severity = $severity,
            r.reason = $reason,
            r.created_at = datetime(),
            r.source = 'expert_discussion_v2'
        RETURN e.name_zh as exercise
        """
        
        if self.dry_run:
            # 预览模式
            preview_query = f"""
            MATCH (e:Exercise)
            WHERE {where_clause}
            RETURN e.name_zh as exercise, e.primary_muscle_zh as muscle
            LIMIT 10
            """
            
            with self.driver.session() as session:
                results = list(session.run(preview_query))
                
                if results:
                    self.log(f"  预览前{min(10, len(results))}个匹配:")
                    for i, r in enumerate(results, 1):
                        self.log(f"    {i}. {r['exercise']} ({r['muscle']})")
                
                # 统计总数
                count_query = f"""
                MATCH (e:Exercise)
                WHERE {where_clause}
                RETURN count(e) as total
                """
                result = session.run(count_query)
                total = result.single()["total"]
                self.log(f"  预计创建: {total} 个关系 (严重程度: {severity})")
                
                self.stats["created_by_injury"][injury_name] = total
                self.stats["created_by_severity"][severity] += total
                return total
        else:
            # 实际执行
            with self.driver.session() as session:
                results = list(session.run(query, {
                    "injury_name": injury_name,
                    "severity": severity,
                    "reason": rules['description']
                }))
                created = len(results)
                
                self.log(f"  ✅ 成功创建 {created} 个关系 (严重程度: {severity})")
                
                self.stats["created_by_injury"][injury_name] = created
                self.stats["created_by_severity"][severity] += created
                return created

    def create_all_contraindications(self, rules: Dict):
        """创建所有禁忌关系"""
        self.log("\n🔗 开始创建CONTRAINDICATED_FOR关系...")
        
        total = 0
        for injury_name, injury_rules in rules.items():
            try:
                created = self.create_contraindications(injury_name, injury_rules)
                total += created
            except Exception as e:
                self.log(f"❌ 处理 {injury_name} 失败: {e}", "ERROR")
                self.stats["errors"].append(f"{injury_name}: {str(e)}")
        
        self.stats["total_created"] = total
        return total

    def verify_results(self):
        """验证结果"""
        self.log("\n📊 验证创建结果...")
        
        with self.driver.session() as session:
            # 总数
            result = session.run("MATCH ()-[r:CONTRAINDICATED_FOR]->() RETURN count(r) as count")
            count = result.single()["count"]
            self.log(f"  CONTRAINDICATED_FOR总数: {count} 个")
            
            # 按损伤类型统计
            result = session.run("""
                MATCH (e:Exercise)-[r:CONTRAINDICATED_FOR]->(i:InjuryType)
                RETURN i.name as injury, count(e) as count, collect(DISTINCT r.severity)[0] as severity
                ORDER BY count DESC
            """)
            self.log("\n  按损伤类型统计:")
            for r in result:
                severity_icon = {"absolute": "🚫", "relative": "⚠️", "caution": "💡"}.get(r.get('severity'), "")
                self.log(f"    {severity_icon} {r['injury']}: {r['count']} 个")
            
            # 按严重程度统计
            result = session.run("""
                MATCH ()-[r:CONTRAINDICATED_FOR]->()
                RETURN r.severity as severity, count(r) as count
                ORDER BY count DESC
            """)
            self.log("\n  按严重程度统计:")
            for r in result:
                self.log(f"    {r['severity']}: {r['count']} 个")

    def print_summary(self):
        """打印摘要"""
        self.log("\n" + "=" * 60)
        self.log("📋 创建禁忌关系摘要")
        self.log("=" * 60)
        self.log(f"✅ 总计创建: {self.stats['total_created']} 个关系")
        
        self.log("\n按损伤类型:")
        for injury, count in sorted(self.stats["created_by_injury"].items(), key=lambda x: x[1], reverse=True):
            self.log(f"  {injury}: {count} 个")
        
        self.log("\n按严重程度:")
        for severity, count in self.stats["created_by_severity"].items():
            icon = {"absolute": "🚫", "relative": "⚠️", "caution": "💡"}.get(severity, "")
            self.log(f"  {icon} {severity}: {count} 个")
        
        if self.stats["errors"]:
            self.log(f"\n❌ 错误: {len(self.stats['errors'])} 个")
        
        self.log("=" * 60)
        
        if self.dry_run:
            self.log("\n🔍 [DRY-RUN] 预览模式")
        else:
            self.log("\n✅ 创建完成！")

    def run(self, phase: str = "1"):
        """执行流程"""
        self.log("=" * 60)
        self.log(f"🚀 创建增强版CONTRAINDICATED_FOR关系 (Phase {phase})")
        self.log("=" * 60)
        
        # 选择规则
        if phase == "1":
            rules = PHASE1_CONTRAINDICATION_RULES
            self.log(f"📌 Phase 1: 核心损伤类型 ({len(rules)} 个)")
        elif phase == "2":
            rules = PHASE2_CONTRAINDICATION_RULES
            self.log(f"📌 Phase 2: 重要损伤类型 ({len(rules)} 个)")
        elif phase == "3":
            rules = PHASE3_CONTRAINDICATION_RULES
            self.log(f"📌 Phase 3: 补充损伤类型 ({len(rules)} 个)")
        elif phase == "all":
            rules = ALL_CONTRAINDICATION_RULES
            self.log(f"📌 All Phases: 全部损伤类型 ({len(rules)} 个)")
        else:
            self.log(f"❌ 无效的phase参数: {phase}", "ERROR")
            return
        
        try:
            # 1. 创建缺失的InjuryType节点
            self.create_missing_injury_types(rules)
            
            # 2. 创建禁忌关系
            self.create_all_contraindications(rules)
            
            # 3. 验证结果
            if not self.dry_run:
                self.verify_results()
            
            # 4. 打印摘要
            self.print_summary()
            
        except Exception as e:
            self.log(f"❌ 执行失败: {e}", "ERROR")
            import traceback
            traceback.print_exc()
        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(description="创建增强版CONTRAINDICATED_FOR关系")
    parser.add_argument(
        "--phase",
        choices=["1", "2", "3", "all"],
        default="1",
        help="实施阶段 (1=核心, 2=重要, 3=补充, all=全部)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式"
    )
    
    args = parser.parse_args()
    
    creator = EnhancedContraindicationCreator()
    
    if args.dry_run:
        creator.set_dry_run(enabled=True)
    
    creator.run(phase=args.phase)


if __name__ == "__main__":
    main()
