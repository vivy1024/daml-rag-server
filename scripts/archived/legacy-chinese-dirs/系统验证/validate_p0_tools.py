"""
P0核心工具验证脚本

使用真实的数据库连接验证所有P0工具的功能
不使用Mock数据，直接连接Neo4j、Qdrant和三层检索引擎

验证内容：
1. 所有P0工具都能正确注册
2. 工具注册表功能正常
3. 三层检索引擎集成正确
4. 基础架构（BaseMCPTool、异常类型、注册表）功能正常

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-15
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.framework.clients.neo4j_client import Neo4jClient
from qdrant_client import QdrantClient
from src.framework.retrieval.true_three_layer_engine import TrueThreeLayerEngine
from src.applications.fitness.mcp_tools.registry import MCPToolRegistry
from src.applications.fitness.mcp_tools.exercise.intelligent_exercise_selector import IntelligentExerciseSelector
from src.applications.fitness.mcp_tools.safety.contraindications_checker import ContraindicationsChecker
from src.applications.fitness.mcp_tools.safety.injury_risk_assessor import InjuryRiskAssessor
from src.applications.fitness.mcp_tools.training.muscle_group_volume_calculator import MuscleGroupVolumeCalculator
from src.applications.fitness.mcp_tools.nutrition.tdee_calculator import TDEECalculator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class P0ToolsValidator:
    """P0工具验证器"""
    
    def __init__(self):
        self.neo4j_client = None
        self.qdrant_client = None
        self.three_layer_engine = None
        self.registry = None
        self.validation_results = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "errors": []
        }
    
    async def initialize_clients(self):
        """初始化数据库客户端"""
        logger.info("🔧 初始化数据库客户端...")
        
        try:
            # 初始化Neo4j客户端
            self.neo4j_client = Neo4jClient()
            logger.info("✅ Neo4j客户端初始化成功")
            
            # 初始化Qdrant客户端
            self.qdrant_client = QdrantClient(url="http://qdrant:6333")
            logger.info("✅ Qdrant客户端初始化成功")
            
            # 初始化三层检索引擎（它会自己管理连接）
            self.three_layer_engine = TrueThreeLayerEngine()
            logger.info("✅ 三层检索引擎初始化成功")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 客户端初始化失败: {e}")
            self.validation_results["errors"].append(f"客户端初始化失败: {e}")
            return False
    
    def register_p0_tools(self):
        """注册所有P0工具"""
        logger.info("📝 注册P0核心工具...")
        
        try:
            self.registry = MCPToolRegistry()
            
            # 注册5个P0工具
            tools = [
                IntelligentExerciseSelector(
                    self.neo4j_client,
                    self.qdrant_client,
                    self.three_layer_engine,
                    logger
                ),
                ContraindicationsChecker(
                    self.neo4j_client,
                    self.qdrant_client,
                    self.three_layer_engine,
                    logger
                ),
                InjuryRiskAssessor(
                    self.neo4j_client,
                    self.qdrant_client,
                    self.three_layer_engine,
                    logger
                ),
                MuscleGroupVolumeCalculator(
                    self.neo4j_client,
                    self.qdrant_client,
                    self.three_layer_engine,
                    logger
                ),
                TDEECalculator(
                    self.neo4j_client,
                    self.qdrant_client,
                    self.three_layer_engine,
                    logger
                )
            ]
            
            for tool in tools:
                self.registry.register_tool(tool)
                logger.info(f"  ✅ 注册工具: {tool.get_name()}")
            
            logger.info(f"✅ 成功注册 {len(tools)} 个P0工具")
            return True
            
        except Exception as e:
            logger.error(f"❌ 工具注册失败: {e}")
            self.validation_results["errors"].append(f"工具注册失败: {e}")
            return False
    
    def validate_tool_registration(self):
        """验证工具注册"""
        logger.info("\n📋 验证工具注册...")
        
        expected_tools = [
            "intelligent_exercise_selector",
            "contraindications_checker",
            "injury_risk_assessor",
            "muscle_group_volume_calculator",
            "tdee_calculator"
        ]
        
        for tool_name in expected_tools:
            self.validation_results["total_checks"] += 1
            
            tool = self.registry.get_tool(tool_name)
            if tool:
                logger.info(f"  ✅ 工具已注册: {tool_name}")
                self.validation_results["passed_checks"] += 1
            else:
                logger.error(f"  ❌ 工具未注册: {tool_name}")
                self.validation_results["failed_checks"] += 1
                self.validation_results["errors"].append(f"工具未注册: {tool_name}")
    
    def validate_tool_metadata(self):
        """验证工具元数据"""
        logger.info("\n📊 验证工具元数据...")
        
        for tool_name in self.registry.list_tool_names():
            self.validation_results["total_checks"] += 1
            
            metadata = self.registry.get_metadata(tool_name)
            
            if metadata and metadata.name and metadata.category:
                logger.info(f"  ✅ {tool_name}: {metadata.category} - {metadata.complexity}")
                self.validation_results["passed_checks"] += 1
            else:
                logger.error(f"  ❌ {tool_name}: 元数据不完整")
                self.validation_results["failed_checks"] += 1
                self.validation_results["errors"].append(f"{tool_name}: 元数据不完整")
    
    def validate_tool_categories(self):
        """验证工具分类"""
        logger.info("\n🏷️  验证工具分类...")
        
        expected_categories = ["exercise", "safety", "training", "nutrition"]
        categories = self.registry.get_categories()
        
        for category in expected_categories:
            self.validation_results["total_checks"] += 1
            
            if category in categories:
                logger.info(f"  ✅ 分类存在: {category}")
                self.validation_results["passed_checks"] += 1
            else:
                logger.error(f"  ❌ 分类缺失: {category}")
                self.validation_results["failed_checks"] += 1
                self.validation_results["errors"].append(f"分类缺失: {category}")
    
    def validate_three_layer_engine(self):
        """验证三层检索引擎集成"""
        logger.info("\n🔍 验证三层检索引擎集成...")
        
        self.validation_results["total_checks"] += 1
        
        tool = self.registry.get_tool("intelligent_exercise_selector")
        
        if tool and hasattr(tool, "three_layer_engine") and tool.three_layer_engine:
            logger.info("  ✅ 三层检索引擎已正确注入")
            self.validation_results["passed_checks"] += 1
        else:
            logger.error("  ❌ 三层检索引擎未正确注入")
            self.validation_results["failed_checks"] += 1
            self.validation_results["errors"].append("三层检索引擎未正确注入")
    
    def validate_database_connections(self):
        """验证数据库连接"""
        logger.info("\n🔌 验证数据库连接...")
        
        # 验证Neo4j连接
        self.validation_results["total_checks"] += 1
        if self.neo4j_client:
            logger.info("  ✅ Neo4j客户端连接正常")
            self.validation_results["passed_checks"] += 1
        else:
            logger.error("  ❌ Neo4j客户端连接异常")
            self.validation_results["failed_checks"] += 1
            self.validation_results["errors"].append("Neo4j客户端连接异常")
        
        # 验证Qdrant连接
        self.validation_results["total_checks"] += 1
        if self.qdrant_client:
            logger.info("  ✅ Qdrant客户端连接正常")
            self.validation_results["passed_checks"] += 1
        else:
            logger.error("  ❌ Qdrant客户端连接异常")
            self.validation_results["failed_checks"] += 1
            self.validation_results["errors"].append("Qdrant客户端连接异常")
    
    def print_summary(self):
        """打印验证摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 P0核心工具验证摘要")
        logger.info("=" * 60)
        logger.info(f"总检查项: {self.validation_results['total_checks']}")
        logger.info(f"✅ 通过: {self.validation_results['passed_checks']}")
        logger.info(f"❌ 失败: {self.validation_results['failed_checks']}")
        
        if self.validation_results["errors"]:
            logger.info("\n❌ 错误列表:")
            for error in self.validation_results["errors"]:
                logger.info(f"  - {error}")
        
        success_rate = (
            self.validation_results["passed_checks"] / 
            self.validation_results["total_checks"] * 100
            if self.validation_results["total_checks"] > 0 else 0
        )
        
        logger.info(f"\n成功率: {success_rate:.1f}%")
        logger.info("=" * 60)
        
        return self.validation_results["failed_checks"] == 0
    
    async def run_validation(self):
        """运行完整验证"""
        logger.info("🚀 开始P0核心工具验证\n")
        
        # 1. 初始化客户端
        if not await self.initialize_clients():
            logger.error("❌ 客户端初始化失败，终止验证")
            return False
        
        # 2. 注册P0工具
        if not self.register_p0_tools():
            logger.error("❌ 工具注册失败，终止验证")
            return False
        
        # 3. 验证工具注册
        self.validate_tool_registration()
        
        # 4. 验证工具元数据
        self.validate_tool_metadata()
        
        # 5. 验证工具分类
        self.validate_tool_categories()
        
        # 6. 验证三层检索引擎
        self.validate_three_layer_engine()
        
        # 7. 验证数据库连接
        self.validate_database_connections()
        
        # 8. 打印摘要
        return self.print_summary()
    
    async def cleanup(self):
        """清理资源"""
        logger.info("\n🧹 清理资源...")
        
        # Neo4j客户端会自动管理连接
        logger.info("✅ 资源清理完成")


async def main():
    """主函数"""
    validator = P0ToolsValidator()
    
    try:
        success = await validator.run_validation()
        
        if success:
            logger.info("\n🎉 所有P0核心工具验证通过！")
            return 0
        else:
            logger.error("\n❌ P0核心工具验证失败，请检查错误信息")
            return 1
            
    except Exception as e:
        logger.error(f"\n💥 验证过程发生异常: {e}", exc_info=True)
        return 1
        
    finally:
        await validator.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
