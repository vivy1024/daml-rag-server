#!/usr/bin/env python3
"""
批量导入中文营养数据到Neo4j
导入完整的4000+食物数据和营养成分
"""

import asyncio
import json
import logging
from pathlib import Path
from neo4j import AsyncGraphDatabase
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BatchNutritionImporter:
    """批量营养数据导入器"""

    def __init__(self,
                 neo4j_uri: str = "bolt://fitness_neo4j:7687",
                 neo4j_user: str = "neo4j",
                 neo4j_password: str = "build_body_2024"):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password

        # 导入统计
        self.stats = {
            "total_files": 0,
            "total_foods": 0,
            "imported_foods": 0,
            "failed_foods": 0,
            "created_relationships": 0,
            "processing_time": 0.0,
            "categories": {}
        }

        # 营养素映射
        self.nutrient_mapping = {
            # 基础营养成分
            "energyKCal": {"name": "能量", "unit": "kcal", "category": "基础"},
            "energyKJ": {"name": "能量", "unit": "kJ", "category": "基础"},
            "protein": {"name": "蛋白质", "unit": "g", "category": "基础"},
            "fat": {"name": "脂肪", "unit": "g", "category": "基础"},
            "CHO": {"name": "碳水化合物", "unit": "g", "category": "基础"},
            "dietaryFiber": {"name": "膳食纤维", "unit": "g", "category": "基础"},
            "water": {"name": "水分", "unit": "g", "category": "基础"},
            "ash": {"name": "灰分", "unit": "g", "category": "基础"},

            # 维生素
            "vitaminA": {"name": "维生素A", "unit": "μgRE", "category": "维生素"},
            "carotene": {"name": "胡萝卜素", "unit": "μg", "category": "维生素"},
            "retinol": {"name": "视黄醇", "unit": "μg", "category": "维生素"},
            "thiamin": {"name": "维生素B1", "unit": "mg", "category": "维生素"},
            "riboflavin": {"name": "维生素B2", "unit": "mg", "category": "维生素"},
            "niacin": {"name": "烟酸", "unit": "mg", "category": "维生素"},
            "vitaminC": {"name": "维生素C", "unit": "mg", "category": "维生素"},
            "vitaminETotal": {"name": "维生素E", "unit": "mg", "category": "维生素"},
            "vitaminE1": {"name": "维生素Eα", "unit": "mg", "category": "维生素"},
            "vitaminE2": {"name": "维生素Eγ", "unit": "mg", "category": "维生素"},
            "vitaminE3": {"name": "维生素Eδ", "unit": "mg", "category": "维生素"},

            # 矿物质
            "Ca": {"name": "钙", "unit": "mg", "category": "矿物质"},
            "P": {"name": "磷", "unit": "mg", "category": "矿物质"},
            "K": {"name": "钾", "unit": "mg", "category": "矿物质"},
            "Na": {"name": "钠", "unit": "mg", "category": "矿物质"},
            "Mg": {"name": "镁", "unit": "mg", "category": "矿物质"},
            "Fe": {"name": "铁", "unit": "mg", "category": "矿物质"},
            "Zn": {"name": "锌", "unit": "mg", "category": "矿物质"},
            "Se": {"name": "硒", "unit": "μg", "category": "矿物质"},
            "Cu": {"name": "铜", "unit": "mg", "category": "矿物质"},
            "Mn": {"name": "锰", "unit": "mg", "category": "矿物质"},

            # 其他成分
            "cholesterol": {"name": "胆固醇", "unit": "mg", "category": "其他"},
            "alcohol": {"name": "酒精", "unit": "g", "category": "其他"},
        }

    async def import_all_detailed_data(self):
        """导入所有详细营养数据"""
        start_time = time.time()
        logger.info("开始批量导入详细营养数据...")

        detailed_dir = Path("data/chinese-nutrition/detailed")

        if not detailed_dir.exists():
            logger.error(f"详细数据目录不存在: {detailed_dir}")
            return False

        try:
            async with AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            ) as driver:

                async with driver.session() as session:
                    # 1. 创建Schema
                    await self._create_schema(session)

                    # 2. 逐个处理JSON文件
                    json_files = list(detailed_dir.glob("*.json"))
                    self.stats["total_files"] = len(json_files)

                    logger.info(f"找到 {len(json_files)} 个JSON文件")

                    for i, json_file in enumerate(json_files, 1):
                        logger.info(f"处理文件 {i}/{len(json_files)}: {json_file.name}")

                        try:
                            await self._import_json_file(session, json_file)

                        except Exception as e:
                            logger.error(f"处理文件 {json_file.name} 失败: {e}")
                            continue

        except Exception as e:
            logger.error(f"批量导入失败: {e}")
            return False

        self.stats["processing_time"] = time.time() - start_time
        await self._print_import_report()

        return True

    async def _create_schema(self, session):
        """创建数据库Schema"""
        logger.info("创建Schema约束...")

        constraints = [
            "CREATE CONSTRAINT chinese_food_code_unique IF NOT EXISTS FOR (f:ChineseFood) REQUIRE f.food_code IS UNIQUE",
            "CREATE CONSTRAINT nutrient_name_unique IF NOT EXISTS FOR (n:Nutrient) REQUIRE n.name IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                await session.run(constraint)
                logger.info(f"创建约束: {constraint}")
            except Exception as e:
                logger.info(f"约束已存在: {e}")

        indexes = [
            "CREATE INDEX chinese_food_category_index IF NOT EXISTS FOR (f:ChineseFood) ON (f.category)",
            "CREATE INDEX nutrient_category_index IF NOT EXISTS FOR (n:Nutrient) ON (n.category)",
        ]

        for index in indexes:
            try:
                await session.run(index)
                logger.info(f"创建索引: {index}")
            except Exception as e:
                logger.info(f"索引创建跳过: {e}")

    async def _import_json_file(self, session, json_file: Path):
        """导入单个JSON文件"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                foods_data = json.load(f)

            if not isinstance(foods_data, list):
                logger.warning(f"文件 {json_file.name} 格式不是列表，跳过")
                return

            self.stats["total_foods"] += len(foods_data)

            # 从文件名推断分类
            category = self._infer_category_from_filename(json_file.name)
            self.stats["categories"][category] = 0

            logger.info(f"  食物数量: {len(foods_data)}, 分类: {category}")

            # 批量处理食物
            batch_size = 50  # 每批处理50个食物
            for i in range(0, len(foods_data), batch_size):
                batch = foods_data[i:i + batch_size]

                for food_data in batch:
                    try:
                        await self._import_single_food(session, food_data, category)
                        self.stats["imported_foods"] += 1
                        self.stats["categories"][category] += 1

                    except Exception as e:
                        logger.warning(f"  导入食物失败: {food_data.get('foodName', 'Unknown')} - {e}")
                        self.stats["failed_foods"] += 1

                # 每批处理短暂休息
                if i + batch_size < len(foods_data):
                    await asyncio.sleep(0.1)

                # 进度报告
                if (i + batch_size) % 200 == 0 or i + batch_size >= len(foods_data):
                    logger.info(f"  已处理: {min(i + batch_size, len(foods_data))}/{len(foods_data)}")

        except Exception as e:
            logger.error(f"读取文件 {json_file.name} 失败: {e}")
            raise

    async def _import_single_food(self, session, food_data: dict, category: str):
        """导入单个食物数据"""
        food_name = food_data.get("foodName", "")
        food_code = food_data.get("foodCode", "")
        edible = food_data.get("edible", "100")

        if not food_name or not food_code:
            raise ValueError(f"食物名称或代码缺失: {food_data}")

        # 创建食物节点
        await session.run('''
            MERGE (f:ChineseFood:Food {
                food_code: $food_code,
                name: $food_name,
                food_name: $food_name,
                category: $category,
                edible_part: $edible,
                source: "中国食物成分表详细版",
                data_type: "detailed",
                imported_at: $imported_at
            })
        ''',
        food_code=food_code,
        food_name=food_name,
        category=category,
        edible=edible,
        imported_at=datetime.now().isoformat())

        # 创建营养素关系
        created_relationships = 0

        for field_key, value in food_data.items():
            if field_key in self.nutrient_mapping and value is not None and value != '':
                nutrient_info = self.nutrient_mapping[field_key]

                # 解析数值
                amount = self._parse_nutrient_value(value)
                if amount is None:
                    continue

                # 创建或获取营养素节点
                await session.run('''
                    MERGE (n:Nutrient {
                        name: $nutrient_name,
                        category: $category
                    })
                    SET n.unit = $unit,
                        n.updated_at = $updated_at
                ''',
                nutrient_name=nutrient_info['name'],
                category=nutrient_info['category'],
                unit=nutrient_info['unit'],
                updated_at=datetime.now().isoformat())

                # 创建食物-营养素关系
                await session.run('''
                    MATCH (f:ChineseFood {food_code: $food_code})
                    MATCH (n:Nutrient {name: $nutrient_name})
                    MERGE (f)-[r:CONTAINS_NUTRIENT]->(n)
                    SET r.amount = $amount,
                        r.unit = $unit,
                        r.per_100g = true,
                        r.edible_part = $edible,
                        r.data_source = "中国食物成分表详细版",
                        r.raw_value = $raw_value
                ''',
                food_code=food_code,
                nutrient_name=nutrient_info['name'],
                amount=amount,
                unit=nutrient_info['unit'],
                edible=float(edible) if edible else 100.0,
                raw_value=str(value))

                created_relationships += 1

        self.stats["created_relationships"] += created_relationships

    def _infer_category_from_filename(self, filename: str) -> str:
        """从文件名推断食物分类"""
        filename_lower = filename.lower()

        if 'meat' in filename_lower or '畜肉类' in filename:
            return '畜肉类'
        elif 'poultry' in filename_lower or '禽肉类' in filename:
            return '禽肉类'
        elif 'dairy' in filename_lower or '乳类' in filename:
            return '乳类'
        elif 'egg' in filename_lower or '蛋类' in filename:
            return '蛋类'
        elif 'grain' in filename_lower or 'bean' in filename_lower or '谷类' in filename or '豆类' in filename:
            return '谷薯豆类'
        elif 'vegetable' in filename_lower or 'fruit' in filename_lower or '蔬菜' in filename or '水果' in filename:
            if '坚果' in filename:
                return '坚果种子类'
            return '蔬果类'
        elif 'infant' in filename_lower or '婴幼儿' in filename:
            return '婴幼儿食品'
        else:
            return '其他'

    def _parse_nutrient_value(self, value) -> float:
        """解析营养素数值"""
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            value = value.strip()
            if value == 'Tr':  # 痕量
                return 0.001
            elif value == '-' or value == '' or value == 'None':
                return None
            elif value.startswith('<'):
                # <0.01 这样的格式
                try:
                    return float(value[1:]) / 2
                except ValueError:
                    return None
            else:
                try:
                    return float(value)
                except ValueError:
                    return None

        return None

    async def _print_import_report(self):
        """输出导入报告"""
        logger.info("=" * 70)
        logger.info("批量营养数据导入完成报告")
        logger.info("=" * 70)
        logger.info(f"处理文件数: {self.stats['total_files']}")
        logger.info(f"总食物数量: {self.stats['total_foods']}")
        logger.info(f"成功导入: {self.stats['imported_foods']}")
        logger.info(f"导入失败: {self.stats['failed_foods']}")
        logger.info(f"成功导入率: {(self.stats['imported_foods'] / max(1, self.stats['total_foods'])) * 100:.1f}%")
        logger.info(f"创建关系数: {self.stats['created_relationships']}")
        logger.info(f"处理时间: {self.stats['processing_time']:.2f} 秒")

        if self.stats['processing_time'] > 0:
            speed = self.stats['imported_foods'] / self.stats['processing_time']
            logger.info(f"处理速度: {speed:.1f} 食物/秒")

        logger.info("\n分类统计:")
        for category, count in self.stats["categories"].items():
            logger.info(f"  {category}: {count} 个食物")

async def main():
    """主函数"""
    logger.info("启动批量营养数据导入器...")

    importer = BatchNutritionImporter()
    success = await importer.import_all_detailed_data()

    if success:
        print("\n✅ 批量营养数据导入成功!")
        print(f"成功导入 {importer.stats['imported_foods']} 个食物")
        print("营养知识图谱已大幅扩展!")
    else:
        print("\n❌ 批量营养数据导入失败!")

if __name__ == "__main__":
    asyncio.run(main())