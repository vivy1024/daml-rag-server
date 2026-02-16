#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
教材知识提取脚本

使用 neo4j-graphrag-python 的 SimpleKGPipeline 从健身教材中提取知识图谱

版本: v1.0.0
日期: 2026-02-16
作者: 薛小川
"""

import os
import sys
import json
import yaml
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Neo4j GraphRAG 导入
from neo4j import GraphDatabase
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.embeddings import SentenceTransformerEmbeddings
from neo4j_graphrag.experimental.pipeline.kg_builder import SimpleKGPipeline
from neo4j_graphrag.experimental.components.schema import GraphSchema
from neo4j_graphrag.experimental.components.text_splitters.fixed_size_splitter import FixedSizeSplitter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextbookKnowledgeExtractor:
    """教材知识提取器"""

    def __init__(self, config_path: str = "config/kg_pipeline_config.yaml"):
        """
        初始化提取器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(project_root) / config_path
        self.config = self._load_config()

        # 初始化组件
        self.llm = self._init_llm()
        self.embedder = self._init_embedder()
        self.driver = self._init_neo4j_driver()
        self.schema = self._load_schema()
        self.text_splitter = self._init_text_splitter()

        # 检查点管理
        self.checkpoint_file = Path(project_root) / self.config['checkpoint']['checkpoint_file']
        self.checkpoint_data = self._load_checkpoint()

        logger.info("✅ 教材知识提取器初始化完成")

    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        logger.info(f"✅ 配置文件加载成功: {self.config_path}")
        return config

    def _init_llm(self) -> OpenAILLM:
        """初始化 LLM（DeepSeek）"""
        llm_config = self.config['llm']

        # 从环境变量读取配置
        api_key = os.getenv(llm_config['api_key_env'])
        base_url = os.getenv(llm_config['base_url_env'])
        model = os.getenv(llm_config['model_env'])

        if not api_key:
            raise ValueError(f"环境变量 {llm_config['api_key_env']} 未设置")

        # 创建 OpenAILLM 实例（DeepSeek 兼容 OpenAI API）
        llm = OpenAILLM(
            model_name=model,
            api_key=api_key,
            base_url=base_url,
            model_params={
                'temperature': llm_config['temperature'],
                'max_tokens': llm_config['max_tokens'],
            }
        )

        logger.info(f"✅ LLM 初始化完成: {model}")
        return llm

    def _init_embedder(self) -> SentenceTransformerEmbeddings:
        """初始化 Embedder（GTE-Large-zh）"""
        embedder_config = self.config['embedder']

        # 创建 SentenceTransformerEmbeddings 实例
        embedder = SentenceTransformerEmbeddings(
            model=embedder_config['model']
        )

        logger.info(f"✅ Embedder 初始化完成: {embedder_config['model']}")
        return embedder

    def _init_neo4j_driver(self):
        """初始化 Neo4j Driver"""
        neo4j_config = self.config['neo4j']

        # 从环境变量读取配置
        uri = os.getenv(neo4j_config['uri_env'])
        user = os.getenv(neo4j_config['user_env'])
        password = os.getenv(neo4j_config['password_env'])

        if not all([uri, user, password]):
            raise ValueError("Neo4j 环境变量未完全设置")

        # 创建 Driver
        driver = GraphDatabase.driver(uri, auth=(user, password))

        # 测试连接
        try:
            driver.verify_connectivity()
            logger.info(f"✅ Neo4j 连接成功: {uri}")
        except Exception as e:
            logger.error(f"❌ Neo4j 连接失败: {e}")
            raise

        return driver

    def _load_schema(self) -> GraphSchema:
        """加载 Schema 配置"""
        schema_file = Path(project_root) / self.config['pipeline']['schema_file']

        if not schema_file.exists():
            raise FileNotFoundError(f"Schema 文件不存在: {schema_file}")

        # 使用 GraphSchema.from_file 加载
        schema = GraphSchema.from_file(schema_file)

        logger.info(f"✅ Schema 加载成功: {schema_file}")
        logger.info(f"   - 节点类型: {len(schema.node_types)}")
        logger.info(f"   - 关系类型: {len(schema.relationship_types)}")

        return schema

    def _init_text_splitter(self) -> FixedSizeSplitter:
        """初始化文本分割器"""
        splitter_config = self.config['text_splitter']

        # 创建 FixedSizeSplitter
        text_splitter = FixedSizeSplitter(
            chunk_size=splitter_config['chunk_size'],
            chunk_overlap=splitter_config['chunk_overlap']
        )

        logger.info(f"✅ 文本分割器初始化完成: chunk_size={splitter_config['chunk_size']}, overlap={splitter_config['chunk_overlap']}")
        return text_splitter

    def _load_checkpoint(self) -> Dict[str, Any]:
        """加载检查点"""
        if not self.config['checkpoint']['enabled']:
            return {}

        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            logger.info(f"✅ 检查点加载成功: {self.checkpoint_file}")
            return checkpoint

        return {}

    def _save_checkpoint(self, file_path: str, processed_pages: int):
        """保存检查点"""
        if not self.config['checkpoint']['enabled']:
            return

        self.checkpoint_data[file_path] = {
            'processed_pages': processed_pages,
            'timestamp': datetime.now().isoformat()
        }

        # 确保目录存在
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(self.checkpoint_data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 检查点保存成功: {file_path} (已处理 {processed_pages} 页)")

    def extract_from_pdf(
        self,
        pdf_path: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        从 PDF 提取知识图谱

        Args:
            pdf_path: PDF 文件路径
            document_metadata: 文档元数据
            dry_run: 是否为 dry-run 模式（不写入数据库）

        Returns:
            提取结果统计
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

        logger.info(f"开始提取 PDF: {pdf_path}")

        # 检查是否已处理
        if str(pdf_path) in self.checkpoint_data:
            logger.info(f"⚠️ 文件已处理，跳过: {pdf_path}")
            return self.checkpoint_data[str(pdf_path)]

        # 创建 Pipeline
        pipeline = SimpleKGPipeline(
            llm=self.llm,
            driver=self.driver,
            embedder=self.embedder,
            schema=self.schema,
            from_pdf=True,
            text_splitter=self.text_splitter,
            on_error=self.config['kg_writer']['on_error'],
            perform_entity_resolution=self.config['kg_writer']['perform_entity_resolution']
        )

        # 运行提取
        try:
            import asyncio
            result = asyncio.run(pipeline.run_async(
                file_path=str(pdf_path),
                document_metadata=document_metadata
            ))

            # 提取统计
            stats = {
                'file_path': str(pdf_path),
                'status': 'success',
                'nodes_created': len(result.nodes) if hasattr(result, 'nodes') else 0,
                'relationships_created': len(result.relationships) if hasattr(result, 'relationships') else 0,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"✅ 提取完成: {pdf_path}")
            logger.info(f"   - 节点数: {stats['nodes_created']}")
            logger.info(f"   - 关系数: {stats['relationships_created']}")

            # 保存检查点
            if not dry_run:
                self._save_checkpoint(str(pdf_path), stats['nodes_created'])

            return stats

        except Exception as e:
            logger.error(f"❌ 提取失败: {pdf_path}, 错误: {e}")
            return {
                'file_path': str(pdf_path),
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def extract_from_text(
        self,
        text: str,
        document_metadata: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        从文本提取知识图谱

        Args:
            text: 文本内容
            document_metadata: 文档元数据
            dry_run: 是否为 dry-run 模式（不写入数据库）

        Returns:
            提取结果统计
        """
        logger.info(f"开始提取文本 (长度: {len(text)} 字符)")

        # 创建 Pipeline
        pipeline = SimpleKGPipeline(
            llm=self.llm,
            driver=self.driver,
            embedder=self.embedder,
            schema=self.schema,
            from_pdf=False,
            text_splitter=self.text_splitter,
            on_error=self.config['kg_writer']['on_error'],
            perform_entity_resolution=self.config['kg_writer']['perform_entity_resolution']
        )

        # 运行提取
        try:
            import asyncio
            result = asyncio.run(pipeline.run_async(
                text=text,
                document_metadata=document_metadata
            ))

            # 提取统计
            stats = {
                'text_length': len(text),
                'status': 'success',
                'nodes_created': len(result.nodes) if hasattr(result, 'nodes') else 0,
                'relationships_created': len(result.relationships) if hasattr(result, 'relationships') else 0,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"✅ 提取完成")
            logger.info(f"   - 节点数: {stats['nodes_created']}")
            logger.info(f"   - 关系数: {stats['relationships_created']}")

            return stats

        except Exception as e:
            logger.error(f"❌ 提取失败, 错误: {e}")
            return {
                'text_length': len(text),
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def batch_extract_pdfs(
        self,
        pdf_dir: str,
        pattern: str = "*.pdf",
        dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """
        批量提取 PDF 目录中的所有文件

        Args:
            pdf_dir: PDF 目录路径
            pattern: 文件匹配模式
            dry_run: 是否为 dry-run 模式

        Returns:
            提取结果列表
        """
        pdf_dir = Path(pdf_dir)
        if not pdf_dir.exists():
            raise FileNotFoundError(f"目录不存在: {pdf_dir}")

        # 查找所有 PDF 文件
        pdf_files = list(pdf_dir.glob(pattern))
        logger.info(f"找到 {len(pdf_files)} 个 PDF 文件")

        results = []
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"处理 [{i}/{len(pdf_files)}]: {pdf_file.name}")

            # 提取文档元数据
            metadata = {
                'source_file': pdf_file.name,
                'source_dir': str(pdf_dir),
                'extraction_date': datetime.now().isoformat()
            }

            # 提取
            result = self.extract_from_pdf(
                pdf_path=str(pdf_file),
                document_metadata=metadata,
                dry_run=dry_run
            )
            results.append(result)

        # 汇总统计
        total_nodes = sum(r.get('nodes_created', 0) for r in results)
        total_relationships = sum(r.get('relationships_created', 0) for r in results)
        success_count = sum(1 for r in results if r.get('status') == 'success')

        logger.info(f"\n{'='*60}")
        logger.info(f"批量提取完成")
        logger.info(f"  - 总文件数: {len(pdf_files)}")
        logger.info(f"  - 成功: {success_count}")
        logger.info(f"  - 失败: {len(pdf_files) - success_count}")
        logger.info(f"  - 总节点数: {total_nodes}")
        logger.info(f"  - 总关系数: {total_relationships}")
        logger.info(f"{'='*60}\n")

        return results

    def close(self):
        """关闭资源"""
        if self.driver:
            self.driver.close()
            logger.info("✅ Neo4j Driver 已关闭")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="教材知识提取脚本")
    parser.add_argument(
        '--mode',
        choices=['pdf', 'text', 'batch'],
        required=True,
        help='提取模式: pdf（单个PDF）, text（文本）, batch（批量PDF）'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='输入路径（PDF文件路径、文本文件路径或PDF目录）'
    )
    parser.add_argument(
        '--config',
        default='config/kg_pipeline_config.yaml',
        help='配置文件路径'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry-run 模式（不写入数据库）'
    )
    parser.add_argument(
        '--pattern',
        default='*.pdf',
        help='批量模式下的文件匹配模式'
    )

    args = parser.parse_args()

    # 创建提取器
    extractor = TextbookKnowledgeExtractor(config_path=args.config)

    try:
        if args.mode == 'pdf':
            # 单个 PDF 提取
            result = extractor.extract_from_pdf(
                pdf_path=args.input,
                dry_run=args.dry_run
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.mode == 'text':
            # 文本提取
            with open(args.input, 'r', encoding='utf-8') as f:
                text = f.read()

            result = extractor.extract_from_text(
                text=text,
                dry_run=args.dry_run
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif args.mode == 'batch':
            # 批量 PDF 提取
            results = extractor.batch_extract_pdfs(
                pdf_dir=args.input,
                pattern=args.pattern,
                dry_run=args.dry_run
            )
            print(json.dumps(results, indent=2, ensure_ascii=False))

    finally:
        extractor.close()


if __name__ == '__main__':
    main()
