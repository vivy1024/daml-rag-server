#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展INVOLVES_JOINT关系

功能：
- 从exercises_v2文件系统读取joints数据
- 创建Exercise→Joint的INVOLVES_JOINT关系
- 目标：从103个（5.8%）提升到1000+个（60%+）

优先级：P2
预期效果：更好的康复训练支持
"""

import os
import sys
import json
from pathlib import Path
from neo4j import GraphDatabase
from datetime import datetime

# Neo4j连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")

# 数据源路径（容器内绝对路径）
EXERCISES_V2_PATH = Path("/app/../yuzhen-backend/storage/app/public/exercises_v2")


class InvolvesJointExpander:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.stats = {
            "exercises_scanned": 0,
            "exercises_with_joints": 0,
            "involves_joint_created": 0,
            "involves_joint_skipped": 0,
            "errors": []
        }
        self.joint_mapping = {}  # joint_id -> joint_name
    
    def close(self):
        self.driver.close()
    
    def log(self, message):
        """打印日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def load_joint_mapping(self):
        """加载Joint节点映射"""
        self.log("\n📋 加载Joint节点映射...")
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (j:Joint)
                RETURN j.id as joint_id, j.name_zh as joint_name
            """)
            
            for record in result:
                self.joint_mapping[record["joint_id"]] = record["joint_name"]
            
            self.log(f"  ✅ 加载了 {len(self.joint_mapping)} 个Joint节点")
            self.log(f"  Joint列表: {list(self.joint_mapping.values())}")
    
    def scan_exercises_v2(self):
        """扫描exercises_v2文件系统"""
        self.log("\n🔍 扫描exercises_v2文件系统...")
        
        exercises_with_joints = []
        
        # 遍历所有data.json文件
        for data_file in EXERCISES_V2_PATH.rglob("data.json"):
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.stats["exercises_scanned"] += 1
                
                # 检查是否有joints字段且不为空
                if "joints" in data and data["joints"]:
                    exercises_with_joints.append({
                        "exercise_id": data["id"],
                        "name_zh": data.get("name_zh", ""),
                        "name_en": data.get("name_en", ""),
                        "joints": data["joints"]
                    })
                    self.stats["exercises_with_joints"] += 1
            
            except Exception as e:
                self.stats["errors"].append(f"读取文件 {data_file}: {e}")
        
        self.log(f"  ✅ 扫描了 {self.stats['exercises_scanned']} 个动作")
        self.log(f"  ✅ 找到 {self.stats['exercises_with_joints']} 个有joints数据的动作")
        
        return exercises_with_joints
    
    def create_involves_joint_relationships(self, exercises_with_joints):
        """创建INVOLVES_JOINT关系"""
        self.log("\n🔗 创建INVOLVES_JOINT关系...")
        
        with self.driver.session() as session:
            for exercise in exercises_with_joints:
                exercise_id = exercise["exercise_id"]
                joints = exercise["joints"]
                
                for joint_id in joints:
                    try:
                        # 检查关系是否已存在
                        check_result = session.run("""
                            MATCH (e:Exercise {id: $exercise_id})-[r:INVOLVES_JOINT]->(j:Joint {id: $joint_id})
                            RETURN count(r) as count
                        """, {"exercise_id": exercise_id, "joint_id": joint_id})
                        
                        if check_result.single()["count"] > 0:
                            self.stats["involves_joint_skipped"] += 1
                            continue
                        
                        # 创建新关系
                        result = session.run("""
                            MATCH (e:Exercise {id: $exercise_id})
                            MATCH (j:Joint {id: $joint_id})
                            MERGE (e)-[r:INVOLVES_JOINT]->(j)
                            RETURN e.name_zh as exercise_name, j.name_zh as joint_name
                        """, {"exercise_id": exercise_id, "joint_id": joint_id})
                        
                        record = result.single()
                        if record:
                            self.stats["involves_joint_created"] += 1
                            if self.stats["involves_joint_created"] <= 10:
                                self.log(f"    ✅ {record['exercise_name']} → {record['joint_name']}")
                    
                    except Exception as e:
                        self.stats["errors"].append(f"Exercise {exercise_id} -> Joint {joint_id}: {e}")
            
            if self.stats["involves_joint_created"] > 10:
                self.log(f"    ... 还有 {self.stats['involves_joint_created'] - 10} 个关系")
        
        self.log(f"  ✅ 成功创建 {self.stats['involves_joint_created']} 个新关系")
        self.log(f"  ⏭️  跳过 {self.stats['involves_joint_skipped']} 个已存在的关系")
    
    def verify_results(self):
        """验证结果"""
        self.log("\n📊 验证结果...")
        
        with self.driver.session() as session:
            # 检查INVOLVES_JOINT关系总数
            result = session.run("MATCH ()-[r:INVOLVES_JOINT]->() RETURN count(r) as count")
            total_count = result.single()["count"]
            self.log(f"  INVOLVES_JOINT关系总数: {total_count} 个")
            
            # 计算覆盖率
            result = session.run("MATCH (e:Exercise) RETURN count(e) as count")
            exercise_count = result.single()["count"]
            coverage = (total_count / exercise_count * 100) if exercise_count > 0 else 0
            self.log(f"  覆盖率: {coverage:.1f}% ({total_count}/{exercise_count})")
            
            # 按Joint统计
            result = session.run("""
                MATCH (j:Joint)<-[r:INVOLVES_JOINT]-(e:Exercise)
                RETURN j.name_zh as joint, count(e) as exercise_count
                ORDER BY exercise_count DESC
            """)
            
            self.log("\n  各关节涉及的动作数量:")
            for record in result:
                self.log(f"    {record['joint']}: {record['exercise_count']} 个动作")
            
            # 测试查询
            self.log("\n🔍 测试查询: 查找涉及膝关节的动作")
            result = session.run("""
                MATCH (e:Exercise)-[:INVOLVES_JOINT]->(j:Joint {name_zh: '膝关节'})
                RETURN e.name_zh as exercise
                LIMIT 5
            """)
            
            for record in result:
                self.log(f"    - {record['exercise']}")
    
    def print_summary(self):
        """打印总结"""
        self.log("\n" + "=" * 60)
        self.log("📊 执行总结")
        self.log("=" * 60)
        self.log(f"✅ 扫描动作: {self.stats['exercises_scanned']} 个")
        self.log(f"✅ 有joints数据: {self.stats['exercises_with_joints']} 个")
        self.log(f"✅ 新建关系: {self.stats['involves_joint_created']} 个")
        self.log(f"⏭️  跳过关系: {self.stats['involves_joint_skipped']} 个")
        
        if self.stats["errors"]:
            self.log(f"\n⚠️ 错误 ({len(self.stats['errors'])} 个):")
            for error in self.stats["errors"][:5]:
                self.log(f"  - {error}")
            if len(self.stats["errors"]) > 5:
                self.log(f"  ... 还有 {len(self.stats['errors']) - 5} 个错误")
    
    def run(self):
        """执行流程"""
        try:
            self.log("=" * 60)
            self.log("🚀 扩展INVOLVES_JOINT关系")
            self.log("=" * 60)
            
            # 1. 加载Joint节点映射
            self.load_joint_mapping()
            
            # 2. 扫描exercises_v2文件系统
            exercises_with_joints = self.scan_exercises_v2()
            
            # 3. 创建INVOLVES_JOINT关系
            self.create_involves_joint_relationships(exercises_with_joints)
            
            # 4. 验证结果
            self.verify_results()
            
            # 5. 打印总结
            self.print_summary()
            
            self.log("\n✅ 完成!")
        
        except Exception as e:
            self.log(f"\n❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.close()


if __name__ == "__main__":
    expander = InvolvesJointExpander()
    expander.run()
