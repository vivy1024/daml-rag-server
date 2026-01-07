#!/usr/bin/env python3
"""
训练知识导入脚本

使用方法：
1. 导入所有训练知识：
   python scripts/import_training_knowledge.py --data-type all

2. 导入特定类型的训练知识：
   python scripts/import_training_knowledge.py --data-type training_volume
   python scripts/import_training_knowledge.py --data-type strength_standards
   python scripts/import_training_knowledge.py --data-type workout_programs
   python scripts/import_training_knowledge.py --data-type acsm_standards
   python scripts/import_training_knowledge.py --data-type nsca_standards

3. 模拟导入（不实际执行）：
   python scripts/import_training_knowledge.py --data-type all --dry-run

4. 输出JSON格式报告：
   python scripts/import_training_knowledge.py --data-type all --output-json report.json
"""

import asyncio
import sys
import os
import argparse
import json
import logging
from datetime import datetime
from typing import Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.applications.fitness.data_supplement import DataSupplementManager
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, total_stages: int):
        self.total_stages = total_stages
        self.current_stage = 0
        self.start_time = datetime.now()
    
    def next_stage(self, stage_name: str):
        """进入下一阶段"""
        self.current_stage += 1
        elapsed = (datetime.now() - self.start_time).total_seconds()
        logger.info(f"\n{'=' * 60}")
        logger.info(f"[{self.current_stage}/{self.total_stages}] {stage_name}")
        logger.info(f"已用时: {elapsed:.2f}秒")
        logger.info(f"{'=' * 60}")
    
    def complete(self):
        """完成所有阶段"""
        total_time = (datetime.now() - self.start_time).total_seconds()
        logger.info(f"\n{'=' * 60}")
        logger.info(f"✅ 所有阶段完成！总耗时: {total_time:.2f}秒")
        logger.info(f"{'=' * 60}")


async def import_training_knowledge(
    data_type: str,
    dry_run: bool = False,
    output_json: Optional[str] = None
) -> int:
    """
    导入训练知识数据
    
    Args:
        data_type: 数据类型 (training_volume, strength_standards, workout_programs, 
                           acsm_standards, nsca_standards, all)
        dry_run: 是否为模拟导入
        output_json: JSON报告输出路径
    
    Returns:
        int: 退出码 (0=成功, 1=失败)
    """
    logger.info("\n" + "=" * 60)
    logger.info("训练知识导入工具")
    logger.info("=" * 60)
    logger.info(f"数据类型: {data_type}")
    logger.info(f"模拟导入: {'是' if dry_run else '否'}")
    if output_json:
        logger.info(f"JSON报告: {output_json}")
    logger.info("=" * 60)
    
    if dry_run:
        logger.warning("\n⚠️  模拟导入模式：不会实际修改数据库")
    
    # 加载环境变量
    load_dotenv()
    
    # 获取Neo4j连接信息
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "build_body_2024")
    
    # 创建异步Neo4j driver
    driver = AsyncGraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password)
    )
    
    try:
        # 创建数据补充管理器
        manager = DataSupplementManager(driver)
        
        # 根据数据类型执行导入
        report = None
        
        if data_type == "all":
            # 导入所有训练知识
            tracker = ProgressTracker(5)
            
            tracker.next_stage("训练量标准导入")
            if not dry_run:
                report = await manager.execute_training_knowledge(skip_validation=True)
            else:
                logger.info("⏭️  跳过实际导入（模拟模式）")
        
        elif data_type == "training_volume":
            # 仅导入训练量标准
            tracker = ProgressTracker(1)
            tracker.next_stage("训练量标准导入")
            
            if not dry_run:
                report = await manager.execute_training_volume_only()
            else:
                logger.info("⏭️  跳过实际导入（模拟模式）")
        
        elif data_type == "strength_standards":
            # 仅导入力量标准
            tracker = ProgressTracker(1)
            tracker.next_stage("力量标准导入")
            
            if not dry_run:
                report = await manager.execute_strength_standards_only()
            else:
                logger.info("⏭️  跳过实际导入（模拟模式）")
        
        elif data_type == "workout_programs":
            # 仅导入训练计划模板
            tracker = ProgressTracker(1)
            tracker.next_stage("训练计划模板导入")
            
            if not dry_run:
                report = await manager.execute_workout_programs_only()
            else:
                logger.info("⏭️  跳过实际导入（模拟模式）")
        
        elif data_type == "acsm_standards":
            # 仅导入ACSM标准
            tracker = ProgressTracker(1)
            tracker.next_stage("ACSM标准导入")
            
            if not dry_run:
                report = await manager.execute_acsm_standards_only()
            else:
                logger.info("⏭️  跳过实际导入（模拟模式）")
        
        elif data_type == "nsca_standards":
            # 仅导入NSCA标准
            tracker = ProgressTracker(1)
            tracker.next_stage("NSCA标准导入")
            
            if not dry_run:
                report = await manager.execute_nsca_standards_only()
            else:
                logger.info("⏭️  跳过实际导入（模拟模式）")
        
        else:
            logger.error(f"❌ 不支持的数据类型: {data_type}")
            logger.error("支持的类型: training_volume, strength_standards, workout_programs, "
                        "acsm_standards, nsca_standards, all")
            return 1
        
        tracker.complete()
        
        # 输出报告
        if report:
            logger.info("\n" + "=" * 60)
            logger.info("导入报告")
            logger.info("=" * 60)
            logger.info(report.generate_summary())
            
            # 保存JSON报告
            if output_json:
                with open(output_json, 'w', encoding='utf-8') as f:
                    json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
                logger.info(f"\n✅ JSON报告已保存到: {output_json}")
            
            # 返回状态码
            return 0 if report.is_successful else 1
        else:
            # 模拟模式
            logger.info("\n✅ 模拟导入完成")
            return 0
        
    except Exception as e:
        logger.error(f"\n❌ 导入过程中发生错误: {e}", exc_info=True)
        return 1
    
    finally:
        await driver.close()
        logger.info("🔒 Neo4j连接已关闭")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='训练知识导入工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 导入所有训练知识
  python scripts/import_training_knowledge.py --data-type all
  
  # 仅导入训练量标准
  python scripts/import_training_knowledge.py --data-type training_volume
  
  # 模拟导入（不实际执行）
  python scripts/import_training_knowledge.py --data-type all --dry-run
  
  # 输出JSON格式报告
  python scripts/import_training_knowledge.py --data-type all --output-json report.json
        """
    )
    
    parser.add_argument(
        '--data-type',
        type=str,
        required=True,
        choices=['training_volume', 'strength_standards', 'workout_programs', 
                 'acsm_standards', 'nsca_standards', 'all'],
        help='要导入的数据类型'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='模拟导入，不实际修改数据库'
    )
    
    parser.add_argument(
        '--output-json',
        type=str,
        help='JSON格式报告的输出路径'
    )
    
    args = parser.parse_args()
    
    # 执行导入
    exit_code = asyncio.run(import_training_knowledge(
        data_type=args.data_type,
        dry_run=args.dry_run,
        output_json=args.output_json
    ))
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
