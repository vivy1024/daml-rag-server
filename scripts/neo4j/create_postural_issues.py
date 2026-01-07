# -*- coding: utf-8 -*-
"""
Neo4j体态问题节点创建脚本

创建PosturalIssue节点类型并建立相关关系：
- PosturalIssue节点：12种常见体态问题
- CORRECTS关系：Exercise → PosturalIssue（矫正动作）
- AGGRAVATES关系：Exercise → PosturalIssue（加重动作）
- RELATED_TO关系：PosturalIssue → Muscle（相关肌肉）

版本: v1.0.0
日期: 2026-01-05
Requirements: 20.1, 20.2, 20.3, 20.4
"""

import sys
import os
import logging
from typing import List, Dict, Any
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
class PosturalIssueDefinition:
    """体态问题定义"""
    name: str
    name_zh: str
    description: str
    category: str
    related_muscles: List[str]
    corrective_exercises: List[str]
    aggravating_exercises: List[str]



# 体态问题数据定义
POSTURAL_ISSUES_DATA = [
    # 上半身体态问题
    {
        "name": "rounded_shoulders",
        "name_zh": "圆肩",
        "description": "肩部向前旋转，胸肌紧张，上背肌肉无力",
        "category": "upper_body",
        "related_muscles": ["pectoralis_major", "anterior_deltoid", "rhomboids", "middle_trapezius"],
        "corrective_exercises": ["face pull", "band pull apart", "wall slide", "prone y raise"],
        "aggravating_exercises": ["bench press", "push up", "chest fly"]
    },
    {
        "name": "forward_head",
        "name_zh": "头前伸",
        "description": "头部向前突出，颈部肌肉紧张",
        "category": "upper_body",
        "related_muscles": ["sternocleidomastoid", "upper_trapezius", "levator_scapulae"],
        "corrective_exercises": ["chin tuck", "neck retraction", "prone cobra"],
        "aggravating_exercises": ["overhead press", "upright row"]
    },
    {
        "name": "excessive_thoracic_kyphosis",
        "name_zh": "胸椎后凸过度(驼背)",
        "description": "上背部过度弯曲，胸椎后凸角度过大",
        "category": "spine",
        "related_muscles": ["thoracic_erectors", "rhomboids", "middle_trapezius", "pectoralis_major"],
        "corrective_exercises": ["thoracic extension", "foam roll", "prone t raise"],
        "aggravating_exercises": ["sit up", "crunch"]
    },
    {
        "name": "flat_back",
        "name_zh": "胸椎后凸不足(平背)",
        "description": "上背部过于平直，缺乏正常的胸椎曲度",
        "category": "spine",
        "related_muscles": ["thoracic_erectors", "latissimus_dorsi"],
        "corrective_exercises": ["cat cow stretch", "thoracic rotation"],
        "aggravating_exercises": ["deadlift", "good morning"]
    },
    # 骨盆和腰椎问题
    {
        "name": "anterior_pelvic_tilt",
        "name_zh": "骨盆前倾",
        "description": "骨盆向前倾斜，腰椎前凸过度",
        "category": "lower_body",
        "related_muscles": ["hip_flexors", "rectus_femoris", "lumbar_erectors", "rectus_abdominis", "glutes"],
        "corrective_exercises": ["hip flexor stretch", "glute bridge", "dead bug", "plank"],
        "aggravating_exercises": ["back squat", "overhead press", "sit up"]
    },
    {
        "name": "posterior_pelvic_tilt",
        "name_zh": "骨盆后倾",
        "description": "骨盆向后倾斜，腰椎曲度减小",
        "category": "lower_body",
        "related_muscles": ["hamstrings", "glutes", "hip_flexors", "lumbar_erectors"],
        "corrective_exercises": ["hip thrust", "romanian deadlift", "lumbar extension"],
        "aggravating_exercises": ["leg curl", "crunch"]
    },
    {
        "name": "excessive_lumbar_lordosis",
        "name_zh": "腰椎前凸过度",
        "description": "腰椎向前弯曲过度，下背部过度拱起",
        "category": "spine",
        "related_muscles": ["lumbar_erectors", "hip_flexors", "rectus_abdominis", "glutes"],
        "corrective_exercises": ["pelvic tilt", "cat stretch", "knee to chest"],
        "aggravating_exercises": ["back extension", "superman"]
    },
    {
        "name": "scoliosis",
        "name_zh": "脊柱侧弯",
        "description": "脊柱向侧方弯曲，左右不对称",
        "category": "spine",
        "related_muscles": ["quadratus_lumborum", "obliques", "erector_spinae"],
        "corrective_exercises": ["side plank", "bird dog", "single arm row"],
        "aggravating_exercises": ["heavy squat", "heavy deadlift"]
    },
    # 下肢体态问题
    {
        "name": "genu_varum",
        "name_zh": "膝内翻(O型腿)",
        "description": "双膝向外弯曲，膝关节内侧间距增大",
        "category": "lower_body",
        "related_muscles": ["adductors", "vastus_medialis", "glutes"],
        "corrective_exercises": ["adductor squeeze", "side lying leg lift", "clamshell"],
        "aggravating_exercises": ["wide stance squat", "sumo deadlift"]
    },
    {
        "name": "genu_valgum",
        "name_zh": "膝外翻(X型腿)",
        "description": "双膝向内弯曲，膝关节向内靠拢",
        "category": "lower_body",
        "related_muscles": ["abductors", "glutes", "vastus_lateralis"],
        "corrective_exercises": ["lateral band walk", "single leg squat", "hip abduction"],
        "aggravating_exercises": ["narrow stance squat", "leg press"]
    },
    # 足部体态问题
    {
        "name": "flat_feet",
        "name_zh": "扁平足",
        "description": "足弓塌陷，足底平坦",
        "category": "lower_body",
        "related_muscles": ["tibialis_posterior", "gastrocnemius"],
        "corrective_exercises": ["toe curl", "arch lift", "calf raise"],
        "aggravating_exercises": ["running", "jumping"]
    },
    {
        "name": "high_arches",
        "name_zh": "高弓足",
        "description": "足弓过高，足底接触面积小",
        "category": "lower_body",
        "related_muscles": ["plantar_fascia", "peroneus"],
        "corrective_exercises": ["foot roll", "toe spread", "ankle mobility"],
        "aggravating_exercises": ["box jump", "plyometric"]
    },
]



