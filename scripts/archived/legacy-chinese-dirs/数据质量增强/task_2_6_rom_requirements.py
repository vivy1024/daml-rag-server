#!/usr/bin/env python3
"""
任务 2.6: 实现关节活动度要求补充

功能：
1. 为关键动作添加rom_requirements字段
2. 验证JSON格式和数值范围（0-180度）
3. 扩展ROM数据覆盖更多关键动作

需求: Requirements 1.3

作者：薛小川
日期：2025-12-15
"""

import asyncio
import json
import logging
from typing import Dict
from neo4j import AsyncGraphDatabase

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ROMRequirementsSupplementer:
    """关节活动度要求补充器"""
    
    def __init__(self, uri: str, user: str, password: str):
        """初始化"""
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.rom_data = self._load_comprehensive_rom_data()
    
    def _load_comprehensive_rom_data(self) -> Dict[str, Dict[str, int]]:
        """
        加载全面的关节活动度要求数据
        
        关节活动度范围参考：
        - 髋关节屈曲 (hip_flexion): 0-120度
        - 髋关节伸展 (hip_extension): 0-30度
        - 膝关节屈曲 (knee_flexion): 0-140度
        - 踝关节背屈 (ankle_dorsiflexion): 0-20度
        - 肩关节屈曲 (shoulder_flexion): 0-180度
        - 肩关节外展 (shoulder_abduction): 0-180度
        - 肩关节水平外展 (shoulder_horizontal_abduction): 0-90度
        - 肘关节屈曲 (elbow_flexion): 0-150度
        - 腕关节背伸 (wrist_extension): 0-70度
        - 腕关节掌屈 (wrist_flexion): 0-80度
        """
        return {
            # 下肢动作
            "杠铃深蹲": {
                "hip_flexion": 90,
                "knee_flexion": 90,
                "ankle_dorsiflexion": 15
            },
            "杠铃前蹲": {
                "hip_flexion": 100,
                "knee_flexion": 100,
                "ankle_dorsiflexion": 20
            },
            "杠铃硬拉": {
                "hip_flexion": 90,
                "knee_flexion": 30
            },
            "罗马尼亚硬拉": {
                "hip_flexion": 90,
                "knee_flexion": 15
            },
            "箱式深蹲": {
                "hip_flexion": 90,
                "knee_flexion": 90,
                "ankle_dorsiflexion": 10
            },
            "保加利亚分腿蹲": {
                "hip_flexion": 90,
                "knee_flexion": 90,
                "ankle_dorsiflexion": 15
            },
            "腿举": {
                "hip_flexion": 90,
                "knee_flexion": 90
            },
            "腿屈伸": {
                "knee_flexion": 90
            },
            "腿弯举": {
                "knee_flexion": 90
            },
            "站姿提踵": {
                "ankle_dorsiflexion": 20
            },
            
            # 上肢推类动作
            "杠铃卧推": {
                "shoulder_horizontal_abduction": 90,
                "elbow_flexion": 90
            },
            "上斜卧推": {
                "shoulder_flexion": 120,
                "elbow_flexion": 90
            },
            "下斜卧推": {
                "shoulder_horizontal_abduction": 80,
                "elbow_flexion": 90
            },
            "哑铃卧推": {
                "shoulder_horizontal_abduction": 100,
                "elbow_flexion": 90
            },
            "杠铃推举": {
                "shoulder_flexion": 180,
                "elbow_flexion": 90
            },
            "哑铃推举": {
                "shoulder_flexion": 180,
                "elbow_flexion": 90
            },
            "阿诺德推举": {
                "shoulder_flexion": 180,
                "elbow_flexion": 90
            },
            
            # 上肢拉类动作
            "引体向上": {
                "shoulder_flexion": 180,
                "elbow_flexion": 140
            },
            "正握引体向上": {
                "shoulder_flexion": 180,
                "elbow_flexion": 140
            },
            "反握引体向上": {
                "shoulder_flexion": 180,
                "elbow_flexion": 140
            },
            "杠铃划船": {
                "shoulder_extension": 30,
                "elbow_flexion": 120
            },
            "哑铃划船": {
                "shoulder_extension": 30,
                "elbow_flexion": 120
            },
            "坐姿划船": {
                "shoulder_extension": 30,
                "elbow_flexion": 120
            },
            "高位下拉": {
                "shoulder_flexion": 180,
                "elbow_flexion": 140
            },
            
            # 手臂动作
            "杠铃弯举": {
                "elbow_flexion": 140
            },
            "哑铃弯举": {
                "elbow_flexion": 140
            },
            "锤式弯举": {
                "elbow_flexion": 140
            },
            "集中弯举": {
                "elbow_flexion": 140
            },
            "三头肌下压": {
                "elbow_flexion": 90
            },
            "仰卧臂屈伸": {
                "elbow_flexion": 120
            },
            "窄距卧推": {
                "shoulder_horizontal_abduction": 60,
                "elbow_flexion": 90
            },
            
            # 肩部动作
            "哑铃侧平举": {
                "shoulder_abduction": 90
            },
            "哑铃前平举": {
                "shoulder_flexion": 90
            },
            "俯身飞鸟": {
                "shoulder_horizontal_abduction": 90
            },
            "面拉": {
                "shoulder_horizontal_abduction": 90,
                "elbow_flexion": 90
            },
            
            # 核心动作
            "平板支撑": {
                "shoulder_flexion": 90
            },
            "侧平板支撑": {
                "shoulder_abduction": 90
            },
            "卷腹": {
                "hip_flexion": 30
            },
            "悬垂举腿": {
                "hip_flexion": 90,
                "shoulder_flexion": 180
            }
        }
    
    def _validate_rom_data(self, exercise_name: str, rom: Dict[str, int]) -> bool:
        """
        验证ROM数据的有效性
        
        Args:
            exercise_name: 动作名称
            rom: ROM数据字典
            
        Returns:
            bool: 是否有效
        """
        is_valid = True
        
        for joint, angle in rom.items():
            if not isinstance(angle, int):
                logger.error(f"   ❌ {exercise_name} 的 {joint} 角度不是整数: {angle}")
                is_valid = False
            elif not (0 <= angle <= 180):
                logger.error(f"   ❌ {exercise_name} 的 {joint} 角度超出范围 (0-180): {angle}")
                is_valid = False
        
        return is_valid
    
    async def supplement_rom_requirements(self) -> Dict:
        """
        补充关节活动度要求
        
        Returns:
            Dict: 执行结果统计
        """
        logger.info("=" * 60)
        logger.info("开始补充关节活动度要求 (ROM Requirements)")
        logger.info("=" * 60)
        
        stats = {
            "total_exercises": len(self.rom_data),
            "updated_count": 0,
            "failed_count": 0,
            "validation_errors": []
        }
        
        async with self.driver.session() as session:
            for exercise_name, rom in self.rom_data.items():
                try:
                    # 验证数据
                    if not self._validate_rom_data(exercise_name, rom):
                        stats["validation_errors"].append(exercise_name)
                        stats["failed_count"] += 1
                        continue
                    
                    # 转换为JSON
                    rom_json = json.dumps(rom, ensure_ascii=False)
                    
                    # 更新Neo4j
                    query = """
                    MATCH (e:Exercise)
                    WHERE e.name_zh = $name
                    SET e.rom_requirements = $rom,
                        e.rom_updated_at = datetime()
                    RETURN count(e) as updated_count
                    """
                    
                    result = await session.run(query, {
                        "name": exercise_name,
                        "rom": rom_json
                    })
                    record = await result.single()
                    
                    if record and record["updated_count"] > 0:
                        stats["updated_count"] += record["updated_count"]
                        logger.info(f"   ✅ {exercise_name}: {len(rom)} 个关节")
                    else:
                        logger.warning(f"   ⚠️ {exercise_name}: 未找到匹配的动作")
                        stats["failed_count"] += 1
                
                except Exception as e:
                    logger.error(f"   ❌ {exercise_name} 补充失败: {e}")
                    stats["failed_count"] += 1
        
        logger.info("=" * 60)
        logger.info("关节活动度要求补充完成")
        logger.info(f"总计: {stats['total_exercises']} 个动作")
        logger.info(f"成功: {stats['updated_count']} 个")
        logger.info(f"失败: {stats['failed_count']} 个")
        if stats["validation_errors"]:
            logger.info(f"验证错误: {len(stats['validation_errors'])} 个")
        logger.info("=" * 60)
        
        return stats
    
    async def verify_rom_requirements(self) -> Dict:
        """
        验证ROM数据的完整性和正确性
        
        Returns:
            Dict: 验证结果
        """
        logger.info("\n" + "=" * 60)
        logger.info("验证关节活动度要求数据")
        logger.info("=" * 60)
        
        async with self.driver.session() as session:
            # 1. 统计有ROM数据的动作数量
            query1 = """
            MATCH (e:Exercise)
            WHERE e.rom_requirements IS NOT NULL
            RETURN count(e) as count
            """
            result1 = await session.run(query1)
            record1 = await result1.single()
            total_with_rom = record1["count"] if record1 else 0
            
            # 2. 检查JSON格式有效性
            query2 = """
            MATCH (e:Exercise)
            WHERE e.rom_requirements IS NOT NULL
            RETURN e.name_zh as name, e.rom_requirements as rom
            LIMIT 10
            """
            result2 = await session.run(query2)
            
            json_valid_count = 0
            json_invalid_count = 0
            
            async for record in result2:
                try:
                    rom_data = json.loads(record["rom"])
                    
                    # 验证数值范围
                    all_valid = True
                    for joint, angle in rom_data.items():
                        if not (0 <= angle <= 180):
                            logger.warning(f"   ⚠️ {record['name']} 的 {joint} 角度超出范围: {angle}")
                            all_valid = False
                    
                    if all_valid:
                        json_valid_count += 1
                        logger.info(f"   ✅ {record['name']}: JSON有效，数值范围正确")
                    else:
                        json_invalid_count += 1
                
                except json.JSONDecodeError as e:
                    json_invalid_count += 1
                    logger.error(f"   ❌ {record['name']}: JSON解析失败 - {e}")
            
            # 3. 列出所有有ROM数据的动作
            query3 = """
            MATCH (e:Exercise)
            WHERE e.rom_requirements IS NOT NULL
            RETURN e.name_zh as name, e.rom_requirements as rom
            ORDER BY e.name_zh
            """
            result3 = await session.run(query3)
            
            all_exercises = []
            async for record in result3:
                all_exercises.append(record["name"])
            
            logger.info(f"\n总计有ROM数据的动作: {total_with_rom} 个")
            logger.info(f"JSON格式验证: {json_valid_count} 个有效, {json_invalid_count} 个无效")
            logger.info(f"\n所有有ROM数据的动作列表:")
            for i, name in enumerate(all_exercises, 1):
                logger.info(f"   {i}. {name}")
            
            logger.info("=" * 60)
            
            return {
                "total_with_rom": total_with_rom,
                "json_valid_count": json_valid_count,
                "json_invalid_count": json_invalid_count,
                "all_exercises": all_exercises
            }
    
    async def close(self):
        """关闭连接"""
        await self.driver.close()


