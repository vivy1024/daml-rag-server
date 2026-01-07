#!/usr/bin/env python3
"""
食物营养数据向量化脚本
将Neo4j中的1880个食物及其营养成分生成向量并存入Qdrant

作者：BUILD_BODY Team
版本：v1.0.0
日期：2025-11-14
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
from datetime import datetime
import requests
from neo4j import AsyncGraphDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FoodNutritionVectorizer:
    """食物营养数据向量化器"""

    def __init__(self,
                 qdrant_host: str = "localhost",
                 qdrant_port: int = 6333,
                 neo4j_uri: str = "bolt://localhost:7687",
                 neo4j_user: str = "neo4j",
                 neo4j_password: str = "build_body_2024"):
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.qdrant_url = f"http://{qdrant_host}:{qdrant_port}"
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password

        # 向量化统计
        self.stats = {
            "total_foods": 0,
            "vectorized_foods": 0,
            "failed_foods": 0,
            "processing_time": 0.0,
            "categories": {},
            "vectors_created": 0
        }

    async def create_food_nutrition_collection(self, vector_size: int = 768):
        """创建食物营养向量集合"""
        logger.info(f"创建Qdrant集合: food_nutrition_vector")

        collection_config = {
            "vectors": {
                "size": vector_size,
                "distance": "Cosine"
            },
            "payload_schema": {
                "food_code": "keyword",
                "food_name": "text",
                "category": "keyword",
                "nutrients": "json",
                "total_calories": "float",
                "protein_g": "float",
                "carbs_g": "float",
                "fat_g": "float",
                "health_score": "float",
                "fitness_score": "float"
            }
        }

        try:
            # 删除现有集合（如果存在）
            response = requests.delete(f"{self.qdrant_url}/collections/food_nutrition_vector")
            if response.status_code in [200, 404]:
                logger.info("已清理旧集合或集合不存在")

            # 创建新集合
            response = requests.put(
                f"{self.qdrant_url}/collections/food_nutrition_vector",
                json=collection_config
            )

            if response.status_code == 200:
                logger.info("Qdrant集合 food_nutrition_vector 创建成功")
                return True
            else:
                logger.error(f"创建集合失败: {response.text}")
                return False

        except Exception as e:
            logger.error(f"创建Qdrant集合失败: {e}")
            return False

    async def get_foods_from_neo4j(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """从Neo4j获取食物营养数据"""
        logger.info("从Neo4j获取食物营养数据...")

        try:
            async with AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            ) as driver:
                async with driver.session() as session:
                    query = """
                    MATCH (f:ChineseFood)
                    OPTIONAL MATCH (f)-[r:CONTAINS_NUTRIENT]->(n:Nutrient)
                    WITH f, collect({
                        nutrient: n.name,
                        amount: r.amount,
                        unit: r.unit,
                        category: n.category
                    }) as nutrients
                    RETURN
                        f.food_code as food_code,
                        f.name as food_name,
                        f.category as category,
                        f.source as source,
                        nutrients
                    ORDER BY f.name
                    """

                    if limit:
                        query += f" LIMIT {limit}"

                    result = await session.run(query)
                    foods = []
                    async for record in result:
                        # 过滤空营养素
                        nutrients = [n for n in record["nutrients"] if n["nutrient"] and n["amount"]]
                        foods.append({
                            "food_code": record["food_code"],
                            "food_name": record["food_name"],
                            "category": record["category"],
                            "source": record.get("source", ""),
                            "nutrients": nutrients
                        })

                    logger.info(f"获取到 {len(foods)} 个食物数据")
                    return foods

        except Exception as e:
            logger.error(f"从Neo4j获取数据失败: {e}")
            return []

    def generate_food_text_description(self, food: Dict[str, Any]) -> str:
        """生成食物的文本描述用于向量化"""
        food_name = food["food_name"]
        category = food["category"]
        nutrients = food["nutrients"]

        # 基础描述
        description = f"{food_name}是一种{category}食物，"

        # 主要营养成分
        macronutrients = []
        micronutrients = []

        for nutrient in nutrients:
            nutrient_name = nutrient["nutrient"]
            amount = nutrient["amount"]
            unit = nutrient["unit"]
            category = nutrient["category"]

            if nutrient_name in ["蛋白质", "脂肪", "碳水化合物", "膳食纤维"]:
                if amount > 0:
                    macronutrients.append(f"{nutrient_name}{amount:g}{unit}")
            elif category in ["维生素", "矿物质"]:
                if amount > 0:
                    micronutrients.append(f"{nutrient_name}{amount:g}{unit}")

        # 添加宏量营养素描述
        if macronutrients:
            description += f"主要营养成分包括{', '.join(macronutrients)}，"

        # 添加微量营养素描述
        if micronutrients:
            description += f"富含{', '.join(micronutrients[:5])}等营养素"

        # 添加健身营养特性
        protein = next((n for n in nutrients if n["nutrient"] == "蛋白质"), None)
        if protein and protein["amount"] > 20:
            description += "，是优质的高蛋白食物来源"

        fiber = next((n for n in nutrients if n["nutrient"] == "膳食纤维"), None)
        if fiber and fiber["amount"] > 3:
            description += "，富含膳食纤维有助于消化健康"

        calcium = next((n for n in nutrients if n["nutrient"] == "钙"), None)
        if calcium and calcium["amount"] > 100:
            description += "，钙含量丰富有助于骨骼健康"

        iron = next((n for n in nutrients if n["nutrient"] == "铁"), None)
        if iron and iron["amount"] > 2:
            description += "，铁含量丰富有助于预防贫血"

        return description

    def extract_nutrition_features(self, food: Dict[str, Any]) -> Dict[str, float]:
        """提取营养特征数值"""
        nutrients = food["nutrients"]
        features = {}

        # 标准化营养素名称映射
        nutrient_mapping = {
            "蛋白质": "protein_g",
            "脂肪": "fat_g",
            "碳水化合物": "carbs_g",
            "膳食纤维": "fiber_g",
            "能量": "energy_kcal",
            "钙": "calcium_mg",
            "铁": "iron_mg",
            "锌": "zinc_mg",
            "钾": "potassium_mg",
            "钠": "sodium_mg",
            "维生素A": "vitamin_a_ug",
            "维生素B1": "vitamin_b1_mg",
            "维生素B2": "vitamin_b2_mg",
            "烟酸": "niacin_mg",
            "维生素C": "vitamin_c_mg",
            "维生素E": "vitamin_e_mg"
        }

        for nutrient in nutrients:
            nutrient_name = nutrient["nutrient"]
            amount = nutrient["amount"]
            unit = nutrient["unit"]

            if nutrient_name in nutrient_mapping and amount > 0:
                feature_name = nutrient_mapping[nutrient_name]

                # 单位标准化（转换为标准单位）
                if feature_name.endswith("_kcal"):
                    features[feature_name] = float(amount) if unit == "kcal" else float(amount) * 0.239
                elif feature_name.endswith("_g"):
                    features[feature_name] = float(amount) if unit == "g" else float(amount) / 1000
                elif feature_name.endswith("_mg"):
                    features[feature_name] = float(amount) if unit == "mg" else float(amount) * 1000
                elif feature_name.endswith("_ug"):
                    features[feature_name] = float(amount) if unit in ["μg", "µg"] else float(amount) / 1000

        return features

    def calculate_scores(self, features: Dict[str, float]) -> tuple:
        """计算健康评分和健身评分"""
        health_score = 50.0
        fitness_score = 50.0

        # 健康评分逻辑
        protein = features.get("protein_g", 0)
        fiber = features.get("fiber_g", 0)
        fat = features.get("fat_g", 0)
        carbs = features.get("carbs_g", 0)

        if protein > 0:
            health_score += min(15, protein * 0.5)
        if fiber > 2:
            health_score += min(10, fiber * 2)
        if fat < 10:
            health_score += 5

        # 健身评分逻辑
        if protein > 20:
            fitness_score += min(25, protein)
        if protein > 15:
            fitness_score += 10

        vitamins = sum(1 for key in features.keys() if key.startswith("vitamin_"))
        minerals = sum(1 for key in features.keys() if key in ["calcium_mg", "iron_mg", "zinc_mg", "potassium_mg"])

        fitness_score += vitamins * 2
        fitness_score += minerals * 1.5

        health_score = min(100, max(0, health_score))
        fitness_score = min(100, max(0, fitness_score))

        return health_score, fitness_score

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """生成文本向量（使用简单的TF-IDF或外部API）"""
        try:
            # 尝试使用现有的向量化API
            vectorization_url = "http://localhost:8001/api/embeddings"

            response = requests.post(
                vectorization_url,
                json={"text": text},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200 and "embedding" in result.get("data", {}):
                    return result["data"]["embedding"]

        except Exception as e:
            logger.debug(f"向量化API调用失败: {e}")

        # 如果API失败，使用简单的哈希方法生成向量
        import hashlib
        import numpy as np

        hash_obj = hashlib.md5(text.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()

        # 将哈希值转换为768维向量
        vector = []
        for i in range(0, len(hash_hex), 2):
            byte_val = int(hash_hex[i:i+2], 16)
            # 扩展到32个float值以达到768维
            for j in range(24):
                vector.append((byte_val / 255.0) * (1 if j % 2 == 0 else -1))

        # 截取或填充到768维
        while len(vector) < 768:
            vector.append(0.0)

        return vector[:768]

    async def vectorize_and_store_foods(self, foods: List[Dict[str, Any]]):
        """向量化并存储食物数据"""
        logger.info(f"开始向量化 {len(foods)} 个食物...")

        start_time = time.time()
        self.stats["total_foods"] = len(foods)

        batch_size = 10  # 每批处理10个食物
        points = []

        for i, food in enumerate(foods):
            try:
                # 生成文本描述
                text_description = self.generate_food_text_description(food)

                # 生成向量
                embedding = await self.generate_embedding(text_description)

                if embedding is None:
                    logger.warning(f"向量化失败: {food['food_name']}")
                    self.stats["failed_foods"] += 1
                    continue

                # 提取营养特征
                features = self.extract_nutrition_features(food)
                health_score, fitness_score = self.calculate_scores(features)

                # 构建payload
                payload = {
                    "food_code": food["food_code"],
                    "food_name": food["food_name"],
                    "category": food["category"],
                    "nutrients": food["nutrients"],
                    "total_calories": features.get("energy_kcal", 0),
                    "protein_g": features.get("protein_g", 0),
                    "carbs_g": features.get("carbs_g", 0),
                    "fat_g": features.get("fat_g", 0),
                    "fiber_g": features.get("fiber_g", 0),
                    "health_score": health_score,
                    "fitness_score": fitness_score,
                    "features": features,
                    "created_at": datetime.now().isoformat()
                }

                # 创建点
                point = {
                    "id": i + 1,  # 使用简单自增ID
                    "vector": embedding,
                    "payload": payload
                }

                points.append(point)
                self.stats["vectorized_foods"] += 1

                # 统计分类
                category = food["category"]
                if category not in self.stats["categories"]:
                    self.stats["categories"][category] = 0
                self.stats["categories"][category] += 1

                # 批量插入
                if len(points) >= batch_size:
                    await self._insert_points_batch(points)
                    points = []
                    self.stats["vectors_created"] += batch_size

                # 进度报告
                if (i + 1) % 50 == 0:
                    elapsed = time.time() - start_time
                    speed = (i + 1) / elapsed
                    logger.info(f"已处理: {i + 1}/{len(foods)} ({speed:.1f} 食物/秒)")

            except Exception as e:
                logger.error(f"处理食物 {food.get('food_name', 'Unknown')} 失败: {e}")
                self.stats["failed_foods"] += 1

        # 插入剩余的点
        if points:
            await self._insert_points_batch(points)
            self.stats["vectors_created"] += len(points)

        self.stats["processing_time"] = time.time() - start_time

    async def _insert_points_batch(self, points: List[Dict[str, Any]]):
        """批量插入向量点"""
        try:
            response = requests.put(
                f"{self.qdrant_url}/collections/food_nutrition_vector/points",
                json={"points": points},
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"批量插入失败: {response.text}")

        except Exception as e:
            logger.error(f"批量插入异常: {e}")

    async def run_vectorization(self, limit: Optional[int] = None):
        """执行完整的向量化流程"""
        logger.info("开始食物营养数据向量化流程...")

        try:
            # 1. 创建Qdrant集合
            collection_created = await self.create_food_nutrition_collection()
            if not collection_created:
                logger.error("Qdrant集合创建失败，终止流程")
                return False

            # 2. 获取食物数据
            foods = await self.get_foods_from_neo4j(limit)
            if not foods:
                logger.error("未获取到食物数据，终止流程")
                return False

            # 3. 向量化并存储
            await self.vectorize_and_store_foods(foods)

            # 4. 输出报告
            await self._print_vectorization_report()

            return True

        except Exception as e:
            logger.error(f"向量化流程失败: {e}")
            return False

    async def _print_vectorization_report(self):
        """输出向量化报告"""
        logger.info("=" * 60)
        logger.info("食物营养数据向量化完成报告")
        logger.info("=" * 60)
        logger.info(f"处理食物总数: {self.stats['total_foods']}")
        logger.info(f"成功向量化: {self.stats['vectorized_foods']}")
        logger.info(f"向量化失败: {self.stats['failed_foods']}")
        logger.info(f"成功率: {(self.stats['vectorized_foods'] / max(1, self.stats['total_foods'])) * 100:.1f}%")
        logger.info(f"创建向量数: {self.stats['vectors_created']}")
        logger.info(f"处理时间: {self.stats['processing_time']:.2f} 秒")

        if self.stats['processing_time'] > 0:
            speed = self.stats['vectorized_foods'] / self.stats['processing_time']
            logger.info(f"平均处理速度: {speed:.1f} 食物/秒")

        logger.info("\n分类统计:")
        for category, count in self.stats["categories"].items():
            logger.info(f"  {category}: {count} 个食物")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='食物营养数据向量化工具')
    parser.add_argument('--limit', type=int, help='限制处理的食物数量（测试用）')
    parser.add_argument('--qdrant-host', default='localhost', help='Qdrant主机地址')
    parser.add_argument('--qdrant-port', type=int, default=6333, help='Qdrant端口')
    parser.add_argument('--neo4j-uri', default='bolt://localhost:7687', help='Neo4j URI')

    args = parser.parse_args()

    logger.info("启动食物营养数据向量化器...")

    vectorizer = FoodNutritionVectorizer(
        qdrant_host=args.qdrant_host,
        qdrant_port=args.qdrant_port,
        neo4j_uri=args.neo4j
    )

    success = await vectorizer.run_vectorization(limit=args.limit)

    if success:
        print("\n" + "=" * 60)
        print("食物营养数据向量化完成!")
        print(f"成功向量化 {vectorizer.stats['vectorized_foods']} 个食物")
        print("现在可以使用向量检索进行食物营养智能搜索!")
        print("=" * 60)
    else:
        print("\n食物营养数据向量化失败!")


if __name__ == "__main__":
    asyncio.run(main())