class PosturalIssueCreator:
    """体态问题节点创建器"""
    
    def __init__(self, neo4j_manager: Neo4jManager):
        self.manager = neo4j_manager
        self.issues = [PosturalIssueDefinition(**data) for data in POSTURAL_ISSUES_DATA]
        
    def create_nodes(self) -> Dict[str, Any]:
        """创建PosturalIssue节点"""
        created = 0
        existing = 0
        errors = []
        
        logger.info("=" * 60)
        logger.info("开始创建PosturalIssue节点...")
        logger.info("=" * 60)
        
        for issue in self.issues:
            try:
                query = """
                MERGE (p:PosturalIssue {name: $name})
                ON CREATE SET p.name_zh = $name_zh,
                              p.description = $description,
                              p.category = $category
                ON MATCH SET p.name_zh = $name_zh,
                             p.description = $description,
                             p.category = $category
                RETURN p, 
                       CASE WHEN p.name_zh IS NULL THEN 'created' ELSE 'existing' END as status
                """
                params = {
                    "name": issue.name,
                    "name_zh": issue.name_zh,
                    "description": issue.description,
                    "category": issue.category
                }
                result = self.manager.execute_write(query, params)
                
                if result and result[0].get("status") == "created":
                    created += 1
                    logger.info(f"  ✅ 创建: {issue.name_zh}")
                else:
                    existing += 1
                    logger.debug(f"  🔄 更新: {issue.name_zh}")
                    
            except Exception as e:
                errors.append(f"{issue.name_zh}: {str(e)}")
                logger.error(f"  ❌ 失败: {issue.name_zh} - {str(e)}")
                
        logger.info("=" * 60)
        logger.info(f"节点创建完成: 新建={created}, 已存在={existing}, 错误={len(errors)}")
        logger.info("=" * 60)
        
        return {"created": created, "existing": existing, "errors": errors}
        
    def create_related_to_relationships(self) -> Dict[str, Any]:
        """创建PosturalIssue → Muscle关系"""
        created = 0
        skipped = 0
        errors = []
        
        logger.info("\n创建RELATED_TO关系...")
        
        for issue in self.issues:
            for muscle_name in issue.related_muscles:
                try:
                    query = """
                    MATCH (p:PosturalIssue {name: $issue_name})
                    MATCH (m:Muscle {name: $muscle_name})
                    MERGE (p)-[r:RELATED_TO]->(m)
                    RETURN r
                    """
                    result = self.manager.execute_write(query, {
                        "issue_name": issue.name,
                        "muscle_name": muscle_name
                    })
                    
                    if result:
                        created += 1
                    else:
                        skipped += 1
                        logger.debug(f"  ⚠️ 未找到肌肉: {muscle_name}")
                        
                except Exception as e:
                    errors.append(f"{issue.name_zh} → {muscle_name}: {str(e)}")
                    
        logger.info(f"RELATED_TO关系: 创建={created}, 跳过={skipped}, 错误={len(errors)}")
        return {"created": created, "skipped": skipped, "errors": errors}
        
    def create_corrects_relationships(self) -> Dict[str, Any]:
        """创建Exercise → PosturalIssue CORRECTS关系"""
        created = 0
        skipped = 0
        errors = []
        
        logger.info("\n创建CORRECTS关系...")
        
        for issue in self.issues:
            for exercise_name in issue.corrective_exercises:
                try:
                    # 使用中文关键词匹配（更宽松的匹配策略）
                    # 例如："face pull" -> "面拉", "plank" -> "平板", "glute bridge" -> "臀桥"
                    query = """
                    MATCH (e:Exercise)
                    WHERE toLower(e.name_zh) CONTAINS toLower($exercise_keyword)
                       OR toLower(e.name_en) CONTAINS toLower($exercise_name)
                    MATCH (p:PosturalIssue {name: $issue_name})
                    MERGE (e)-[r:CORRECTS]->(p)
                    RETURN count(r) as count
                    """
                    
                    # 英文到中文关键词映射
                    keyword_mapping = {
                        "face pull": "面拉",
                        "band pull apart": "弹力带",
                        "wall slide": "墙壁",
                        "prone y raise": "俯卧Y",
                        "chin tuck": "下巴",
                        "neck retraction": "颈部",
                        "prone cobra": "俯卧眼镜蛇",
                        "thoracic extension": "胸椎伸展",
                        "foam roll": "泡沫轴",
                        "prone t raise": "俯卧T",
                        "cat cow stretch": "猫牛式",
                        "thoracic rotation": "胸椎旋转",
                        "hip flexor stretch": "髋屈肌拉伸",
                        "glute bridge": "臀桥",
                        "dead bug": "死虫",
                        "plank": "平板",
                        "hip thrust": "臀冲",
                        "romanian deadlift": "罗马尼亚硬拉",
                        "lumbar extension": "腰椎伸展",
                        "pelvic tilt": "骨盆倾斜",
                        "cat stretch": "猫式",
                        "knee to chest": "膝盖",
                        "back extension": "背部伸展",
                        "superman": "超人",
                        "side plank": "侧平板",
                        "bird dog": "鸟狗",
                        "single arm row": "单臂划船",
                        "adductor squeeze": "内收肌",
                        "side lying leg lift": "侧卧抬腿",
                        "clamshell": "蚌式",
                        "lateral band walk": "侧向弹力带",
                        "single leg squat": "单腿深蹲",
                        "hip abduction": "髋外展",
                        "toe curl": "脚趾",
                        "arch lift": "足弓",
                        "calf raise": "提踵",
                        "foot roll": "足部滚动",
                        "toe spread": "脚趾伸展",
                        "ankle mobility": "踝关节",
                    }
                    
                    # 获取中文关键词
                    exercise_keyword = keyword_mapping.get(exercise_name.lower(), exercise_name)
                    
                    result = self.manager.execute_write(query, {
                        "exercise_keyword": exercise_keyword,
                        "exercise_name": exercise_name,
                        "issue_name": issue.name
                    })
                    
                    if result and result[0]["count"] > 0:
                        created += result[0]["count"]
                        logger.info(f"  ✅ {exercise_name} ({exercise_keyword}) → {issue.name_zh}: {result[0]['count']}个")
                    else:
                        skipped += 1
                        logger.debug(f"  ⚠️ 未找到动作: {exercise_name} ({exercise_keyword})")
                        
                except Exception as e:
                    errors.append(f"{exercise_name} → {issue.name_zh}: {str(e)}")
                    
        logger.info(f"CORRECTS关系: 创建={created}, 跳过={skipped}, 错误={len(errors)}")
        return {"created": created, "skipped": skipped, "errors": errors}
        
    def create_aggravates_relationships(self) -> Dict[str, Any]:
        """创建Exercise → PosturalIssue AGGRAVATES关系"""
        created = 0
        skipped = 0
        errors = []
        
        logger.info("\n创建AGGRAVATES关系...")
        
        for issue in self.issues:
            for exercise_name in issue.aggravating_exercises:
                try:
                    # 使用中文关键词匹配
                    query = """
                    MATCH (e:Exercise)
                    WHERE toLower(e.name_zh) CONTAINS toLower($exercise_keyword)
                       OR toLower(e.name_en) CONTAINS toLower($exercise_name)
                    MATCH (p:PosturalIssue {name: $issue_name})
                    MERGE (e)-[r:AGGRAVATES]->(p)
                    RETURN count(r) as count
                    """
                    
                    # 英文到中文关键词映射
                    keyword_mapping = {
                        "bench press": "卧推",
                        "push up": "俯卧撑",
                        "chest fly": "飞鸟",
                        "overhead press": "推举",
                        "upright row": "直立划船",
                        "sit up": "仰卧起坐",
                        "crunch": "卷腹",
                        "deadlift": "硬拉",
                        "good morning": "早安",
                        "back squat": "深蹲",
                        "leg curl": "腿弯举",
                        "heavy squat": "深蹲",
                        "heavy deadlift": "硬拉",
                        "wide stance squat": "宽站距深蹲",
                        "sumo deadlift": "相扑硬拉",
                        "narrow stance squat": "窄站距深蹲",
                        "leg press": "腿举",
                        "running": "跑步",
                        "jumping": "跳跃",
                        "box jump": "箱子跳",
                        "plyometric": "增强式",
                    }
                    
                    # 获取中文关键词
                    exercise_keyword = keyword_mapping.get(exercise_name.lower(), exercise_name)
                    
                    result = self.manager.execute_write(query, {
                        "exercise_keyword": exercise_keyword,
                        "exercise_name": exercise_name,
                        "issue_name": issue.name
                    })
                    
                    if result and result[0]["count"] > 0:
                        created += result[0]["count"]
                        logger.info(f"  ✅ {exercise_name} ({exercise_keyword}) → {issue.name_zh}: {result[0]['count']}个")
                    else:
                        skipped += 1
                        logger.debug(f"  ⚠️ 未找到动作: {exercise_name} ({exercise_keyword})")
                        
                except Exception as e:
                    errors.append(f"{exercise_name} → {issue.name_zh}: {str(e)}")
                    
        logger.info(f"AGGRAVATES关系: 创建={created}, 跳过={skipped}, 错误={len(errors)}")
        return {"created": created, "skipped": skipped, "errors": errors}
        
    def verify(self) -> Dict[str, Any]:
        """验证创建结果"""
        logger.info("\n" + "=" * 60)
        logger.info("验证PosturalIssue节点和关系...")
        logger.info("=" * 60)
        
        # 统计节点和关系数量
        stats_query = """
        MATCH (p:PosturalIssue)
        OPTIONAL MATCH (p)-[r1:RELATED_TO]->(m:Muscle)
        OPTIONAL MATCH (e1:Exercise)-[r2:CORRECTS]->(p)
        OPTIONAL MATCH (e2:Exercise)-[r3:AGGRAVATES]->(p)
        RETURN count(DISTINCT p) as nodes,
               count(DISTINCT r1) as related_to,
               count(DISTINCT r2) as corrects,
               count(DISTINCT r3) as aggravates
        """
        stats = self.manager.execute_query(stats_query, {})
        
        if stats:
            result = stats[0]
            logger.info(f"  PosturalIssue节点: {result['nodes']}/{len(self.issues)}")
            logger.info(f"  RELATED_TO关系: {result['related_to']}")
            logger.info(f"  CORRECTS关系: {result['corrects']}")
            logger.info(f"  AGGRAVATES关系: {result['aggravates']}")
            
            # 详细统计
            detail_query = """
            MATCH (p:PosturalIssue)
            OPTIONAL MATCH (p)-[:RELATED_TO]->(m:Muscle)
            OPTIONAL MATCH (e1:Exercise)-[:CORRECTS]->(p)
            OPTIONAL MATCH (e2:Exercise)-[:AGGRAVATES]->(p)
            RETURN p.name_zh as issue,
                   count(DISTINCT m) as muscles,
                   count(DISTINCT e1) as corrects,
                   count(DISTINCT e2) as aggravates
            ORDER BY p.name_zh
            """
            details = self.manager.execute_query(detail_query, {})
            
            logger.info("\n详细统计:")
            for d in details:
                logger.info(f"  {d['issue']}: 肌肉={d['muscles']}, 矫正={d['corrects']}, 加重={d['aggravates']}")
            
            logger.info("=" * 60)
            return result
        
        return {}



def main():
    """主函数"""
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "build_body_2024")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    manager = None
    
    try:
        logger.info("连接Neo4j数据库...")
        manager = Neo4jManager(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            database=neo4j_database
        )
        logger.info("✅ 数据库连接成功\n")
        
        creator = PosturalIssueCreator(manager)
        
        # 1. 创建节点
        node_result = creator.create_nodes()
        
        # 2. 创建关系
        related_result = creator.create_related_to_relationships()
        corrects_result = creator.create_corrects_relationships()
        aggravates_result = creator.create_aggravates_relationships()
        
        # 3. 验证
        verification = creator.verify()
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 体态问题节点和关系创建完成！")
        logger.info("=" * 60)
        
        return 0
            
    except Exception as e:
        logger.error(f"❌ 执行失败: {str(e)}")
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
