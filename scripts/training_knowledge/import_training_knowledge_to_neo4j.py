#!/usr/bin/env python3
"""
导入训练知识到Neo4j图数据库

读取training_knowledge JSON文件，创建节点和关系，导入Neo4j。

Author: 薛小川
Created: 2025-11-19
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from neo4j import GraphDatabase

# 禁用代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TrainingKnowledgeNeo4jImporter:
    """训练知识Neo4j导入器"""
    
    def __init__(
        self,
        knowledge_dir: str,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "your_password"
    ):
        """
        初始化
        
        Args:
            knowledge_dir: 训练知识目录
            neo4j_uri: Neo4j连接URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
        """
        self.knowledge_dir = Path(knowledge_dir)
        
        # 连接Neo4j
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        print(f"✅ 连接到Neo4j: {neo4j_uri}")
    
    def close(self):
        """关闭连接"""
        self.driver.close()
    
    def load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """加载JSON文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def clear_database(self):
        """清空数据库（可选）"""
        with self.driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as count")
            count = result.single()["count"]
            
            if count > 0:
                print(f"⚠️  数据库中已有 {count} 个节点")
                response = input("是否清空数据库？(y/n): ")
                if response.lower() == 'y':
                    session.run("MATCH (n) DETACH DELETE n")
                    print("✅ 数据库已清空")
                else:
                    print("⚠️  跳过清空数据库")
    
    def create_constraints_and_indexes(self):
        """创建约束和索引"""
        print("\n🔧 创建约束和索引...")
        
        constraints = [
            "CREATE CONSTRAINT periodization_model_id IF NOT EXISTS FOR (m:PeriodizationModel) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT training_phase_id IF NOT EXISTS FOR (p:TrainingPhase) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT training_level_id IF NOT EXISTS FOR (l:TrainingLevel) REQUIRE l.id IS UNIQUE",
            "CREATE CONSTRAINT muscle_group_id IF NOT EXISTS FOR (m:MuscleGroup) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT training_goal_id IF NOT EXISTS FOR (g:TrainingGoal) REQUIRE g.id IS UNIQUE",
            "CREATE CONSTRAINT injury_type_id IF NOT EXISTS FOR (i:InjuryType) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT guideline_id IF NOT EXISTS FOR (g:Guideline) REQUIRE g.id IS UNIQUE"
        ]
        
        indexes = [
            "CREATE INDEX periodization_model_name IF NOT EXISTS FOR (m:PeriodizationModel) ON (m.name)",
            "CREATE INDEX training_level_name IF NOT EXISTS FOR (l:TrainingLevel) ON (l.name)"
        ]
        
        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    print(f"⚠️  约束创建警告: {e}")
            
            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    print(f"⚠️  索引创建警告: {e}")
        
        print(f"✅ 创建约束: {len(constraints)} 个")
        print(f"✅ 创建索引: {len(indexes)} 个")
    
    def import_periodization_models(self):
        """导入周期化模型"""
        print("\n📥 导入周期化模型...")
        
        file_path = self.knowledge_dir / "periodization-models.json"
        if not file_path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            return
        
        data = self.load_json_file(file_path)
        models = data.get('periodization_models', {})
        
        with self.driver.session() as session:
            for model_id, model_data in models.items():
                # 创建周期化模型节点
                cypher = """
                CREATE (m:PeriodizationModel {
                    id: $id,
                    name: $name,
                    name_en: $name_en,
                    description: $description,
                    duration: $duration,
                    suitable_for: $suitable_for,
                    advantages: $advantages,
                    disadvantages: $disadvantages,
                    source: $source,
                    created_at: datetime()
                })
                """
                
                session.run(cypher, {
                    'id': model_id,
                    'name': model_data.get('name', ''),
                    'name_en': model_data.get('aka', [''])[0] if model_data.get('aka') else '',
                    'description': model_data.get('description', ''),
                    'duration': model_data.get('duration', ''),
                    'suitable_for': model_data.get('best_for', []),
                    'advantages': model_data.get('advantages', []),
                    'disadvantages': model_data.get('disadvantages', []),
                    'source': 'periodization-models.json'
                })
                
                # 创建训练阶段节点和关系
                for order, phase in enumerate(model_data.get('phases', []), 1):
                    phase_id = f"{model_id}_phase_{order}"
                    
                    phase_cypher = """
                    CREATE (p:TrainingPhase {
                        id: $id,
                        name: $name,
                        name_en: $name_en,
                        duration: $duration,
                        intensity: $intensity,
                        reps: $reps,
                        sets: $sets,
                        rest: $rest,
                        goal: $goal,
                        order: $order,
                        created_at: datetime()
                    })
                    """
                    
                    session.run(phase_cypher, {
                        'id': phase_id,
                        'name': phase.get('phase', ''),
                        'name_en': phase.get('phase', ''),
                        'duration': phase.get('weeks', ''),
                        'intensity': phase.get('intensity', ''),
                        'reps': str(phase.get('reps', '')),
                        'sets': str(phase.get('sets', '')),
                        'rest': phase.get('rest', ''),
                        'goal': phase.get('goal', ''),
                        'order': order
                    })
                    
                    # 创建HAS_PHASE关系
                    rel_cypher = """
                    MATCH (m:PeriodizationModel {id: $model_id})
                    MATCH (p:TrainingPhase {id: $phase_id})
                    CREATE (m)-[:HAS_PHASE {order: $order, created_at: datetime()}]->(p)
                    """
                    
                    session.run(rel_cypher, {
                        'model_id': model_id,
                        'phase_id': phase_id,
                        'order': order
                    })
        
        print(f"✅ 导入周期化模型: {len(models)} 个")
    
    def import_training_levels(self):
        """导入训练等级"""
        print("\n📥 导入训练等级...")
        
        # 定义训练等级
        levels = [
            {
                'id': 'beginner',
                'name': '初学者',
                'name_en': 'Beginner',
                'training_months': '0-6',
                'description': '需要学习基础动作模式',
                'characteristics': ['学习基础动作', '建立神经肌肉连接', '快速进步期']
            },
            {
                'id': 'novice',
                'name': '新手',
                'name_en': 'Novice',
                'training_months': '6-12',
                'description': '掌握基础动作，开始系统训练',
                'characteristics': ['动作模式稳定', '可以承受中等强度', '线性进步']
            },
            {
                'id': 'intermediate',
                'name': '中级',
                'name_en': 'Intermediate',
                'training_months': '12-24',
                'description': '需要周期化训练',
                'characteristics': ['力量基础扎实', '需要变化刺激', '波动式进步']
            },
            {
                'id': 'advanced',
                'name': '高级',
                'name_en': 'Advanced',
                'training_months': '24-60',
                'description': '需要精细化训练计划',
                'characteristics': ['接近遗传潜力', '需要高级技术', '缓慢进步']
            },
            {
                'id': 'elite',
                'name': '精英',
                'name_en': 'Elite',
                'training_months': '60+',
                'description': '竞技水平',
                'characteristics': ['达到遗传潜力', '专项化训练', '微小进步']
            }
        ]
        
        with self.driver.session() as session:
            for level in levels:
                cypher = """
                CREATE (l:TrainingLevel {
                    id: $id,
                    name: $name,
                    name_en: $name_en,
                    training_months: $training_months,
                    description: $description,
                    characteristics: $characteristics,
                    created_at: datetime()
                })
                """
                
                session.run(cypher, level)
            
            # 创建进阶关系
            progressions = [
                ('beginner', 'novice', 6),
                ('novice', 'intermediate', 12),
                ('intermediate', 'advanced', 24),
                ('advanced', 'elite', 36)
            ]
            
            for from_level, to_level, months in progressions:
                rel_cypher = """
                MATCH (l1:TrainingLevel {id: $from_level})
                MATCH (l2:TrainingLevel {id: $to_level})
                CREATE (l1)-[:PROGRESSES_TO {
                    typical_duration_months: $months,
                    requirements: ['掌握当前等级技能', '力量达标'],
                    created_at: datetime()
                }]->(l2)
                """
                
                session.run(rel_cypher, {
                    'from_level': from_level,
                    'to_level': to_level,
                    'months': months
                })
        
        print(f"✅ 导入训练等级: {len(levels)} 个")
        print(f"✅ 创建进阶关系: {len(progressions)} 个")
    
    def import_muscle_groups(self):
        """导入肌群"""
        print("\n📥 导入肌群...")
        
        file_path = self.knowledge_dir / "training-volume-landmarks.json"
        if not file_path.exists():
            print(f"⚠️  文件不存在: {file_path}")
            return
        
        data = self.load_json_file(file_path)
        volume_landmarks = data.get('volume_landmarks', {})
        
        count = 0
        with self.driver.session() as session:
            for muscle_id, muscle_data in volume_landmarks.items():
                # 只处理有MV字段且为dict的肌群
                if isinstance(muscle_data.get('MV'), dict):
                    cypher = """
                    CREATE (m:MuscleGroup {
                        id: $id,
                        name: $name,
                        name_en: $name_en,
                        mv: $mv,
                        mev: $mev,
                        mav: $mav,
                        mrv: $mrv,
                        optimal_frequency: $optimal_frequency,
                        created_at: datetime()
                    })
                    """
                    
                    session.run(cypher, {
                        'id': muscle_id,
                        'name': muscle_id.replace('_', ' ').title(),
                        'name_en': muscle_id.title(),
                        'mv': muscle_data['MV'].get('sets_per_week', ''),
                        'mev': muscle_data['MEV'].get('sets_per_week', ''),
                        'mav': muscle_data['MAV'].get('sets_per_week', ''),
                        'mrv': muscle_data['MRV'].get('sets_per_week', ''),
                        'optimal_frequency': muscle_data.get('optimal_frequency', '')
                    })
                    count += 1
        
        print(f"✅ 导入肌群: {count} 个")
    
    def import_training_goals(self):
        """导入训练目标"""
        print("\n📥 导入训练目标...")
        
        goals = [
            {
                'id': 'gain_muscle',
                'name': '增肌',
                'name_en': 'Gain Muscle',
                'description': '增加肌肉质量',
                'calorie_adjustment': 400,
                'protein_per_kg': 2.0,
                'fat_per_kg': 1.0
            },
            {
                'id': 'lose_fat',
                'name': '减脂',
                'name_en': 'Lose Fat',
                'description': '减少体脂率',
                'calorie_adjustment': -500,
                'protein_per_kg': 2.2,
                'fat_per_kg': 0.8
            },
            {
                'id': 'gain_strength',
                'name': '增力',
                'name_en': 'Gain Strength',
                'description': '提高最大力量',
                'calorie_adjustment': 200,
                'protein_per_kg': 1.8,
                'fat_per_kg': 1.0
            },
            {
                'id': 'maintain',
                'name': '维持',
                'name_en': 'Maintain',
                'description': '维持当前状态',
                'calorie_adjustment': 0,
                'protein_per_kg': 1.6,
                'fat_per_kg': 0.8
            }
        ]
        
        with self.driver.session() as session:
            for goal in goals:
                cypher = """
                CREATE (g:TrainingGoal {
                    id: $id,
                    name: $name,
                    name_en: $name_en,
                    description: $description,
                    calorie_adjustment: $calorie_adjustment,
                    protein_per_kg: $protein_per_kg,
                    fat_per_kg: $fat_per_kg,
                    created_at: datetime()
                })
                """
                
                session.run(cypher, goal)
        
        print(f"✅ 导入训练目标: {len(goals)} 个")
    
    def create_model_level_relationships(self):
        """创建周期化模型和训练等级的关系"""
        print("\n🔗 创建模型-等级关系...")
        
        # 定义推荐关系
        relationships = [
            ('linear_periodization', 'beginner', 1, '简单、结构化、适合建立基础'),
            ('linear_periodization', 'novice', 2, '适合力量快速增长期'),
            ('undulating_periodization', 'intermediate', 1, '提供变化刺激，避免适应'),
            ('undulating_periodization', 'advanced', 2, '适合需要多样化的训练者'),
            ('block_periodization', 'advanced', 1, '专项化训练，适合竞技准备'),
            ('conjugate_periodization', 'advanced', 1, '同时发展多种素质'),
            ('reverse_linear_periodization', 'intermediate', 2, '适合耐力和肌肥大目标')
        ]
        
        with self.driver.session() as session:
            for model_id, level_id, priority, reason in relationships:
                cypher = """
                MATCH (m:PeriodizationModel {id: $model_id})
                MATCH (l:TrainingLevel {id: $level_id})
                CREATE (m)-[:SUITABLE_FOR_LEVEL {
                    priority: $priority,
                    reason: $reason,
                    created_at: datetime()
                }]->(l)
                """
                
                session.run(cypher, {
                    'model_id': model_id,
                    'level_id': level_id,
                    'priority': priority,
                    'reason': reason
                })
        
        print(f"✅ 创建模型-等级关系: {len(relationships)} 个")
    
    def create_model_goal_relationships(self):
        """创建周期化模型和训练目标的关系"""
        print("\n🔗 创建模型-目标关系...")
        
        relationships = [
            ('linear_periodization', 'gain_strength', 9, '优先力量峰值期'),
            ('linear_periodization', 'gain_muscle', 8, '包含完整肥大期'),
            ('undulating_periodization', 'gain_muscle', 9, '持续肥大刺激'),
            ('undulating_periodization', 'maintain', 7, '提供训练变化'),
            ('block_periodization', 'gain_strength', 10, '专项力量发展'),
            ('conjugate_periodization', 'gain_strength', 9, '多角度力量发展'),
            ('reverse_linear_periodization', 'lose_fat', 8, '高容量消耗热量')
        ]
        
        with self.driver.session() as session:
            for model_id, goal_id, effectiveness, notes in relationships:
                cypher = """
                MATCH (m:PeriodizationModel {id: $model_id})
                MATCH (g:TrainingGoal {id: $goal_id})
                CREATE (m)-[:RECOMMENDED_FOR_GOAL {
                    effectiveness: $effectiveness,
                    notes: $notes,
                    created_at: datetime()
                }]->(g)
                """
                
                session.run(cypher, {
                    'model_id': model_id,
                    'goal_id': goal_id,
                    'effectiveness': effectiveness,
                    'notes': notes
                })
        
        print(f"✅ 创建模型-目标关系: {len(relationships)} 个")
    
    def verify_import(self):
        """验证导入结果"""
        print("\n📊 验证导入结果...")
        
        with self.driver.session() as session:
            # 统计节点数
            node_counts = {}
            labels = ['PeriodizationModel', 'TrainingPhase', 'TrainingLevel', 
                     'MuscleGroup', 'TrainingGoal']
            
            for label in labels:
                result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
                node_counts[label] = result.single()["count"]
            
            # 统计关系数
            rel_counts = {}
            rel_types = ['HAS_PHASE', 'SUITABLE_FOR_LEVEL', 'RECOMMENDED_FOR_GOAL', 
                        'PROGRESSES_TO']
            
            for rel_type in rel_types:
                result = session.run(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count")
                rel_counts[rel_type] = result.single()["count"]
            
            print("\n节点统计:")
            for label, count in node_counts.items():
                print(f"  - {label}: {count}")
            
            print("\n关系统计:")
            for rel_type, count in rel_counts.items():
                print(f"  - {rel_type}: {count}")
            
            # 测试查询
            print("\n🔍 测试查询: 为初学者推荐周期化模型")
            result = session.run("""
                MATCH (m:PeriodizationModel)-[r:SUITABLE_FOR_LEVEL]->(l:TrainingLevel {id: 'beginner'})
                RETURN m.name as model, r.reason as reason
                ORDER BY r.priority
                LIMIT 3
            """)
            
            for record in result:
                print(f"  - {record['model']}: {record['reason']}")
    
    def run(self):
        """执行完整导入流程"""
        print("=" * 60)
        print("🚀 开始导入训练知识到Neo4j")
        print("=" * 60)
        
        try:
            # 1. 清空数据库（可选）
            self.clear_database()
            
            # 2. 创建约束和索引
            self.create_constraints_and_indexes()
            
            # 3. 导入节点
            self.import_periodization_models()
            self.import_training_levels()
            self.import_muscle_groups()
            self.import_training_goals()
            
            # 4. 创建关系
            self.create_model_level_relationships()
            self.create_model_goal_relationships()
            
            # 5. 验证导入
            self.verify_import()
            
            print("\n" + "=" * 60)
            print("✅ 训练知识导入Neo4j完成！")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ 导入失败: {e}")
            raise
        finally:
            self.close()


def main():
    """主函数"""
    # 配置路径
    base_dir = Path(__file__).parent.parent.parent.parent
    knowledge_dir = base_dir / "perfect_enhanced_dataset" / "training_knowledge"
    
    # 检查目录
    if not knowledge_dir.exists():
        print(f"❌ 训练知识目录不存在: {knowledge_dir}")
        return
    
    # 执行导入
    importer = TrainingKnowledgeNeo4jImporter(
        knowledge_dir=str(knowledge_dir),
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="your_password"  # 请修改为实际密码
    )
    importer.run()


if __name__ == "__main__":
    main()
