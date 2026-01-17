#!/usr/bin/env python3
"""
导入Exercise数据到Qdrant向量数据库

从enhanced_perfect_exercises_dataset.json读取数据，
使用BGE-M3模型生成向量，导入到fitness_exercises_v2集合。

Author: 薛小川
Created: 2026-01-04
"""

import json
import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

# 禁用代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,qdrant'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ExerciseQdrantImporter:
    """Exercise数据Qdrant导入器"""
    
    def __init__(
        self,
        data_file: str,
        qdrant_host: str = "qdrant",
        qdrant_port: int = 6333,
        qdrant_api_key: str = None,
        collection_name: str = "fitness_exercises_v2",
        vector_size: int = 1024,
        embedding_model: str = "BAAI/bge-m3"
    ):
        self.data_file = Path(data_file)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.embedding_model = embedding_model
        
        # 连接Qdrant（支持API Key）
        if qdrant_api_key:
            self.client = QdrantClient(
                host=qdrant_host, 
                port=qdrant_port,
                api_key=qdrant_api_key,
                https=False  # 内网使用HTTP
            )
            logger.info(f"✅ 连接到Qdrant: {qdrant_host}:{qdrant_port} (使用API Key)")
        else:
            self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
            logger.info(f"✅ 连接到Qdrant: {qdrant_host}:{qdrant_port}")
        
        # 加载BGE-M3模型
        self.encoder = self._load_encoder()
    
    def _load_encoder(self):
        """加载BGE-M3编码器"""
        logger.info(f"🔄 加载嵌入模型: {self.embedding_model}")
        
        try:
            # 尝试使用缓存的模型
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from src.framework.models.model_cache_manager import ModelCacheManager
            
            model_cache = ModelCacheManager.get_instance()
            encoder = model_cache.get_bge_model(self.embedding_model)
            
            if encoder:
                logger.info(f"✅ 从缓存加载模型: {self.embedding_model}")
                return encoder
        except Exception as e:
            logger.warning(f"⚠️ 无法从缓存加载模型: {e}")
        
        # 直接加载
        try:
            from sentence_transformers import SentenceTransformer
            encoder = SentenceTransformer(self.embedding_model)
            logger.info(f"✅ 直接加载模型: {self.embedding_model}")
            return encoder
        except Exception as e:
            logger.error(f"❌ 无法加载模型: {e}")
            raise
    
    def load_exercises(self) -> List[Dict[str, Any]]:
        """加载Exercise数据"""
        logger.info(f"📥 加载数据文件: {self.data_file}")
        
        with open(self.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        exercises = data.get('enhanced_perfect_exercises', [])
        logger.info(f"✅ 加载了 {len(exercises)} 个Exercise")
        
        return exercises
    
    def build_search_text(self, exercise: Dict[str, Any]) -> str:
        """
        构建用于语义搜索的文本（增强版 v3.0 - Neo4j字段统一）
        
        优化策略：
        1. 与Neo4j Exercise节点字段完全统一
        2. 提升权重：名称重复3次，主要肌群重复2次
        3. 扩展描述：500字，步骤说明300字
        4. 新增：所有肌群、力类型、动作类型、动力链、握法
        
        目标：最高分 >0.85，平均分 >0.80
        """
        parts = []
        
        # 1. 名称（中英文）- 权重最高，重复3次
        name_zh = exercise.get('name_zh', '')
        name_en = exercise.get('name_en', '')
        if name_zh:
            parts.extend([name_zh] * 3)  # 重复3次提升权重
        if name_en:
            parts.append(name_en)
        
        # 2. 主要肌群 - 权重高，重复2次
        primary_muscle = exercise.get('primary_muscle_zh', '')
        if primary_muscle:
            parts.extend([primary_muscle] * 2)
        
        # 3. 所有主要肌群（从muscles_primary_zh获取）
        muscles_primary = exercise.get('muscles_primary_zh', [])
        if isinstance(muscles_primary, list):
            parts.extend([str(m) for m in muscles_primary if m])
        
        # 4. 次要肌群（从muscles_secondary_zh获取）
        secondary_muscles = exercise.get('muscles_secondary_zh', [])
        if isinstance(secondary_muscles, list) and secondary_muscles:
            parts.extend([str(m) for m in secondary_muscles if m])
        
        # 5. 所有相关肌群（从all_muscles_zh获取）
        all_muscles = exercise.get('all_muscles_zh', [])
        if isinstance(all_muscles, list):
            parts.extend([str(m) for m in all_muscles if m])
        
        # 6. 力类型（推/拉/保持）- 使用force_zh字段
        force_zh = exercise.get('force_zh', '')
        if force_zh and isinstance(force_zh, str):
            parts.append(force_zh)
        
        # 7. 动作类型（复合/单关节）- 使用mechanic_zh字段
        mechanic_zh = exercise.get('mechanic_zh', '')
        if mechanic_zh and isinstance(mechanic_zh, str):
            parts.append(mechanic_zh)
        
        # 8. 动力链（开链/闭链/混合）
        kinetic_chain = exercise.get('kinetic_chain_type', '')
        if kinetic_chain and isinstance(kinetic_chain, str):
            # 转换为中文
            kinetic_chain_map = {
                'open_chain': '开链动作',
                'closed_chain': '闭链动作',
                'mixed': '混合动作'
            }
            parts.append(kinetic_chain_map.get(kinetic_chain, kinetic_chain))
        
        # 9. 握法（从grips_zh获取）
        grips = exercise.get('grips_zh', [])
        if isinstance(grips, list):
            parts.extend([str(g) for g in grips if g])
        elif grips and isinstance(grips, str):
            parts.append(grips)
        
        # 10. 器械（可能是字符串或列表）
        equipment = exercise.get('equipment_zh', '')
        if isinstance(equipment, list):
            parts.extend([str(e) for e in equipment if e])
        elif equipment and isinstance(equipment, str):
            parts.append(equipment)
        
        # 11. 难度（使用difficulty_zh字段）
        difficulty = exercise.get('difficulty_zh', '') or exercise.get('difficulty', '')
        if difficulty and isinstance(difficulty, str):
            parts.append(difficulty)
        
        # 12. 训练参数
        rep_range = exercise.get('rep_range', '')
        if rep_range:
            parts.append(f"次数范围{rep_range}次")
        
        set_range = exercise.get('set_range', '')
        if set_range:
            parts.append(f"组数{set_range}组")
        
        # 13. 描述（扩展到500字）
        desc = exercise.get('description_zh', '') or ''
        if desc and isinstance(desc, str):
            parts.append(desc[:500])
        
        # 14. 正确步骤（从correct_steps_zh获取，取前300字）
        steps = exercise.get('correct_steps_zh', []) or []
        if isinstance(steps, list) and steps:
            steps_text = ' '.join(str(s) for s in steps if s)[:300]
            if steps_text:
                parts.append(steps_text)
        
        # 15. 安全等级
        safety_level = exercise.get('safety_level', '')
        if safety_level and isinstance(safety_level, str):
            safety_map = {
                'LOW_RISK': '低风险',
                'MODERATE_RISK': '中等风险',
                'HIGH_RISK': '高风险'
            }
            parts.append(safety_map.get(safety_level, safety_level))
        
        return ' '.join(parts)
    
    def build_payload(self, exercise: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建Qdrant payload（增强版 v3.0 - Neo4j字段统一）
        
        与Neo4j Exercise节点字段完全统一，支持丰富的过滤和检索
        """
        # 处理equipment_zh - 确保是字符串
        equipment = exercise.get('equipment_zh', '')
        if isinstance(equipment, list):
            equipment_str = ', '.join(equipment) if equipment else ''
        else:
            equipment_str = equipment or ''
        
        # 处理grips_zh - 确保是列表
        grips = exercise.get('grips_zh', [])
        if not isinstance(grips, list):
            grips = [grips] if grips else []
        
        # 处理muscles_secondary_zh - 确保是列表
        secondary_muscles = exercise.get('muscles_secondary_zh', [])
        if not isinstance(secondary_muscles, list):
            secondary_muscles = [secondary_muscles] if secondary_muscles else []
        
        # 处理all_muscles_zh - 确保是列表
        all_muscles = exercise.get('all_muscles_zh', [])
        if not isinstance(all_muscles, list):
            all_muscles = [all_muscles] if all_muscles else []
        
        # 处理correct_steps_zh - 确保是列表
        steps = exercise.get('correct_steps_zh', [])
        if not isinstance(steps, list):
            steps = [steps] if steps else []
        
        # 动力链中文映射
        kinetic_chain = exercise.get('kinetic_chain_type', '')
        kinetic_chain_zh_map = {
            'open_chain': '开链',
            'closed_chain': '闭链',
            'mixed': '混合'
        }
        kinetic_chain_zh = kinetic_chain_zh_map.get(kinetic_chain, kinetic_chain)
        
        # 安全等级中文映射
        safety_level = exercise.get('safety_level', '')
        safety_level_zh_map = {
            'LOW_RISK': '低风险',
            'MODERATE_RISK': '中等风险',
            'HIGH_RISK': '高风险'
        }
        safety_level_zh = safety_level_zh_map.get(safety_level, safety_level)
        
        return {
            # === 基础信息 ===
            'exercise_id': exercise['id'],  # 整数ID，用于与Neo4j关联
            'name_zh': exercise.get('name_zh') or '',
            'name_en': exercise.get('name_en') or '',
            'slug': exercise.get('slug') or '',
            
            # === 肌肉信息（与Neo4j统一）===
            'primary_muscle_zh': exercise.get('primary_muscle_zh') or '',
            'primary_muscle_en': exercise.get('primary_muscle_en') or '',
            'secondary_muscles_zh': secondary_muscles,  # 次要肌群列表
            'all_muscles_zh': all_muscles,  # 所有相关肌群
            
            # === 运动学分类（与Neo4j统一）===
            'force_zh': exercise.get('force_zh') or '',  # 力类型：推力/拉力/保持
            'force_en': exercise.get('force_en') or '',
            'mechanic_zh': exercise.get('mechanic_zh') or '',  # 动作类型：复合/单关节
            'mechanic_en': exercise.get('mechanic_en') or '',
            'kinetic_chain_type': kinetic_chain,  # 动力链：open_chain/closed_chain/mixed
            'kinetic_chain_zh': kinetic_chain_zh,  # 动力链中文
            'grips_zh': grips,  # 握法列表
            
            # === 器械和难度 ===
            'equipment_zh': equipment_str,
            'equipment_en': exercise.get('equipment_en') or '',
            'difficulty': exercise.get('difficulty_zh') or exercise.get('difficulty') or '中级',
            'difficulty_en': exercise.get('difficulty_en') or '',
            
            # === 训练参数（与Neo4j统一）===
            'rep_range': exercise.get('rep_range') or '',  # 次数范围
            'set_range': exercise.get('set_range') or '',  # 组数范围
            'rest_period': exercise.get('rest_period') or '',  # 休息时间
            'intensity_percentage': exercise.get('intensity_percentage') or '',  # 强度百分比
            
            # === 描述和步骤 ===
            'description_zh': (exercise.get('description_zh') or '')[:1000],  # 限制长度，处理None
            'correct_steps_zh': steps,  # 正确步骤列表
            
            # === 安全信息（与Neo4j统一）===
            'safety_level': safety_level,  # 安全等级
            'safety_level_zh': safety_level_zh,  # 安全等级中文
            
          
            
            # === 搜索文本（用于向量化）===
            'search_text': self.build_search_text(exercise),
        }
    
    def ensure_collection_exists(self, recreate: bool = False):
        """确保集合存在"""
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if exists and recreate:
            logger.info(f"🗑️ 删除现有集合: {self.collection_name}")
            self.client.delete_collection(self.collection_name)
            exists = False
        
        if not exists:
            logger.info(f"📦 创建集合: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"✅ 集合创建成功")
        else:
            logger.info(f"✅ 集合已存在: {self.collection_name}")
    
    def import_exercises(self, exercises: List[Dict[str, Any]], batch_size: int = 100):
        """导入Exercise到Qdrant"""
        logger.info(f"📥 开始导入 {len(exercises)} 个Exercise...")
        
        total = len(exercises)
        success_count = 0
        error_count = 0
        
        for i in range(0, total, batch_size):
            batch = exercises[i:i + batch_size]
            
            # 构建搜索文本
            search_texts = [self.build_search_text(ex) for ex in batch]
            
            # 批量编码
            try:
                vectors = self.encoder.encode(search_texts, normalize_embeddings=True)
            except Exception as e:
                logger.error(f"❌ 编码失败: {e}")
                error_count += len(batch)
                continue
            
            # 构建Qdrant点
            points = []
            for j, (exercise, vector) in enumerate(zip(batch, vectors)):
                try:
                    point = PointStruct(
                        id=exercise['id'],  # 使用exercise_id作为Qdrant点ID
                        vector=vector.tolist(),
                        payload=self.build_payload(exercise)
                    )
                    points.append(point)
                except Exception as e:
                    logger.error(f"❌ 构建点失败 (ID: {exercise.get('id')}): {e}")
                    error_count += 1
            
            # 批量插入
            if points:
                try:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=points
                    )
                    success_count += len(points)
                except Exception as e:
                    logger.error(f"❌ 插入失败: {e}")
                    error_count += len(points)
            
            logger.info(f"  进度: {min(i + batch_size, total)}/{total} ({(min(i + batch_size, total)) * 100 // total}%)")
        
        logger.info(f"\n✅ 导入完成: 成功 {success_count} 个, 失败 {error_count} 个")
        return success_count, error_count
    
    def verify_import(self):
        """验证导入结果"""
        logger.info("\n📊 验证导入结果...")
        
        # 获取集合信息
        info = self.client.get_collection(self.collection_name)
        logger.info(f"  总向量数: {info.points_count}")
        
        # 测试搜索
        test_query = "胸部训练 卧推"
        logger.info(f"\n🔍 测试搜索: '{test_query}'")
        
        query_vector = self.encoder.encode(test_query, normalize_embeddings=True)
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector.tolist(),
            limit=5
        )
        
        for r in results.points:
            logger.info(f"  - {r.payload.get('name_zh')} (ID: {r.payload.get('exercise_id')}, 分数: {r.score:.4f})")
    
    def run(self, recreate: bool = False):
        """执行完整导入流程"""
        logger.info("=" * 60)
        logger.info("🚀 开始导入Exercise数据到Qdrant")
        logger.info("=" * 60)
        
        try:
            # 1. 加载数据
            exercises = self.load_exercises()
            
            # 2. 确保集合存在
            self.ensure_collection_exists(recreate=recreate)
            
            # 3. 导入数据
            self.import_exercises(exercises)
            
            # 4. 验证
            self.verify_import()
            
            logger.info("\n" + "=" * 60)
            logger.info("✅ Exercise数据导入Qdrant完成！")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"\n❌ 导入失败: {e}")
            import traceback
            traceback.print_exc()
            raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='导入Exercise数据到Qdrant')
    parser.add_argument('--recreate', '-r', action='store_true',
                       help='重新创建集合（删除现有数据）')
    args = parser.parse_args()
    
    # 数据文件路径
    data_file = Path("/app/data/enhanced_perfect_exercises_dataset.json")
    
    if not data_file.exists():
        logger.error(f"❌ 数据文件不存在: {data_file}")
        return
    
    # 执行导入
    # 模型选择：GTE-Large-zh（测试结果：相关性94.4%，综合分0.7580，最佳）
    importer = ExerciseQdrantImporter(
        data_file=str(data_file),
        qdrant_host=os.getenv('QDRANT_HOST', 'qdrant'),
        qdrant_port=int(os.getenv('QDRANT_PORT', '6333')),
        collection_name='fitness_exercises_v2',
        vector_size=1024,  # GTE-Large-zh输出1024维
        embedding_model='thenlper/gte-large-zh'
    )
    importer.run(recreate=args.recreate)


if __name__ == "__main__":
    main()
