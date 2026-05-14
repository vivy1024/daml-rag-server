#!/usr/bin/env python3
"""
营养知识向量化脚本
将中文营养知识生成向量并存储到Qdrant向量数据库

作者：BUILD_BODY Team
版本：v1.0.0
日期：2025-01-14
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
from datetime import datetime
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NutritionKnowledgeVectorizer:
    """营养知识向量化器"""

    def __init__(self,
                 qdrant_host: str = "fitness_qdrant",
                 qdrant_port: int = 6333,
                 collection_name: str = "nutrition_knowledge"):
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.collection_name = collection_name
        self.qdrant_url = f"http://{qdrant_host}:{qdrant_port}"

        # 向量化统计
        self.stats = {
            "total_texts": 0,
            "vectorized_texts": 0,
            "failed_texts": 0,
            "processing_time": 0.0,
            "categories": {}
        }

    def generate_nutrition_texts(self) -> List[Dict[str, Any]]:
        """生成营养知识文本集合"""
        logger.info("生成营养知识文本集合...")

        nutrition_texts = []

        # 1. 基础营养知识
        basic_nutrition = [
            {
                "text": "蛋白质是人体必需的宏量营养素，参与肌肉构建和修复，每克提供4千卡能量。健身人群需要1.6-2.2克蛋白质每公斤体重。",
                "category": "基础营养",
                "keywords": ["蛋白质", "宏量营养素", "肌肉构建", "修复", "能量"],
                "metadata": {"type": "basic_nutrition", "nutrient": "蛋白质"}
            },
            {
                "text": "碳水化合物是身体主要能量来源，提供4千卡每克。运动前后适量补充碳水有助于维持血糖水平和恢复体力。",
                "category": "基础营养",
                "keywords": ["碳水化合物", "能量", "血糖", "运动恢复", "运动前"],
                "metadata": {"type": "basic_nutrition", "nutrient": "碳水化合物"}
            },
            {
                "text": "脂肪提供9千卡每克能量，参与激素合成和脂溶性维生素吸收。健康脂肪包括橄榄油、坚果、鱼类中的不饱和脂肪。",
                "category": "基础营养",
                "keywords": ["脂肪", "能量", "激素", "维生素吸收", "不饱和脂肪"],
                "metadata": {"type": "basic_nutrition", "nutrient": "脂肪"}
            },
            {
                "text": "膳食纤维促进肠道健康，控制血糖和胆固醇。成年人每日建议摄入25-35克膳食纤维，来源于蔬菜、水果、全谷物。",
                "category": "基础营养",
                "keywords": ["膳食纤维", "肠道健康", "血糖", "胆固醇", "蔬菜水果"],
                "metadata": {"type": "basic_nutrition", "nutrient": "膳食纤维"}
            }
        ]

        # 2. 维生素知识
        vitamins = [
            {
                "text": "维生素B1（硫胺素）参与能量代谢，对神经系统功能重要。缺乏时可能导致疲劳和神经问题。全谷物、肉类中含量丰富。",
                "category": "维生素",
                "keywords": ["维生素B1", "硫胺素", "能量代谢", "神经系统", "全谷物"],
                "metadata": {"type": "vitamin", "vitamin": "维生素B1"}
            },
            {
                "text": "维生素B2（核黄素）参与能量产生和细胞呼吸。缺乏时可能引起口角炎、皮肤问题。奶制品、蛋类、绿叶蔬菜中含量高。",
                "category": "维生素",
                "keywords": ["维生素B2", "核黄素", "能量产生", "细胞呼吸", "奶制品"],
                "metadata": {"type": "vitamin", "vitamin": "维生素B2"}
            },
            {
                "text": "维生素C（抗坏血酸）是强抗氧化剂，增强免疫系统，促进胶原蛋白合成和铁吸收。柑橘类水果、奇异果含量丰富。",
                "category": "维生素",
                "keywords": ["维生素C", "抗坏血酸", "抗氧化", "免疫", "胶原蛋白"],
                "metadata": {"type": "vitamin", "vitamin": "维生素C"}
            },
            {
                "text": "维生素A维持视力健康，支持免疫系统，参与细胞分化。动物肝脏、胡萝卜、深绿色蔬菜含量丰富。",
                "category": "维生素",
                "keywords": ["维生素A", "视力", "免疫", "细胞分化", "胡萝卜"],
                "metadata": {"type": "vitamin", "vitamin": "维生素A"}
            },
            {
                "text": "叶酸（维生素B9）对DNA合成和细胞分裂至关重要，孕妇需要额外补充预防神经管缺陷。绿叶蔬菜、豆类中含量丰富。",
                "category": "维生素",
                "keywords": ["叶酸", "维生素B9", "DNA合成", "孕妇", "神经管缺陷"],
                "metadata": {"type": "vitamin", "vitamin": "叶酸"}
            }
        ]

        # 3. 矿物质知识
        minerals = [
            {
                "text": "钙是骨骼和牙齿的主要成分，参与肌肉收缩和神经传导。成年人每日需要1000-1200毫克，乳制品、豆制品中含量丰富。",
                "category": "矿物质",
                "keywords": ["钙", "骨骼", "牙齿", "肌肉收缩", "乳制品"],
                "metadata": {"type": "mineral", "mineral": "钙"}
            },
            {
                "text": "铁是血红蛋白的重要组成部分，参与氧气运输。缺乏时导致贫血，表现为疲劳、头晕。红肉、菠菜、豆类中含量丰富。",
                "category": "矿物质",
                "keywords": ["铁", "血红蛋白", "氧气运输", "贫血", "红肉"],
                "metadata": {"type": "mineral", "mineral": "铁"}
            },
            {
                "text": "锌参与免疫功能、蛋白质合成和伤口愈合。对运动员恢复和免疫系统健康重要。海鲜、肉类、坚果中含量丰富。",
                "category": "矿物质",
                "keywords": ["锌", "免疫功能", "蛋白质合成", "伤口愈合", "海鲜"],
                "metadata": {"type": "mineral", "mineral": "锌"}
            },
            {
                "text": "镁参与300多种酶反应，支持肌肉和神经功能，调节心率。坚果、全谷物、绿叶蔬菜中含量丰富。",
                "category": "矿物质",
                "keywords": ["镁", "酶反应", "肌肉功能", "神经功能", "坚果"],
                "metadata": {"type": "mineral", "mineral": "镁"}
            },
            {
                "text": "钾调节体液平衡，支持神经和肌肉功能，控制血压。香蕉、土豆、绿叶蔬菜中含量丰富。运动后补充钾有助于恢复。",
                "category": "矿物质",
                "keywords": ["钾", "体液平衡", "神经功能", "血压", "运动恢复"],
                "metadata": {"type": "mineral", "mineral": "钾"}
            }
        ]

        # 4. 健身营养应用
        fitness_nutrition = [
            {
                "text": "运动前营养策略：运动前2-3小时摄入适量碳水化合物，避免高脂肪和高纤维食物。运动前30分钟可补充少量易消化的碳水。",
                "category": "运动营养",
                "keywords": ["运动前", "碳水化合物", "消化", "能量准备", "时机"],
                "metadata": {"type": "sports_timing", "timing": "pre_workout"}
            },
            {
                "text": "运动后恢复营养：运动后30分钟内摄入碳水化合物和蛋白质比例3:1的食物，促进糖原合成和肌肉修复。乳清蛋白和香蕉是理想选择。",
                "category": "运动营养",
                "keywords": ["运动后", "恢复", "蛋白质", "肌肉修复", "糖原合成"],
                "metadata": {"type": "sports_timing", "timing": "post_workout"}
            },
            {
                "text": "增肌期营养需求：蛋白质摄入量1.6-2.2克/公斤体重，碳水化合物4-6克/公斤体重，适量健康脂肪。需要创造300-500千卡的热量盈余。",
                "category": "运动营养",
                "keywords": ["增肌", "蛋白质", "热量盈余", "肌肉合成", "营养需求"],
                "metadata": {"type": "sports_goal", "goal": "hypertrophy"}
            },
            {
                "text": "减脂期营养策略：创造500-750千卡的热量缺口，保持高蛋白质摄入1.6-2.2克/公斤体重防止肌肉流失。选择低热量密度的食物。",
                "category": "运动营养",
                "keywords": ["减脂", "热量缺口", "肌肉保护", "低热量密度", "高蛋白"],
                "metadata": {"type": "sports_goal", "goal": "fat_loss"}
            }
        ]

        # 5. 食物营养价值
        food_nutrition = [
            {
                "text": "鸡胸肉是优质蛋白质来源，脂肪含量低，每100克含蛋白质23.3克，脂肪1.2克。适合减脂和增肌期食用。",
                "category": "食物营养",
                "keywords": ["鸡胸肉", "蛋白质", "低脂肪", "禽肉", "健身食品"],
                "metadata": {"type": "food_analysis", "food": "鸡胸肉"}
            },
            {
                "text": "燕麦片富含复合碳水化合物和膳食纤维，提供持久能量。每100克含碳水化合物61.6克，膳食纤维5.3克，适合早餐和运动前。",
                "category": "食物营养",
                "keywords": ["燕麦片", "复合碳水", "膳食纤维", "能量", "早餐"],
                "metadata": {"type": "food_analysis", "food": "燕麦片"}
            },
            {
                "text": "西兰花营养丰富，富含维生素C、膳食纤维和抗氧化物质，热量低。每100克含25千卡，维生素C51毫克，适合减脂期食用。",
                "category": "食物营养",
                "keywords": ["西兰花", "维生素C", "膳食纤维", "低热量", "抗氧化"],
                "metadata": {"type": "food_analysis", "food": "西兰花"}
            },
            {
                "text": "鸡蛋含有完全蛋白质，营养吸收率高。每个大鸡蛋含蛋白质6克，生物素含量丰富，适合任何健身阶段。",
                "category": "食物营养",
                "keywords": ["鸡蛋", "完全蛋白质", "生物素", "营养吸收", "性价比"],
                "metadata": {"type": "food_analysis", "food": "鸡蛋"}
            },
            {
                "text": "牛奶提供优质蛋白质和钙，支持骨骼健康。每100毫升含蛋白质3.0克，钙104毫克，适合运动后恢复。",
                "category": "食物营养",
                "keywords": ["牛奶", "蛋白质", "钙", "骨骼健康", "运动恢复"],
                "metadata": {"type": "food_analysis", "food": "牛奶"}
            }
        ]

        # 6. 营养补充剂
        supplements = [
            {
                "text": "乳清蛋白粉吸收速度快，支链氨基酸含量高，适合运动后快速补充。建议运动后30分钟内摄入20-30克。",
                "category": "营养补充",
                "keywords": ["乳清蛋白", "支链氨基酸", "运动恢复", "快速吸收", "运动后"],
                "metadata": {"type": "supplement", "supplement": "乳清蛋白"}
            },
            {
                "text": "肌酸增加力量和肌肉爆发力，提高训练表现。每日5克，连续使用4-6周后休息2-4周。需要充足水分配合。",
                "category": "营养补充",
                "keywords": ["肌酸", "力量", "肌肉爆发力", "训练表现", "水分"],
                "metadata": {"type": "supplement", "supplement": "肌酸"}
            },
            {
                "text": "欧米茄-3脂肪酸（鱼油）减少炎症反应，促进恢复，支持心血管健康。每日摄入1-3克EPA和DHA。",
                "category": "营养补充",
                "keywords": ["欧米茄-3", "鱼油", "抗炎", "恢复", "心血管健康"],
                "metadata": {"type": "supplement", "supplement": "欧米茄-3"}
            }
        ]

        # 7. 特殊人群营养
        special_populations = [
            {
                "text": "素食主义者需要特别注意维生素B12、铁、锌、钙和蛋白质的摄入。豆类、坚果、全谷物可以提供优质蛋白质，需要维生素B12补充剂。",
                "category": "特殊人群",
                "keywords": ["素食", "维生素B12", "铁", "蛋白质", "营养补充"],
                "metadata": {"type": "special_group", "group": "vegetarian"}
            },
            {
                "text": "老年人营养需求特点：需要更多蛋白质维持肌肉量，钙和维生素D预防骨质疏松，维生素B12预防贫血。食物要易消化吸收。",
                "category": "特殊人群",
                "keywords": ["老年人", "肌肉量", "骨质疏松", "易消化", "营养需求"],
                "metadata": {"type": "special_group", "group": "elderly"}
            },
            {
                "text": "青少年运动营养需求：生长发育期需要充足能量和营养素，蛋白质1.2-1.4克/公斤体重，钙1300毫克/日，铁摄入量增加。",
                "category": "特殊人群",
                "keywords": ["青少年", "生长发育", "能量需求", "钙需求", "运动营养"],
                "metadata": {"type": "special_group", "group": "adolescent"}
            }
        ]

        # 合并所有文本
        nutrition_texts = (
            basic_nutrition + vitamins + minerals + fitness_nutrition +
            food_nutrition + supplements + special_populations
        )

        logger.info(f"生成了 {len(nutrition_texts)} 条营养知识文本")
        return nutrition_texts

    async def create_qdrant_collection(self, vector_size: int = 1024):
        """创建Qdrant向量集合"""
        logger.info(f"创建Qdrant集合: {self.collection_name}")

        collection_config = {
            "vectors": {
                "size": vector_size,
                "distance": "Cosine"
            },
            "payload_schema": {
                "text": "text",
                "category": "keyword",
                "keywords": "keyword",
                "metadata": "json"
            }
        }

        try:
            # 删除现有集合
            response = requests.delete(f"{self.qdrant_url}/collections/{self.collection_name}")
            if response.status_code in [200, 404]:
                logger.info("已清理旧集合或集合不存在")

            # 创建新集合
            response = requests.put(
                f"{self.qdrant_url}/collections/{self.collection_name}",
                json=collection_config
            )

            if response.status_code == 200:
                logger.info(f"Qdrant集合 {self.collection_name} 创建成功")
                return True
            else:
                logger.error(f"创建集合失败: {response.text}")
                return False

        except Exception as e:
            logger.error(f"创建Qdrant集合失败: {e}")
            return False

    async def vectorize_and_store_texts(self, texts: List[Dict[str, Any]]):
        """向量化并存储文本到Qdrant"""
        logger.info(f"开始向量化 {len(texts)} 条文本...")

        start_time = time.time()

        try:
            # 使用现有的DAML-RAG向量化服务
            vectorization_url = "http://localhost:8001/api/embeddings"

            processed_count = 0
            failed_count = 0

            for i, text_item in enumerate(texts):
                try:
                    # 调用向量化API
                    response = requests.post(
                        vectorization_url,
                        json={"text": text_item["text"]},
                        timeout=30
                    )

                    if response.status_code == 200:
                        result = response.json()
                        if result.get("code") == 200 and "embedding" in result.get("data", {}):
                            vector = result["data"]["embedding"]

                            # 存储到Qdrant
                            point_id = processed_count + 1
                            payload = {
                                "text": text_item["text"],
                                "category": text_item["category"],
                                "keywords": text_item["keywords"],
                                "metadata": text_item["metadata"],
                                "created_at": datetime.now().isoformat()
                            }

                            point = {
                                "id": point_id,
                                "vector": vector,
                                "payload": payload
                            }

                            # 插入向量
                            insert_response = requests.put(
                                f"{self.qdrant_url}/collections/{self.collection_name}/points",
                                json={"points": [point]}
                            )

                            if insert_response.status_code == 200:
                                processed_count += 1
                                self.stats["categories"][text_item["category"]] = \
                                    self.stats["categories"].get(text_item["category"], 0) + 1

                                if (i + 1) % 5 == 0:
                                    logger.info(f"已处理: {i + 1}/{len(texts)}")
                            else:
                                logger.warning(f"向量存储失败: {insert_response.text}")
                                failed_count += 1
                        else:
                            logger.warning(f"向量化失败: {result}")
                            failed_count += 1
                    else:
                        logger.warning(f"向量化API调用失败: {response.status_code}")
                        failed_count += 1

                except Exception as e:
                    logger.error(f"处理文本 {i} 失败: {e}")
                    failed_count += 1

            self.stats["total_texts"] = len(texts)
            self.stats["vectorized_texts"] = processed_count
            self.stats["failed_texts"] = failed_count
            self.stats["processing_time"] = time.time() - start_time

            logger.info(f"向量化完成: 成功 {processed_count}, 失败 {failed_count}")
            logger.info(f"处理时间: {self.stats['processing_time']:.2f} 秒")

            return processed_count > 0

        except Exception as e:
            logger.error(f"向量化过程失败: {e}")
            return False

    async def run_vectorization(self):
        """执行完整的向量化流程"""
        logger.info("开始营养知识向量化流程...")

        # 1. 生成文本
        nutrition_texts = self.generate_nutrition_texts()

        # 2. 创建Qdrant集合
        collection_created = await self.create_qdrant_collection()
        if not collection_created:
            logger.error("Qdrant集合创建失败，终止流程")
            return False

        # 3. 向量化并存储
        success = await self.vectorize_and_store_texts(nutrition_texts)

        if success:
            await self._print_vectorization_report()
        else:
            logger.error("向量化流程失败")

        return success

    async def _print_vectorization_report(self):
        """输出向量化报告"""
        logger.info("=" * 60)
        logger.info("营养知识向量化完成报告")
        logger.info("=" * 60)
        logger.info(f"总文本数: {self.stats['total_texts']}")
        logger.info(f"向量化成功: {self.stats['vectorized_texts']}")
        logger.info(f"向量化失败: {self.stats['failed_texts']}")
        logger.info(f"成功率: {(self.stats['vectorized_texts'] / max(1, self.stats['total_texts'])) * 100:.1f}%")
        logger.info(f"处理时间: {self.stats['processing_time']:.2f} 秒")
        logger.info(f"平均处理速度: {self.stats['total_texts'] / max(1, self.stats['processing_time']):.1f} 条/秒")

        logger.info("\n分类统计:")
        for category, count in self.stats["categories"].items():
            logger.info(f"  {category}: {count} 条")

async def main():
    """主函数"""
    logger.info("启动营养知识向量化器...")

    vectorizer = NutritionKnowledgeVectorizer()
    success = await vectorizer.run_vectorization()

    if success:
        print("✅ 营养知识向量化完成!")
        print("现在可以使用营养知识进行智能检索和推荐了。")
    else:
        print("❌ 营养知识向量化失败!")

if __name__ == "__main__":
    asyncio.run(main())