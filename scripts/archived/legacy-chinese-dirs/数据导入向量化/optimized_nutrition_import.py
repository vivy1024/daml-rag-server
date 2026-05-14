#!/usr/bin/env python3
"""
优化的完整营养数据导入脚本
分批高效导入1851个食物数据，建立完整营养关系网络

作者：BUILD_BODY Team
版本：v2.0.0
日期：2025-11-14
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from neo4j import AsyncGraphDatabase
import time
from dataclasses import dataclass
from datetime import datetime
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ImportStats:
    """导入统计"""
    processed_files: int = 0
    total_foods: int = 0
    imported_foods: int = 0
    failed_foods: int = 0
    created_nutrients: int = 0
    created_relationships: int = 0
    errors: int = 0
    start_time: float = 0.0

class OptimizedNutritionImporter:
    """优化的营养数据导入器"""

    def __init__(self):
        self.stats = ImportStats()
        self.stats.start_time = time.time()

        # 营养素映射表（完整版）
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

    async def create_optimized_schema(self, session):
        """创建优化的数据库Schema"""
        logger.info("创建优化的Schema...")

        # 创建约束
        constraints = [
            "CREATE CONSTRAINT food_code_unique IF NOT EXISTS FOR (f:ChineseFood) REQUIRE f.food_code IS UNIQUE",
            "CREATE CONSTRAINT nutrient_name_unique IF NOT EXISTS FOR (n:Nutrient) REQUIRE n.name IS UNIQUE",
        ]

        for constraint in constraints:
            try:
                await session.run(constraint)
                logger.info(f"创建约束: {constraint}")
            except Exception as e:
                logger.debug(f"约束已存在: {e}")

        # 创建索引
        indexes = [
            "CREATE INDEX chinese_food_name_index IF NOT EXISTS FOR (f:ChineseFood) ON (f.name)",
            "CREATE INDEX chinese_food_category_index IF NOT EXISTS FOR (f:ChineseFood) ON (f.category)",
            "CREATE INDEX nutrient_category_index IF NOT EXISTS FOR (n:Nutrient) ON (n.category)",
        ]

        for index in indexes:
            try:
                await session.run(index)
                logger.info(f"创建索引: {index}")
            except Exception as e:
                logger.debug(f"索引创建跳过: {e}")

    async def import_all_files_optimized(self):
        """优化的批量导入所有文件"""
        logger.info("开始优化批量导入...")

        archive_dir = Path("mcp-servers/archive/data")
        if not archive_dir.exists():
            logger.error(f"数据目录不存在: {archive_dir}")
            return False

        json_files = list(archive_dir.glob("merged_*.json"))
        logger.info(f"找到 {len(json_files)} 个JSON文件")

        try:
            async with AsyncGraphDatabase.driver(
                "bolt://localhost:7687",
                auth=("neo4j", "build_body_2024")
            ) as driver:
                async with driver.session() as session:
                    # 创建Schema
                    await self.create_optimized_schema(session)

                    # 分批处理文件
                    batch_size = 5  # 每批处理5个文件
                    for i in range(0, len(json_files), batch_size):
                        batch_files = json_files[i:i + batch_size]
                        logger.info(f"处理批次 {i//batch_size + 1}/{(len(json_files)-1)//batch_size + 1}")

                        for json_file in batch_files:
                            try:
                                await self._import_single_file_optimized(session, json_file)
                                self.stats.processed_files += 1

                                # 每个文件后短暂休息
                                await asyncio.sleep(0.1)

                            except Exception as e:
                                logger.error(f"处理文件 {json_file.name} 失败: {e}")
                                self.stats.errors += 1
                                continue

                        # 每批次后报告进度
                        self._print_progress()

                        # 批次间休息
                        if i + batch_size < len(json_files):
                            await asyncio.sleep(0.5)

                    # 创建营养素分类统计
                    await self._create_nutrient_category_summary(session)

        except Exception as e:
            logger.error(f"导入过程失败: {e}")
            return False

        self._print_final_report()
        return True

    async def _import_single_file_optimized(self, session, json_file: Path):
        """优化的单文件导入"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                foods = json.load(f)

            if not isinstance(foods, list):
                logger.warning(f"文件 {json_file.name} 格式不是列表")
                return

            self.stats.total_foods += len(foods)
            category = self._infer_category_from_filename(json_file.name)

            # 小批量处理食物
            mini_batch = 10  # 每次处理10个食物
            for i in range(0, len(foods), mini_batch):
                batch = foods[i:i + mini_batch]

                for food_data in batch:
                    try:
                        await self._import_food_optimized(session, food_data, category)
                        self.stats.imported_foods += 1
                    except Exception as e:
                        logger.debug(f"导入食物失败: {food_data.get('foodName', 'Unknown')} - {e}")
                        self.stats.failed_foods += 1

                # 小批次间休息
                if i + mini_batch < len(foods):
                    await asyncio.sleep(0.01)

        except Exception as e:
            logger.error(f"读取文件 {json_file.name} 失败: {e}")
            raise

    async def _import_food_optimized(self, session, food_data: Dict[str, Any], category: str):
        """优化的单个食物导入"""
        food_name = food_data.get("foodName", "")
        food_code = food_data.get("foodCode", "")
        edible = food_data.get("edible", "100")

        if not food_name or not food_code:
            return

        # 创建食物节点（使用MERGE避免重复）
        await session.run('''
            MERGE (f:ChineseFood:Food {food_code: $food_code})
            SET f.name = $food_name,
                f.food_name = $food_name,
                f.category = $category,
                f.edible_part = $edible,
                f.source = "中国食物成分表完整版",
                f.data_type = "complete",
                f.imported_at = $imported_at
        ''',
        food_code=food_code,
        food_name=food_name,
        category=category,
        edible=edible,
        imported_at=datetime.now().isoformat())

        # 批量创建营养素关系
        nutrients_to_create = []

        for field_key, value in food_data.items():
            if field_key in self.nutrient_mapping and value is not None and value != '':
                amount = self._parse_nutrient_value(value)
                if amount is not None:
                    nutrient_info = self.nutrient_mapping[field_key]
                    nutrients_to_create.append({
                        'name': nutrient_info['name'],
                        'category': nutrient_info['category'],
                        'unit': nutrient_info['unit'],
                        'amount': amount,
                        'raw_value': str(value)
                    })

        # 批量创建营养素关系
        for nutrient in nutrients_to_create:
            await session.run('''
                MERGE (n:Nutrient {name: $nutrient_name})
                SET n.category = $category, n.unit = $unit
                WITH n
                MATCH (f:ChineseFood {food_code: $food_code})
                MERGE (f)-[r:CONTAINS_NUTRIENT]->(n)
                SET r.amount = $amount,
                    r.unit = $unit,
                    r.per_100g = true,
                    r.edible_part = $edible,
                    r.raw_value = $raw_value,
                    r.data_source = "中国食物成分表完整版"
            ''',
            food_code=food_code,
            nutrient_name=nutrient['name'],
            category=nutrient['category'],
            unit=nutrient['unit'],
            amount=nutrient['amount'],
            edible=float(edible),
            raw_value=nutrient['raw_value'])

            self.stats.created_relationships += 1

    def _infer_category_from_filename(self, filename: str) -> str:
        """从文件名推断食物分类"""
        filename_lower = filename.lower()

        if '畜肉类' in filename_lower:
            return '畜肉类'
        elif '禽肉类' in filename_lower:
            return '禽肉类'
        elif '乳类' in filename_lower:
            return '乳类'
        elif '蛋类' in filename_lower:
            return '蛋类'
        elif '谷类' in filename_lower or '干豆类' in filename_lower:
            return '谷豆类'
        elif '蔬菜类' in filename_lower:
            return '蔬菜类'
        elif '水果类' in filename_lower:
            return '水果类'
        elif '坚果种子类' in filename_lower:
            return '坚果类'
        elif '鱼虾蟹贝类' in filename_lower:
            return '水产类'
        elif '婴幼儿食品' in filename_lower:
            return '婴幼儿食品'
        elif '植物油' in filename_lower or '动物油脂' in filename_lower:
            return '油脂类'
        else:
            return '其他'

    def _parse_nutrient_value(self, value) -> Optional[float]:
        """解析营养素数值"""
        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            value = value.strip()
            if value == 'Tr':  # 痕量
                return 0.001
            elif value in ['-', '', 'None']:
                return None
            elif value.startswith('<'):
                try:
                    return float(value[1:]) / 2
                except:
                    return None
            else:
                try:
                    return float(value)
                except:
                    return None

        return None

    async def _create_nutrient_category_summary(self, session):
        """创建营养素分类统计"""
        logger.info("创建营养素分类统计...")

        await session.run('''
            MATCH (n:Nutrient)
            WITH n.category as category,
                 collect(n.name) as nutrients,
                 collect(n.unit) as units
            MERGE (c:NutrientCategory {name: category})
            SET c.nutrient_count = size(nutrients),
                c.nutrients = nutrients,
                c.units = units,
                c.updated_at = $timestamp
        ''', timestamp=datetime.now().isoformat())

    def _print_progress(self):
        """打印进度"""
        elapsed = time.time() - self.stats.start_time
        progress = (self.stats.processed_files / 75) * 100  # 假设总共75个文件

        logger.info(f"进度: {progress:.1f}% ({self.stats.processed_files}/75 文件)")
        logger.info(f"已导入: {self.stats.imported_foods} 个食物, {self.stats.created_relationships} 个关系")
        logger.info(f"耗时: {elapsed:.1f}秒")

    def _print_final_report(self):
        """打印最终报告"""
        elapsed = time.time() - self.stats.start_time

        logger.info("=" * 70)
        logger.info("完整营养数据导入完成报告")
        logger.info("=" * 70)
        logger.info(f"处理文件数: {self.stats.processed_files}")
        logger.info(f"总食物数量: {self.stats.total_foods}")
        logger.info(f"成功导入: {self.stats.imported_foods}")
        logger.info(f"导入失败: {self.stats.failed_foods}")
        logger.info(f"成功率: {(self.stats.imported_foods / max(1, self.stats.total_foods)) * 100:.1f}%")
        logger.info(f"创建关系数: {self.stats.created_relationships}")
        logger.info(f"总耗时: {elapsed:.1f}秒")

        if self.stats.imported_foods > 0:
            speed = self.stats.imported_foods / elapsed
            logger.info(f"平均速度: {speed:.1f} 食物/秒")

async def main():
    """主函数"""
    logger.info("启动优化营养数据导入器...")

    importer = OptimizedNutritionImporter()
    success = await importer.import_all_files_optimized()

    if success:
        print("\\n" + "=" * 60)
        print("✅ 完整营养数据导入成功!")
        print(f"成功导入 {importer.stats.imported_foods} 个食物")
        print(f"建立 {importer.stats.created_relationships} 个营养关系")
        print("营养知识图谱现已大幅扩展!")
        print("=" * 60)
    else:
        print("\\n❌ 营养数据导入失败!")

if __name__ == "__main__":
    asyncio.run(main())