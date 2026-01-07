#!/usr/bin/env python3
"""
在Neo4j中创建用户档案节点

定义UserProfile节点类型，并创建示例用户节点。

Author: 薛小川
Created: 2025-11-19
"""

import sys
import os
from pathlib import Path
from neo4j import GraphDatabase

# 禁用代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class UserProfileNodeCreator:
    """用户档案节点创建器"""
    
    def __init__(
        self,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "your_password"
    ):
        """初始化"""
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        print(f"✅ 连接到Neo4j: {neo4j_uri}")
    
    def close(self):
        """关闭连接"""
        self.driver.close()
    
    def create_user_profile_schema(self):
        """创建用户档案Schema"""
        print("\n🔧 创建用户档案Schema...")
        
        with self.driver.session() as session:
            # 创建唯一性约束
            try:
                session.run("""
                    CREATE CONSTRAINT user_profile_id IF NOT EXISTS
                    FOR (u:UserProfile) REQUIRE u.user_id IS UNIQUE
                """)
                print("✅ 创建唯一性约束: user_id")
            except Exception as e:
                print(f"⚠️  约束已存在或创建失败: {e}")
            
            # 创建索引
            try:
                session.run("""
                    CREATE INDEX user_profile_training_level IF NOT EXISTS
                    FOR (u:UserProfile) ON (u.training_level)
                """)
                print("✅ 创建索引: training_level")
            except Exception as e:
                print(f"⚠️  索引已存在或创建失败: {e}")
    
    def create_example_users(self):
        """创建示例用户节点"""
        print("\n📥 创建示例用户...")
        
        example_users = [
            {
                'user_id': 'user_beginner_001',
                'age': 22,
                'gender': 'male',
                'weight': 70.0,
                'height': 175.0,
                'training_experience_months': 3,
                'squat_1rm': 60.0,
                'bench_1rm': 50.0,
                'deadlift_1rm': 80.0,
                'primary_goal': 'gain_muscle',
                'training_level': 'beginner',
                'injuries': [],
                'health_conditions': [],
                'sleep_hours': 7.0,
                'stress_level': 'low'
            },
            {
                'user_id': 'user_intermediate_001',
                'age': 28,
                'gender': 'male',
                'weight': 80.0,
                'height': 180.0,
                'training_experience_months': 18,
                'squat_1rm': 140.0,
                'bench_1rm': 100.0,
                'deadlift_1rm': 160.0,
                'primary_goal': 'gain_muscle',
                'training_level': 'intermediate',
                'injuries': [],
                'health_conditions': [],
                'sleep_hours': 7.5,
                'stress_level': 'medium'
            },
            {
                'user_id': 'user_advanced_001',
                'age': 32,
                'gender': 'male',
                'weight': 85.0,
                'height': 178.0,
                'training_experience_months': 48,
                'squat_1rm': 180.0,
                'bench_1rm': 130.0,
                'deadlift_1rm': 200.0,
                'primary_goal': 'gain_strength',
                'training_level': 'advanced',
                'injuries': [],
                'health_conditions': [],
                'sleep_hours': 8.0,
                'stress_level': 'low'
            },
            {
                'user_id': 'user_with_injury_001',
                'age': 35,
                'gender': 'male',
                'weight': 78.0,
                'height': 176.0,
                'training_experience_months': 24,
                'squat_1rm': 100.0,
                'bench_1rm': 85.0,
                'deadlift_1rm': 120.0,
                'primary_goal': 'maintain',
                'training_level': 'intermediate',
                'injuries': ['knee_injury'],
                'health_conditions': [],
                'sleep_hours': 6.5,
                'stress_level': 'high'
            },
            {
                'user_id': 'user_female_001',
                'age': 26,
                'gender': 'female',
                'weight': 58.0,
                'height': 165.0,
                'training_experience_months': 12,
                'squat_1rm': 60.0,
                'bench_1rm': 35.0,
                'deadlift_1rm': 80.0,
                'primary_goal': 'lose_fat',
                'training_level': 'novice',
                'injuries': [],
                'health_conditions': [],
                'sleep_hours': 7.0,
                'stress_level': 'medium'
            }
        ]
        
        with self.driver.session() as session:
            for user in example_users:
                cypher = """
                MERGE (u:UserProfile {user_id: $user_id})
                SET u.age = $age,
                    u.gender = $gender,
                    u.weight = $weight,
                    u.height = $height,
                    u.training_experience_months = $training_experience_months,
                    u.squat_1rm = $squat_1rm,
                    u.bench_1rm = $bench_1rm,
                    u.deadlift_1rm = $deadlift_1rm,
                    u.primary_goal = $primary_goal,
                    u.training_level = $training_level,
                    u.injuries = $injuries,
                    u.health_conditions = $health_conditions,
                    u.sleep_hours = $sleep_hours,
                    u.stress_level = $stress_level,
                    u.created_at = datetime(),
                    u.updated_at = datetime()
                """
                
                session.run(cypher, user)
                print(f"  ✅ 创建用户: {user['user_id']} ({user['training_level']})")
        
        print(f"\n✅ 创建示例用户: {len(example_users)} 个")
    
    def create_user_relationships(self):
        """创建用户与训练知识的关系"""
        print("\n🔗 创建用户关系...")
        
        with self.driver.session() as session:
            # 为每个用户创建与训练等级的关系
            cypher = """
            MATCH (u:UserProfile)
            MATCH (l:TrainingLevel {id: u.training_level})
            MERGE (u)-[:HAS_TRAINING_LEVEL {created_at: datetime()}]->(l)
            """
            result = session.run(cypher)
            print(f"  ✅ 创建用户-训练等级关系")
            
            # 为每个用户创建与训练目标的关系
            cypher = """
            MATCH (u:UserProfile)
            MATCH (g:TrainingGoal {id: u.primary_goal})
            MERGE (u)-[:HAS_TRAINING_GOAL {created_at: datetime()}]->(g)
            """
            result = session.run(cypher)
            print(f"  ✅ 创建用户-训练目标关系")
            
            # 为每个用户推荐周期化模型
            cypher = """
            MATCH (u:UserProfile)
            MATCH (l:TrainingLevel {id: u.training_level})
            MATCH (m:PeriodizationModel)-[r:SUITABLE_FOR_LEVEL]->(l)
            WHERE r.priority = 1
            MERGE (u)-[:RECOMMENDED_MODEL {
                created_at: datetime(),
                reason: r.reason
            }]->(m)
            """
            result = session.run(cypher)
            print(f"  ✅ 创建用户-推荐模型关系")
    
    def verify_users(self):
        """验证用户节点"""
        print("\n📊 验证用户节点...")
        
        with self.driver.session() as session:
            # 统计用户数
            result = session.run("MATCH (u:UserProfile) RETURN count(u) as count")
            count = result.single()["count"]
            print(f"  用户总数: {count}")
            
            # 按训练等级统计
            result = session.run("""
                MATCH (u:UserProfile)
                RETURN u.training_level as level, count(u) as count
                ORDER BY level
            """)
            print(f"\n  按训练等级统计:")
            for record in result:
                print(f"    {record['level']}: {record['count']}")
            
            # 测试查询：查找初学者用户的推荐模型
            print(f"\n🔍 测试查询: 初学者用户的推荐模型")
            result = session.run("""
                MATCH (u:UserProfile {training_level: 'beginner'})
                MATCH (u)-[r:RECOMMENDED_MODEL]->(m:PeriodizationModel)
                RETURN u.user_id as user_id,
                       m.name as model,
                       r.reason as reason
                LIMIT 3
            """)
            
            for record in result:
                print(f"  用户: {record['user_id']}")
                print(f"  推荐模型: {record['model']}")
                print(f"  原因: {record['reason']}\n")
    
    def run(self):
        """执行完整流程"""
        print("=" * 60)
        print("🚀 创建用户档案节点")
        print("=" * 60)
        
        try:
            # 1. 创建Schema
            self.create_user_profile_schema()
            
            # 2. 创建示例用户
            self.create_example_users()
            
            # 3. 创建关系
            self.create_user_relationships()
            
            # 4. 验证
            self.verify_users()
            
            print("\n" + "=" * 60)
            print("✅ 用户档案节点创建完成！")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ 创建失败: {e}")
            raise
        finally:
            self.close()


def main():
    """主函数"""
    creator = UserProfileNodeCreator(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="your_password"  # 请修改为实际密码
    )
    creator.run()


if __name__ == "__main__":
    main()
