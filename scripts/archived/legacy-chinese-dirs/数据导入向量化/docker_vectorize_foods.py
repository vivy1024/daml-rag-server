#!/usr/bin/env python3
"""
Docker环境下食物营养数据向量化脚本
在Docker容器中执行，访问Qdrant和Neo4j服务

此脚本将被复制到Docker容器中执行
"""

import asyncio
import json
import logging
import requests
from neo4j import AsyncGraphDatabase
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Docker环境下的服务地址
QDRANT_URL = "http://fitness_qdrant:6333"
NEO4J_URI = "bolt://fitness_neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"


class DockerFoodVectorizer:
    """Docker环境下的食物向量化器"""

    def __init__(self):
        self.stats = {
            "total_foods": 0,
            "vectorized_foods": 0,
            "failed_foods": 0,
            "processing_time": 0.0,
            "categories": {}
        }

    async def create_collection(self):
        """创建Qdrant集合"""
        logger.info("创建 food_nutrition_vector 集合...")

        collection_config = {
            "vectors": {
                "size": 768,
                "distance": "Cosine"
            },
            "payload_schema": {
                "food_code": "keyword",
                "food_name": "text",
                "category": "keyword",
                "total_calories": "float",
                "protein_g": "float",
                "carbs_g": "float",
                "fat_g": "float",
                "health_score": "float",
                "fitness_score": "float"
            }
        }

        try:
            # 删除旧集合
            requests.delete(f"{QDRANT_URL}/collections/food_nutrition_vector", timeout=10)

            # 创建新集合
            response = requests.put(
                f"{QDRANT_URL}/collections/food_nutrition_vector",
                json=collection_config,
                timeout=10
            )

            if response.status_code == 200:
                logger.info("Qdrant集合创建成功")
                return True
            else:
                logger.error(f"集合创建失败: {response.text}")
                return False

        except Exception as e:
            logger.error(f"创建集合异常: {e}")
            return False

    async def get_foods_data(self):
        """从Neo4j获取食物数据"""
        logger.info("从Neo4j获取食物数据...")

        try:
            async with AsyncGraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            ) as driver:
                async with driver.session() as session:
                    query = """
                    MATCH (f:ChineseFood)
                    OPTIONAL MATCH (f)-[r:CONTAINS_NUTRIENT]->(n:Nutrient)
                    WITH f, collect({
                        nutrient: n.name,
                        amount: r.amount,
                        unit: r.unit
                    }) as nutrients
                    RETURN
                        f.food_code as food_code,
                        f.name as food_name,
                        f.category as category,
                        nutrients
                    LIMIT 500  # 先处理500个进行测试
                    """

                    result = await session.run(query)
                    foods = []
                    async for record in result:
                        # 过滤有效营养素
                        valid_nutrients = [
                            n for n in record["nutrients"]
                            if n["nutrient"] and n["amount"] and n["amount"] > 0
                        ]
                        foods.append({
                            "food_code": record["food_code"],
                            "food_name": record["food_name"],
                            "category": record["category"],
                            "nutrients": valid_nutrients
                        })

                    logger.info(f"获取到 {len(foods)} 个食物数据")
                    return foods

        except Exception as e:
            logger.error(f"获取Neo4j数据失败: {e}")
            return []

    def generate_food_description(self, food):
        """生成食物描述"""
        name = food["food_name"]
        category = food["category"]
        nutrients = food["nutrients"]

        desc = f"{name}是{category}食物，"

        # 主要营养成分
        main_nutrients = []
        for nutrient in nutrients[:8]:  # 只取前8个主要营养素
            amount = nutrient["amount"]
            unit = nutrient["unit"]
            nutrient_name = nutrient["nutrient"]
            if amount > 0:
                main_nutrients.append(f"{nutrient_name}{amount:g}{unit}")

        if main_nutrients:
            desc += f"含有{', '.join(main_nutrients)}"

        # 健康特性
        protein = next((n for n in nutrients if n["nutrient"] == "蛋白质"), None)
        if protein and protein["amount"] > 20:
            desc += "，是高蛋白食物"

        fiber = next((n for n in nutrients if n["nutrient"] == "膳食纤维"), None)
        if fiber and fiber["amount"] > 3:
            desc += "，富含膳食纤维"

        return desc

    def generate_simple_vector(self, text):
        """生成简单的768维向量"""
        import hashlib
        import numpy as np

        # 使用文本哈希生成确定性的向量
        hash_obj = hashlib.sha256(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()

        # 转换为768维float向量
        vector = []
        for i, byte_val in enumerate(hash_bytes):
            # 每个字节扩展为3个float值
            base_val = byte_val / 255.0
            vector.extend([
                base_val,
                base_val * 0.7,
                base_val * 0.3
            ])

            if len(vector) >= 768:
                break

        # 填充到768维
        while len(vector) < 768:
            vector.append(0.0)

        return vector[:768]

    def calculate_scores(self, food):
        """计算健康和健身评分"""
        nutrients = food["nutrients"]

        # 提取主要营养素
        protein = 0
        fat = 0
        carbs = 0
        fiber = 0

        for nutrient in nutrients:
            name = nutrient["nutrient"]
            amount = nutrient["amount"]

            if name == "蛋白质":
                protein = amount
            elif name == "脂肪":
                fat = amount
            elif name == "碳水化合物":
                carbs = amount
            elif name == "膳食纤维":
                fiber = amount

        # 健康评分
        health_score = 50
        if protein > 15:
            health_score += min(20, protein)
        if fiber > 3:
            health_score += min(15, fiber * 3)
        if fat < 10:
            health_score += 10

        # 健身评分
        fitness_score = 50
        if protein > 20:
            fitness_score += min(30, protein * 1.5)
        if protein > 10:
            fitness_score += 10

        health_score = min(100, max(0, health_score))
        fitness_score = min(100, max(0, fitness_score))

        return health_score, fitness_score

    async def vectorize_foods(self, foods):
        """向量化食物数据"""
        logger.info(f"开始向量化 {len(foods)} 个食物...")

        start_time = time.time()
        self.stats["total_foods"] = len(foods)

        points = []
        batch_size = 20

        for i, food in enumerate(foods):
            try:
                # 生成描述
                description = self.generate_food_description(food)

                # 生成向量
                vector = self.generate_simple_vector(description)

                # 计算评分
                health_score, fitness_score = self.calculate_scores(food)

                # 计算总热量
                energy = next((n["amount"] for n in food["nutrients"] if n["nutrient"] == "能量"), 0)

                # 构建payload
                payload = {
                    "food_code": food["food_code"],
                    "food_name": food["food_name"],
                    "category": food["category"],
                    "total_calories": energy,
                    "protein_g": next((n["amount"] for n in food["nutrients"] if n["nutrient"] == "蛋白质"), 0),
                    "carbs_g": next((n["amount"] for n in food["nutrients"] if n["nutrient"] == "碳水化合物"), 0),
                    "fat_g": next((n["amount"] for n in food["nutrients"] if n["nutrient"] == "脂肪"), 0),
                    "health_score": health_score,
                    "fitness_score": fitness_score,
                    "created_at": datetime.now().isoformat()
                }

                # 创建点
                point = {
                    "id": i + 1,
                    "vector": vector,
                    "payload": payload
                }

                points.append(point)
                self.stats["vectorized_foods"] += 1

                # 统计分类
                category = food["category"]
                self.stats["categories"][category] = self.stats["categories"].get(category, 0) + 1

                # 批量插入
                if len(points) >= batch_size:
                    await self._insert_batch(points)
                    points = []

                # 进度报告
                if (i + 1) % 100 == 0:
                    logger.info(f"已处理: {i + 1}/{len(foods)}")

            except Exception as e:
                logger.error(f"处理食物失败: {e}")
                self.stats["failed_foods"] += 1

        # 插入剩余点
        if points:
            await self._insert_batch(points)

        self.stats["processing_time"] = time.time() - start_time

    async def _insert_batch(self, points):
        """批量插入向量点"""
        try:
            response = requests.put(
                f"{QDRANT_URL}/collections/food_nutrition_vector/points",
                json={"points": points},
                timeout=30
            )
            if response.status_code != 200:
                logger.error(f"批量插入失败: {response.text}")
        except Exception as e:
            logger.error(f"批量插入异常: {e}")

    async def run_vectorization(self):
        """执行完整流程"""
        logger.info("开始Docker环境下的食物向量化...")

        # 1. 创建集合
        if not await self.create_collection():
            return False

        # 2. 获取数据
        foods = await self.get_foods_data()
        if not foods:
            logger.error("未获取到食物数据")
            return False

        # 3. 向量化
        await self.vectorize_foods(foods)

        # 4. 输出报告
        self._print_report()
        return True

    def _print_report(self):
        """打印报告"""
        logger.info("=" * 50)
        logger.info("食物向量化完成")
        logger.info("=" * 50)
        logger.info(f"总食物数: {self.stats['total_foods']}")
        logger.info(f"成功向量化: {self.stats['vectorized_foods']}")
        logger.info(f"失败数量: {self.stats['failed_foods']}")
        logger.info(f"处理时间: {self.stats['processing_time']:.2f}秒")

        if self.stats['processing_time'] > 0:
            speed = self.stats['vectorized_foods'] / self.stats['processing_time']
            logger.info(f"处理速度: {speed:.1f} 食物/秒")

        logger.info("分类统计:")
        for category, count in self.stats["categories"].items():
            logger.info(f"  {category}: {count}")


async def main():
    """主函数"""
    vectorizer = DockerFoodVectorizer()
    success = await vectorizer.run_vectorization()

    if success:
        print("\n✅ Docker环境食物向量化完成!")
        print(f"成功处理 {vectorizer.stats['vectorized_foods']} 个食物")
    else:
        print("\n❌ 向量化失败!")


if __name__ == "__main__":
    asyncio.run(main())