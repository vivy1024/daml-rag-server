"""
Food节点数据补充器

功能：
1. 补充血糖指数 (glycemic_index)
2. 补充血糖负荷 (glycemic_load)
3. 补充消化时间 (digestion_time_minutes)
4. 补充过敏原信息 (allergens)

作者：薛小川
日期：2025-12-15
"""

import json
import logging
import os
import time
from typing import Dict, List
from neo4j import AsyncDriver

from .models import SupplementResult

logger = logging.getLogger(__name__)


class FoodSupplementer:
    """Food节点补充器"""
    
    def __init__(self, neo4j_driver: AsyncDriver):
        """
        初始化补充器
        
        Args:
            neo4j_driver: Neo4j异步驱动
        """
        self.driver = neo4j_driver
        self.gi_data = self._load_gi_data()
        self.allergen_data = self._load_allergen_data()
    
    def _load_gi_data(self) -> Dict[str, float]:
        """
        加载血糖指数映射表（从JSON文件）
        
        Returns:
            Dict[str, float]: 食物名称到GI值的映射
        """
        gi_mapping = {}
        
        # 获取JSON文件路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, '..', '..', '..', '..', 'data', 'nutrition', 'core', 'glycemic_index_of_foods.json')
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                gi_data = json.load(f)
            
            # 解析JSON数据，构建食物名称到GI值的映射
            for food_group in gi_data:
                for food_item in food_group.get('list', []):
                    food_name = food_item.get('foodName', '')
                    gi_value = food_item.get('GI', 0)
                    
                    # 清理食物名称（去除前缀标记如 * 和括号内容）
                    clean_name = food_name.strip()
                    if clean_name.startswith('*'):
                        clean_name = clean_name[1:].strip()
                    
                    # 提取主要名称（括号前的部分）
                    if '（' in clean_name:
                        main_name = clean_name.split('（')[0].strip()
                        gi_mapping[main_name] = gi_value
                    
                    # 同时保存完整名称
                    gi_mapping[clean_name] = gi_value
            
            logger.info(f"✅ 从JSON文件加载了 {len(gi_mapping)} 个食物的GI值")
            
        except FileNotFoundError:
            logger.warning(f"⚠️ GI数据文件未找到: {json_path}，使用默认数据")
            # 使用默认的核心数据
            gi_mapping = self._get_default_gi_data()
        except Exception as e:
            logger.error(f"❌ 加载GI数据失败: {e}，使用默认数据")
            gi_mapping = self._get_default_gi_data()
        
        return gi_mapping
    
    def _get_default_gi_data(self) -> Dict[str, float]:
        """
        获取默认的GI数据（核心食物）
        
        Returns:
            Dict[str, float]: 默认的GI值映射
        """
        return {
            # 主食类
            "大米": 73,
            "糙米": 50,
            "燕麦": 55,
            "红薯": 54,
            "土豆": 78,
            "白面包": 75,
            "全麦面包": 51,
            "意大利面": 49,
            "馒头": 88,
            "玉米": 52,
            
            # 水果类
            "香蕉": 51,
            "苹果": 36,
            "橙子": 43,
            "葡萄": 46,
            "西瓜": 76,
            "樱桃": 22,
            "柚子": 25,
            "梨": 38,
            "桃": 28,
            
            # 豆类
            "黄豆": 18,
            "绿豆": 27,
            "豆腐": 32,
            
            # 其他
            "牛奶": 27,
            "酸奶": 48,
            "蜂蜜": 73,
        }
    
    def _load_allergen_data(self) -> Dict[str, List[str]]:
        """
        加载过敏原映射表
        
        Returns:
            Dict[str, List[str]]: 食物名称到过敏原列表的映射
        """
        return {
            # 乳制品
            "牛奶": ["lactose", "dairy"],
            "酸奶": ["lactose", "dairy"],
            "奶酪": ["lactose", "dairy"],
            "黄油": ["dairy"],
            "奶油": ["dairy"],
            
            # 蛋类
            "鸡蛋": ["egg"],
            "鸭蛋": ["egg"],
            "鹌鹑蛋": ["egg"],
            
            # 坚果类
            "花生": ["peanuts", "nuts"],
            "核桃": ["tree_nuts"],
            "杏仁": ["tree_nuts"],
            "腰果": ["tree_nuts"],
            "榛子": ["tree_nuts"],
            
            # 豆类
            "大豆": ["soy"],
            "黄豆": ["soy"],
            "豆腐": ["soy"],
            "豆浆": ["soy"],
            
            # 谷物类
            "小麦": ["gluten", "wheat"],
            "面包": ["gluten", "wheat"],
            "面条": ["gluten", "wheat"],
            "馒头": ["gluten", "wheat"],
            "大麦": ["gluten"],
            "黑麦": ["gluten"],
            
            # 海鲜类
            "鱼": ["fish"],
            "三文鱼": ["fish"],
            "金枪鱼": ["fish"],
            "鳕鱼": ["fish"],
            "虾": ["shellfish"],
            "蟹": ["shellfish"],
            "龙虾": ["shellfish"],
            "贝类": ["shellfish"],
        }
    
    async def supplement(self) -> SupplementResult:
        """
        执行完整的Food节点补充流程
        
        Returns:
            SupplementResult: 补充结果
        """
        start_time = time.time()
        logger.info("开始Food节点数据补充")
        
        errors = []
        total_updated = 0
        
        async with self.driver.session() as session:
            try:
                # 1. 补充血糖指数和血糖负荷
                logger.info("步骤1: 补充血糖指数和血糖负荷")
                gi_count = await self._supplement_glycemic_data(session)
                total_updated += gi_count
                logger.info(f"✅ 已补充 {gi_count} 个Food节点的血糖指数")
                
            except Exception as e:
                error_msg = f"补充血糖指数失败: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append({"stage": "glycemic_data", "error": str(e)})
            
            try:
                # 2. 补充消化时间
                logger.info("步骤2: 补充消化时间")
                digestion_count = await self._supplement_digestion_time(session)
                logger.info(f"✅ 已补充 {digestion_count} 个Food节点的消化时间")
                
            except Exception as e:
                error_msg = f"补充消化时间失败: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append({"stage": "digestion_time", "error": str(e)})
            
            try:
                # 3. 补充过敏原信息
                logger.info("步骤3: 补充过敏原信息")
                allergen_count = await self._supplement_allergens(session)
                logger.info(f"✅ 已补充 {allergen_count} 个Food节点的过敏原信息")
                
            except Exception as e:
                error_msg = f"补充过敏原信息失败: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append({"stage": "allergens", "error": str(e)})
        
        execution_time = time.time() - start_time
        
        # 统计总节点数
        async with self.driver.session() as session:
            result = await session.run("MATCH (f:Food) RETURN count(f) as total")
            record = await result.single()
            total_nodes = record["total"] if record else 0
        
        logger.info(f"Food节点补充完成，耗时 {execution_time:.2f}秒")
        
        return SupplementResult(
            total_nodes=total_nodes,
            updated_nodes=total_updated,
            errors=errors,
            execution_time=execution_time
        )
    
    async def _supplement_glycemic_data(self, session) -> int:
        """
        补充血糖指数和血糖负荷
        
        Args:
            session: Neo4j会话
            
        Returns:
            int: 更新的节点数量
        """
        updated_count = 0
        
        # 为每个食物补充GI值和GL值
        for food_name, gi in self.gi_data.items():
            # 先补充GI值
            result = await session.run("""
                MATCH (f:Food)
                WHERE f.name CONTAINS $food_name
                SET f.glycemic_index = $gi
                RETURN count(f) as updated
            """, {"food_name": food_name, "gi": gi})
            
            record = await result.single()
            if record:
                count = record["updated"]
                updated_count += count
                if count > 0:
                    logger.debug(f"为 {count} 个包含'{food_name}'的食物补充了GI值 {gi}")
                    
                    # 如果有碳水化合物数据，补充GL值
                    await session.run("""
                        MATCH (f:Food)
                        WHERE f.name CONTAINS $food_name
                          AND f.carbohydrate IS NOT NULL
                          AND f.glycemic_index IS NOT NULL
                        SET f.glycemic_load = toFloat(f.glycemic_index) * toFloat(f.carbohydrate) / 100.0
                    """, {"food_name": food_name})
        
        return updated_count
    
    async def _supplement_digestion_time(self, session) -> int:
        """
        补充消化时间（基于GI值估算）
        
        Args:
            session: Neo4j会话
            
        Returns:
            int: 更新的节点数量
        """
        # 根据GI值估算消化时间
        # 高GI (>70): 快速消化，约60分钟
        # 中GI (55-70): 中等消化，约90分钟
        # 低GI (<55): 慢速消化，约120分钟
        result = await session.run("""
            MATCH (f:Food)
            WHERE f.glycemic_index IS NOT NULL
            SET f.digestion_time_minutes = CASE
                WHEN f.glycemic_index > 70 THEN 60
                WHEN f.glycemic_index >= 55 THEN 90
                ELSE 120
            END
            RETURN count(f) as updated
        """)
        
        record = await result.single()
        return record["updated"] if record else 0
    
    async def _supplement_allergens(self, session) -> int:
        """
        补充过敏原信息
        
        Args:
            session: Neo4j会话
            
        Returns:
            int: 更新的节点数量
        """
        updated_count = 0
        
        # 为每个食物补充过敏原信息
        for food_name, allergens in self.allergen_data.items():
            allergens_json = json.dumps(allergens, ensure_ascii=False)
            
            result = await session.run("""
                MATCH (f:Food)
                WHERE f.name CONTAINS $food_name
                SET f.allergens = $allergens
                RETURN count(f) as updated
            """, {"food_name": food_name, "allergens": allergens_json})
            
            record = await result.single()
            if record:
                count = record["updated"]
                updated_count += count
                if count > 0:
                    logger.debug(f"为 {count} 个包含'{food_name}'的食物补充了过敏原信息")
        
        return updated_count
