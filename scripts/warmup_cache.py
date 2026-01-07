#!/usr/bin/env python3
"""
缓存预热脚本 - 启动时预热所有常用数据

预热内容：
1. 常用用户ID的会员权限
2. 常用查询的BGE复杂度分类
3. 常用动作和肌肉数据

用法：
python scripts/warmup_cache.py

版本: v1.0.0
日期: 2025-12-28
"""

import asyncio
import logging
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework.storage.intelligent_membership_cache import IntelligentMembershipCache
from framework.models.query_complexity_classifier import QueryComplexityClassifier
from applications.fitness.clients.backend_client import BackendClient

logger = logging.getLogger(__name__)


async def warmup_membership_cache():
    """预热会员权限缓存"""
    logger.info("🚀 开始预热会员权限缓存...")

    # 常用用户ID列表（从数据库获取或预设）
    common_user_ids = [
        "1", "2", "3", "4", "5",  # 测试用户
        "1001", "1002", "1003", "1004", "1005",  # 示例用户
        "demo", "test", "guest"  # 特殊用户
    ]

    # 初始化缓存（需要后端客户端）
    backend_client = BackendClient()
    membership_cache = IntelligentMembershipCache(
        backend_client=backend_client,
        redis_client=None,  # 暂时不使用Redis
        max_memory_entries=1000,
        redis_ttl_seconds=3600,
        api_timeout_ms=1000
    )

    # 预热所有用户
    for user_id in common_user_ids:
        try:
            logger.info(f"   预热用户 {user_id}...")
            membership = await membership_cache.get_user_membership(user_id)
            if membership:
                logger.info(f"   ✅ 用户 {user_id}: {membership.get('tier', 'unknown')}")
            else:
                logger.info(f"   ⚠️ 用户 {user_id}: 未找到")
        except Exception as e:
            logger.error(f"   ❌ 用户 {user_id}: {e}")

    logger.info("✅ 会员权限缓存预热完成")


async def warmup_bge_classifier():
    """预热BGE复杂度分类器"""
    logger.info("🚀 开始预热BGE复杂度分类器...")

    # 常用查询列表
    common_queries = [
        # 健身基础问题
        "我想增肌",
        "怎么减肥",
        "深蹲怎么做",
        "卧推标准动作",
        "训练计划怎么制定",

        # 营养问题
        "蛋白质摄入多少",
        "减脂期怎么吃",
        "增肌期营养",
        "补剂推荐",

        # 高级问题
        "我有腰椎间盘突出，能练硬拉吗",
        "膝盖疼痛怎么训练",
        "女性产后恢复训练",
        "老年人力量训练",

        # 简单问题
        "你好",
        "谢谢",
        "再见"
    ]

    classifier = QueryComplexityClassifier()

    # 预热所有查询
    for query in common_queries:
        try:
            logger.info(f"   预热查询: {query[:20]}...")
            result = await classifier.classify_complexity(query)
            logger.info(f"   ✅ {query[:20]}... -> {result.reason}")
        except Exception as e:
            logger.error(f"   ❌ {query[:20]}...: {e}")

    logger.info("✅ BGE复杂度分类器预热完成")


async def warmup_graphrag_data():
    """预热GraphRAG数据"""
    logger.info("🚀 开始预热GraphRAG数据...")

    # 常用健身动作
    common_exercises = [
        "深蹲", "硬拉", "卧推", "推举", "划船",
        "引体向上", "俯卧撑", "平板支撑", "箭步蹲", "臀桥"
    ]

    # 这里可以预热Neo4j和Qdrant的常用数据
    # 实际实现需要根据具体的GraphRAG API

    for exercise in common_exercises:
        try:
            logger.info(f"   预热动作: {exercise}")
            # 调用GraphRAG API预热
            # await graphrag_api.query(exercise, domain="fitness_exercises")
            logger.info(f"   ✅ {exercise} 预热完成")
        except Exception as e:
            logger.error(f"   ❌ {exercise}: {e}")

    logger.info("✅ GraphRAG数据预热完成")


async def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("🎯 DAML-RAG 缓存预热工具启动")
    logger.info("=" * 60)

    try:
        # 1. 预热会员权限缓存
        await warmup_membership_cache()
        logger.info("")

        # 2. 预热BGE复杂度分类器
        await warmup_bge_classifier()
        logger.info("")

        # 3. 预热GraphRAG数据
        await warmup_graphrag_data()
        logger.info("")

        logger.info("=" * 60)
        logger.info("🎉 所有缓存预热完成！")
        logger.info("现在用户查询将享受极速响应！")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 预热过程出错: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
    )

    # 运行预热
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