async def main():
    """主函数"""
    # Neo4j连接配置（Docker容器内使用容器名称）
    NEO4J_URI = "bolt://fitness_neo4j:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "build_body_2024"
    
    supplementer = ROMRequirementsSupplementer(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD
    )
    
    try:
        # 1. 补充ROM数据
        stats = await supplementer.supplement_rom_requirements()
        
        # 2. 验证ROM数据
        verification = await supplementer.verify_rom_requirements()
        
        # 3. 输出最终报告
        logger.info("\n" + "=" * 60)
        logger.info("任务 2.6 执行完成")
        logger.info("=" * 60)
        logger.info(f"补充统计:")
        logger.info(f"  - 尝试补充: {stats['total_exercises']} 个动作")
        logger.info(f"  - 成功更新: {stats['updated_count']} 个动作")
        logger.info(f"  - 失败: {stats['failed_count']} 个动作")
        logger.info(f"\n验证结果:")
        logger.info(f"  - 数据库中有ROM数据的动作: {verification['total_with_rom']} 个")
        logger.info(f"  - JSON格式有效: {verification['json_valid_count']} 个")
        logger.info(f"  - JSON格式无效: {verification['json_invalid_count']} 个")
        logger.info("=" * 60)
        
    finally:
        await supplementer.close()


if __name__ == "__main__":
    asyncio.run(main())
