#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建Exercise→InjuryType CONTRAINDICATED_FOR关系

基于运动学教授、专业健身教练、资深用户的专业判断
根据动作的生物力学特征、关节负荷、肌肉激活模式等因素
智能匹配禁忌症

优先级：P2
预期效果：更完善的安全评估
"""

import os
from neo4j import GraphDatabase
from datetime import datetime

# Neo4j连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")


class ContraindicationRuleEngine:
    """
    禁忌症规则引擎
    
    基于运动学专家知识库，根据动作特征判断禁忌症
    """
    
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.stats = {
            "contraindicated_for_created": 0,
            "exercises_analyzed": 0,
            "errors": []
        }
        
        # 运动学专家规则库
        self.rules = self._build_expert_rules()
    
    def close(self):
        self.driver.close()
    
    def log(self, message):
        """打印日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def _build_expert_rules(self):
        """
        构建运动学专家规则库
        
        规则格式：
        {
            "injury_type": "损伤类型",
            "conditions": [匹配条件],
            "severity": "严重程度",
            "reason": "禁忌原因"
        }
        """
        return [
            # === 脊柱相关损伤 ===
            {
                "injury_type": "herniated_disc",  # 腰椎间盘突出
                "conditions": {
                    "force": ["pull"],  # 拉力动作
                    "mechanic": ["compound"],  # 复合动作
                    "primary_muscles": ["背阔肌", "竖脊肌", "下背部", "背部"],  # 涉及下背部
                    "equipment": ["杠铃"],  # 杠铃动作
                    "name_keywords": ["硬拉", "划船", "俯身", "弯腰", "Deadlift", "Row"]  # 动作名称关键词
                },
                "severity": "high",
                "reason": "脊柱屈曲负荷过大，可能加重椎间盘压力"
            },
            {
                "injury_type": "lower_back_pain",  # 下背部疼痛
                "conditions": {
                    "force": ["pull"],
                    "primary_muscles": ["背阔肌", "竖脊肌", "下背部", "背部"],
                    "name_keywords": ["硬拉", "划船", "俯身", "Deadlift", "Row"]
                },
                "severity": "moderate",
                "reason": "下背部负荷增加，可能加重疼痛"
            },
            
            # === 肩关节损伤 ===
            {
                "injury_type": "rotator_cuff_injury",  # 肩袖损伤
                "conditions": {
                    "primary_muscles": ["肩部", "三角肌", "肩前部", "肩中部", "肩后部"],
                    "force": ["push", "pull"],
                    "name_keywords": ["推举", "侧平举", "飞鸟", "引体", "划船", "Press", "Raise", "Fly", "Pull"]
                },
                "severity": "high",
                "reason": "肩关节外展、旋转动作可能撕裂肩袖肌群"
            },
            {
                "injury_type": "shoulder_injury",  # 肩部受伤
                "conditions": {
                    "primary_muscles": ["肩部", "三角肌", "肩前部", "肩中部", "肩后部"],
                    "mechanic": ["compound"],
                    "name_keywords": ["卧推", "推举", "引体", "双杠", "Press", "Push", "Pull"]
                },
                "severity": "high",
                "reason": "肩关节极限位置可能导致再次受伤"
            },
            {
                "injury_type": "shoulder_impingement",  # 肩关节撞击综合征
                "conditions": {
                    "primary_muscles": ["肩部", "三角肌", "肩前部"],
                    "name_keywords": ["推举", "侧平举", "前平举", "Press", "Raise"]
                },
                "severity": "moderate",
                "reason": "肩关节上举动作可能加重撞击"
            },
            
            # === 膝关节损伤 ===
            {
                "injury_type": "acl_injury",  # 前交叉韧带损伤
                "conditions": {
                    "primary_muscles": ["股四头肌", "臀部", "腿部", "大腿"],
                    "mechanic": ["compound"],
                    "kinetic_chain_type": ["closed_chain"],
                    "name_keywords": ["深蹲", "弓步", "跳跃", "Squat", "Lunge", "Jump"]
                },
                "severity": "high",
                "reason": "膝关节剪切力过大，可能加重韧带损伤"
            },
            {
                "injury_type": "chondromalacia_patellae",  # 髌骨软化症
                "conditions": {
                    "primary_muscles": ["股四头肌", "大腿"],
                    "name_keywords": ["深蹲", "腿屈伸", "弓步", "Squat", "Extension", "Lunge"]
                },
                "severity": "moderate",
                "reason": "髌骨压力增加，可能加重软骨磨损"
            },
            {
                "injury_type": "knee_injury",  # 膝关节损伤
                "conditions": {
                    "primary_muscles": ["股四头肌", "腿部", "大腿"],
                    "mechanic": ["compound"],
                    "name_keywords": ["深蹲", "弓步", "Squat", "Lunge"]
                },
                "severity": "high",
                "reason": "膝关节负荷过大，可能加重损伤"
            },
            
            # === 腕关节损伤 ===
            {
                "injury_type": "carpal_tunnel",  # 腕管综合征
                "conditions": {
                    "primary_muscles": ["前臂", "手腕"],
                    "grips": ["overhand", "underhand", "neutral"],
                    "name_keywords": ["腕弯举", "握力", "支撑", "俯卧撑", "Curl", "Push"]
                },
                "severity": "moderate",
                "reason": "腕关节压力增加，可能压迫正中神经"
            },
            
            # === 髋关节损伤 ===
            {
                "injury_type": "itbs",  # 髂胫束综合征
                "conditions": {
                    "primary_muscles": ["臀部", "大腿", "腿部"],
                    "name_keywords": ["深蹲", "弓步", "跑步", "Squat", "Lunge", "Run"]
                },
                "severity": "moderate",
                "reason": "髋关节外展动作可能加重髂胫束摩擦"
            }
        ]
    
    def _match_rule(self, session, exercise_id, rule):
        """
        判断动作是否匹配规则（使用关系查询）
        
        返回：(是否匹配, 匹配分数)
        """
        conditions = rule["conditions"]
        score = 0
        max_score = 0
        
        # 检查force（通过USES_FORCE关系）
        if "force" in conditions:
            max_score += 1
            result = session.run("""
                MATCH (e:Exercise {id: $exercise_id})-[:USES_FORCE]->(f:ForceType)
                WHERE f.name IN $force_types
                RETURN count(f) as count
            """, {"exercise_id": exercise_id, "force_types": conditions["force"]})
            if result.single()["count"] > 0:
                score += 1
        
        # 检查mechanic（通过HAS_MECHANIC关系）
        if "mechanic" in conditions:
            max_score += 1
            result = session.run("""
                MATCH (e:Exercise {id: $exercise_id})-[:HAS_MECHANIC]->(m:MechanicType)
                WHERE m.name IN $mechanic_types
                RETURN count(m) as count
            """, {"exercise_id": exercise_id, "mechanic_types": conditions["mechanic"]})
            if result.single()["count"] > 0:
                score += 1
        
        # 检查kinetic_chain_type（通过HAS_KINETIC_CHAIN关系）
        if "kinetic_chain_type" in conditions:
            max_score += 1
            result = session.run("""
                MATCH (e:Exercise {id: $exercise_id})-[:HAS_KINETIC_CHAIN]->(k:KineticChain)
                WHERE k.name IN $kinetic_types
                RETURN count(k) as count
            """, {"exercise_id": exercise_id, "kinetic_types": conditions["kinetic_chain_type"]})
            if result.single()["count"] > 0:
                score += 1
        
        # 检查equipment（通过REQUIRES关系）
        if "equipment" in conditions:
            max_score += 1
            result = session.run("""
                MATCH (e:Exercise {id: $exercise_id})-[:REQUIRES]->(eq:Equipment)
                WHERE any(keyword IN $equipment_keywords WHERE eq.name_zh CONTAINS keyword OR eq.name_en CONTAINS keyword)
                RETURN count(eq) as count
            """, {"exercise_id": exercise_id, "equipment_keywords": conditions["equipment"]})
            if result.single()["count"] > 0:
                score += 1
        
        # 检查primary_muscles（通过TARGETS_PRIMARY关系）
        if "primary_muscles" in conditions:
            max_score += 2  # 肌肉匹配权重更高
            result = session.run("""
                MATCH (e:Exercise {id: $exercise_id})-[:TARGETS_PRIMARY]->(m:Muscle)
                WHERE any(keyword IN $muscle_keywords WHERE m.name_zh CONTAINS keyword)
                RETURN count(m) as count
            """, {"exercise_id": exercise_id, "muscle_keywords": conditions["primary_muscles"]})
            if result.single()["count"] > 0:
                score += 2
        
        # 检查grips（通过USES_GRIP关系）
        if "grips" in conditions:
            max_score += 1
            result = session.run("""
                MATCH (e:Exercise {id: $exercise_id})-[:USES_GRIP]->(g:GripType)
                WHERE g.name IN $grip_types
                RETURN count(g) as count
            """, {"exercise_id": exercise_id, "grip_types": conditions["grips"]})
            if result.single()["count"] > 0:
                score += 1
        
        # 检查name_keywords（直接查询Exercise节点属性）
        if "name_keywords" in conditions:
            max_score += 2  # 名称关键词权重更高
            result = session.run("""
                MATCH (e:Exercise {id: $exercise_id})
                WHERE any(keyword IN $keywords WHERE e.name_zh CONTAINS keyword OR toLower(e.name_en) CONTAINS toLower(keyword))
                RETURN count(e) as count
            """, {"exercise_id": exercise_id, "keywords": conditions["name_keywords"]})
            if result.single()["count"] > 0:
                score += 2
        
        # 匹配度阈值：至少50%
        if max_score > 0 and score / max_score >= 0.5:
            return True, score / max_score
        
        return False, 0
    
    def analyze_exercises(self):
        """分析所有动作并创建禁忌症关系"""
        self.log("\n🔍 分析动作并创建禁忌症关系...")
        
        with self.driver.session() as session:
            # 获取所有Exercise节点的ID
            result = session.run("""
                MATCH (e:Exercise)
                RETURN e.id as id, e.name_zh as name_zh
                LIMIT 1790
            """)
            
            exercises = list(result)
            self.log(f"  找到 {len(exercises)} 个动作")
            
            # 对每个动作应用规则
            for exercise in exercises:
                self.stats["exercises_analyzed"] += 1
                exercise_id = exercise["id"]
                exercise_name = exercise["name_zh"]
                
                for rule in self.rules:
                    matched, confidence = self._match_rule(session, exercise_id, rule)
                    
                    if matched:
                        try:
                            # 创建CONTRAINDICATED_FOR关系
                            result = session.run("""
                                MATCH (e:Exercise {id: $exercise_id})
                                MATCH (i:InjuryType {name: $injury_type})
                                MERGE (e)-[r:CONTRAINDICATED_FOR]->(i)
                                ON CREATE SET 
                                    r.severity = $severity,
                                    r.confidence = $confidence,
                                    r.reason = $reason,
                                    r.created_at = datetime()
                                RETURN e.name_zh as exercise_name, i.name as injury_type
                            """, {
                                "exercise_id": exercise_id,
                                "injury_type": rule["injury_type"],
                                "severity": rule["severity"],
                                "confidence": confidence,
                                "reason": rule["reason"]
                            })
                            
                            record = result.single()
                            if record:
                                self.stats["contraindicated_for_created"] += 1
                                if self.stats["contraindicated_for_created"] <= 10:
                                    self.log(f"    ✅ {record['exercise_name']} → {record['injury_type']} (置信度: {confidence:.2f})")
                        
                        except Exception as e:
                            self.stats["errors"].append(f"Exercise {exercise_id} -> {rule['injury_type']}: {e}")
            
            if self.stats["contraindicated_for_created"] > 10:
                self.log(f"    ... 还有 {self.stats['contraindicated_for_created'] - 10} 个关系")
        
        self.log(f"  ✅ 成功创建 {self.stats['contraindicated_for_created']} 个CONTRAINDICATED_FOR关系")
    
    def verify_results(self):
        """验证结果"""
        self.log("\n📊 验证结果...")
        
        with self.driver.session() as session:
            # 检查CONTRAINDICATED_FOR关系总数
            result = session.run("MATCH ()-[r:CONTRAINDICATED_FOR]->() RETURN count(r) as count")
            total_count = result.single()["count"]
            self.log(f"  CONTRAINDICATED_FOR关系总数: {total_count} 个")
            
            # 按InjuryType统计
            result = session.run("""
                MATCH (e:Exercise)-[r:CONTRAINDICATED_FOR]->(i:InjuryType)
                RETURN i.name as injury, count(e) as exercise_count, 
                       collect(DISTINCT r.severity)[0] as severity
                ORDER BY exercise_count DESC
                LIMIT 10
            """)
            
            self.log("\n  各损伤类型的禁忌动作数量（Top 10）:")
            for record in result:
                self.log(f"    {record['injury']}: {record['exercise_count']} 个动作 (严重程度: {record['severity']})")
            
            # 按严重程度统计
            result = session.run("""
                MATCH ()-[r:CONTRAINDICATED_FOR]->()
                RETURN r.severity as severity, count(r) as count
                ORDER BY count DESC
            """)
            
            self.log("\n  按严重程度统计:")
            for record in result:
                self.log(f"    {record['severity']}: {record['count']} 个")
    
    def print_summary(self):
        """打印总结"""
        self.log("\n" + "=" * 60)
        self.log("📊 执行总结")
        self.log("=" * 60)
        self.log(f"✅ 分析动作: {self.stats['exercises_analyzed']} 个")
        self.log(f"✅ 创建关系: {self.stats['contraindicated_for_created']} 个")
        self.log(f"✅ 应用规则: {len(self.rules)} 条")
        
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
            self.log("🚀 创建Exercise→InjuryType禁忌症关系")
            self.log("=" * 60)
            self.log("\n基于运动学专家知识库")
            self.log(f"规则数量: {len(self.rules)} 条")
            
            # 1. 分析动作并创建关系
            self.analyze_exercises()
            
            # 2. 验证结果
            self.verify_results()
            
            # 3. 打印总结
            self.print_summary()
            
            self.log("\n✅ 完成!")
        
        except Exception as e:
            self.log(f"\n❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.close()


if __name__ == "__main__":
    engine = ContraindicationRuleEngine()
    engine.run()
