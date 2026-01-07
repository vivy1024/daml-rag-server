#!/usr/bin/env python3
"""
重构计划生成器 - 生成详细的文档重构计划
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


class RestructurePlanner:
    """重构计划生成器"""
    
    def __init__(self, inventory_file: str, problems_file: str):
        # 加载文档清单
        with open(inventory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.documents = data['documents']
        
        # 加载问题列表
        with open(problems_file, 'r', encoding='utf-8') as f:
            self.problems = json.load(f)
        
        # 初始化重构计划
        self.plan = {
            'rename': [],      # 重命名计划
            'move': [],        # 移动计划
            'archive': [],     # 归档计划
            'delete': [],      # 删除计划
            'update': [],      # 更新计划
            'create': []       # 创建计划
        }
    
    def generate_plan(self):
        """生成完整重构计划"""
        print("📋 开始生成重构计划...")
        
        self._plan_numbering()
        self._plan_conflict_resolution()
        self._plan_temporary_files()
        self._plan_missing_docs()
        
        print("✅ 重构计划生成完成")
    
    def _plan_numbering(self):
        """规划文档编号"""
        print("\n🔢 规划文档编号...")
        
        # 为无编号文档分配编号
        for doc in self.problems['unnumbered']:
            category = doc['category']
            filename = doc['filename']
            path = doc['path']
            
            # 根据分类确定编号策略
            if category == '快速开始':
                # 快速开始：01-安装指南, 02-环境配置, 03-快速开始
                number_map = {
                    '安装指南.md': 1,
                    '环境配置.md': 2,
                    '快速开始.md': 3
                }
                new_number = number_map.get(filename, 99)
                new_filename = f"{new_number:02d}-{filename}"
            
            elif category == 'API文档':
                # API文档：01-API参考文档, 02-MCP工具API参考
                number_map = {
                    'API参考文档.md': 1,
                    'MCP工具API参考.md': 2,
                    'MCP工具API.md': 3  # 可能需要合并
                }
                new_number = number_map.get(filename, 99)
                new_filename = f"{new_number:02d}-{filename}"
            
            elif category == '部署运维':
                # 部署运维：01-Docker部署, 02-环境变量配置, 03-知识图谱导入, 04-服务器部署, 05-数据备份
                number_map = {
                    'Docker部署.md': 1,
                    '环境变量配置指南.md': 2,
                    '服务器部署完整指南.md': 4,
                    '生产环境部署指南.md': 5,
                    '数据备份与恢复.md': 6
                }
                new_number = number_map.get(filename, 99)
                new_filename = f"{new_number:02d}-{filename}"
            
            elif category == '开发指南':
                # 开发指南：需要根据内容判断
                if '工作流程日志' in filename or '计划生成结果' in filename:
                    # 临时文件，标记为删除
                    self.plan['delete'].append({
                        'path': path,
                        'filename': filename,
                        'reason': '纯临时日志文件，无长期价值'
                    })
                    continue
                elif '质量保证与专家验证体系' in filename:
                    new_number = 28
                    new_filename = f"{new_number:02d}-{filename}"
                elif 'CONTRAINDICATED_FOR关系增强说明' in filename:
                    new_number = 29
                    new_filename = f"{new_number:02d}-{filename}"
                elif '数据清洗与微调架构规划' in filename:
                    new_number = 30
                    new_filename = f"{new_number:02d}-{filename}"
                elif '运动损伤禁忌症专家讨论' in filename:
                    new_number = 31
                    new_filename = f"{new_number:02d}-{filename}"
                else:
                    continue
            else:
                continue
            
            self.plan['rename'].append({
                'old_path': path,
                'old_filename': filename,
                'new_filename': new_filename,
                'category': category,
                'reason': '添加编号前缀'
            })
        
        print(f"  规划重命名 {len(self.plan['rename'])} 个文档")
        print(f"  规划删除 {len(self.plan['delete'])} 个临时文件")
    
    def _plan_conflict_resolution(self):
        """规划编号冲突解决"""
        print("\n🔧 规划编号冲突解决...")
        
        for conflict in self.problems['duplicate_numbers']:
            category = conflict['category']
            number = conflict['number']
            files = conflict['files']
            paths = conflict['paths']
            
            print(f"  处理 {category} 编号{number:02d} 冲突:")
            
            # 开发指南的编号23冲突
            if category == '开发指南' and number == 23:
                # 保留 23-性能优化指南.md
                # 重命名 23-MCP工具参数问题修复.md -> 32-MCP工具参数问题修复.md
                for i, filename in enumerate(files):
                    if 'MCP工具参数问题修复' in filename:
                        self.plan['rename'].append({
                            'old_path': paths[i],
                            'old_filename': filename,
                            'new_filename': '32-MCP工具参数问题修复.md',
                            'category': category,
                            'reason': f'解决编号{number}冲突'
                        })
                        print(f"    - {filename} -> 32-MCP工具参数问题修复.md")
            
            # 开发指南的编号24冲突
            elif category == '开发指南' and number == 24:
                # 保留 24-监控和可观测性指南.md
                # 重命名 24-安全性增强指南.md -> 33-安全性增强指南.md
                for i, filename in enumerate(files):
                    if '安全性增强指南' in filename:
                        self.plan['rename'].append({
                            'old_path': paths[i],
                            'old_filename': filename,
                            'new_filename': '33-安全性增强指南.md',
                            'category': category,
                            'reason': f'解决编号{number}冲突'
                        })
                        print(f"    - {filename} -> 33-安全性增强指南.md")
        
        print(f"  规划解决 {len(self.problems['duplicate_numbers'])} 个编号冲突")
    
    def _plan_temporary_files(self):
        """规划临时文件处理"""
        print("\n📝 规划临时文件处理...")
        
        # 分析临时文件，决定保留、整合还是删除
        for doc in self.problems['temporary']:
            filename = doc['filename']
            path = doc['path']
            category = doc['category']
            status = doc['status']
            
            # 已经在删除计划中的跳过
            if any(d['path'] == path for d in self.plan['delete']):
                continue
            
            # 快速开始的文档都保留（需要添加编号）
            if category == '快速开始':
                continue
            
            # 判断是否需要删除
            if filename in ['工作流程日志.md', '计划生成结果.md']:
                # 已在_plan_numbering中处理
                continue
            
            # 其他临时文件标记为需要审查
            self.plan['update'].append({
                'path': path,
                'filename': filename,
                'category': category,
                'action': 'review_and_integrate',
                'reason': '临时文件，需要审查内容并决定是否整合到正式文档'
            })
        
        print(f"  规划审查 {len([d for d in self.plan['update'] if d['action'] == 'review_and_integrate'])} 个临时文件")
    
    def _plan_missing_docs(self):
        """规划缺失文档创建"""
        print("\n📄 规划缺失文档创建...")
        
        # 根据设计文档，规划需要创建的文档
        missing_docs = [
            {
                'category': '核心架构',
                'filename': '04-数据库结构.md',
                'description': '整合Neo4j和Qdrant文档',
                'source': ['11-Neo4j数据库结构.md']
            },
            {
                'category': '核心架构',
                'filename': '05-MCP工具架构.md',
                'description': '整合MCP相关文档',
                'source': ['15-MCP架构演进历史.md', '21-MCP工具部署模式说明.md']
            },
            {
                'category': '核心架构',
                'filename': '06-三段式编排器架构.md',
                'description': '描述三段式编排器架构',
                'source': ['03-完整工作流程.md', '29-三段式编排器参考.md']
            },
            {
                'category': '代码参考',
                'filename': '02-步骤1-用户档案预加载.md',
                'description': '工作流程步骤1的代码参考'
            },
            {
                'category': '代码参考',
                'filename': '03-步骤2-会话记录存储.md',
                'description': '工作流程步骤2的代码参考',
                'source': ['11-对话存储双写策略.md']
            },
            {
                'category': '代码参考',
                'filename': '04-步骤3-会员权限检查.md',
                'description': '工作流程步骤3的代码参考',
                'source': ['10-会员系统集成参考.md']
            },
            {
                'category': '代码参考',
                'filename': '05-步骤4-BGE复杂度分类.md',
                'description': '工作流程步骤4的代码参考'
            },
            {
                'category': '代码参考',
                'filename': '06-步骤5-智能模型选择.md',
                'description': '工作流程步骤5的代码参考'
            },
            {
                'category': '代码参考',
                'filename': '07-步骤6-FewShot检索.md',
                'description': '工作流程步骤6的代码参考',
                'source': ['03-推理时上下文学习参考.md']
            },
            {
                'category': '代码参考',
                'filename': '08-步骤6.5-LLM选择DAG方案.md',
                'description': '工作流程步骤6.5的代码参考',
                'source': ['27-LLM决策引擎参考.md']
            },
            {
                'category': '代码参考',
                'filename': '09-步骤7-DAG编排器.md',
                'description': '工作流程步骤7的代码参考',
                'source': ['26-DAG模板系统参考.md', '29-三段式编排器参考.md']
            },
            {
                'category': '代码参考',
                'filename': '10-步骤8-三层检索.md',
                'description': '工作流程步骤8的代码参考',
                'source': ['15-企业级三层检索引擎参考.md', '23-retrieval检索引擎参考.md']
            },
            {
                'category': '代码参考',
                'filename': '11-步骤9-工具结果汇总.md',
                'description': '工作流程步骤9的代码参考'
            },
            {
                'category': '代码参考',
                'filename': '12-步骤10-LLM深度分析.md',
                'description': '工作流程步骤10的代码参考',
                'source': ['28-LLM综合分析引擎参考.md']
            },
            {
                'category': '代码参考',
                'filename': '13-步骤11-交互记录.md',
                'description': '工作流程步骤11的代码参考',
                'source': ['11-对话存储双写策略.md']
            },
            {
                'category': '代码参考',
                'filename': '20-核心组件-缓存系统.md',
                'description': '缓存系统代码参考',
                'source': ['30-智能缓存系统参考.md']
            },
            {
                'category': '代码参考',
                'filename': '21-核心组件-监控系统.md',
                'description': '监控系统代码参考',
                'source': ['31-性能监控系统参考.md']
            },
            {
                'category': '代码参考',
                'filename': '22-核心组件-可视化系统.md',
                'description': '可视化系统代码参考',
                'source': ['32-DAG可视化和调试系统参考.md']
            },
            {
                'category': '开发指南',
                'filename': '02-MCP工具开发指南.md',
                'description': 'MCP工具开发指南'
            },
            {
                'category': '开发指南',
                'filename': '03-三层检索使用指南.md',
                'description': '三层检索使用指南'
            }
        ]
        
        for doc in missing_docs:
            self.plan['create'].append(doc)
        
        print(f"  规划创建 {len(self.plan['create'])} 个新文档")
    
    def save_plan(self, output_file: str):
        """保存重构计划"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.plan, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 重构计划已保存到: {output_file}")
    
    def print_summary(self):
        """打印计划摘要"""
        print("\n" + "="*60)
        print("📊 重构计划摘要")
        print("="*60)
        
        print(f"\n📝 重命名: {len(self.plan['rename'])}个文档")
        print(f"📁 移动: {len(self.plan['move'])}个文档")
        print(f"📦 归档: {len(self.plan['archive'])}个文档")
        print(f"🗑️  删除: {len(self.plan['delete'])}个文档")
        print(f"✏️  更新: {len(self.plan['update'])}个文档")
        print(f"➕ 创建: {len(self.plan['create'])}个文档")
        
        # 详细列出重命名计划
        if self.plan['rename']:
            print("\n📝 重命名计划:")
            for item in self.plan['rename'][:10]:  # 只显示前10个
                print(f"  [{item['category']}] {item['old_filename']} -> {item['new_filename']}")
            if len(self.plan['rename']) > 10:
                print(f"  ... 还有 {len(self.plan['rename']) - 10} 个")
        
        # 详细列出删除计划
        if self.plan['delete']:
            print("\n🗑️  删除计划:")
            for item in self.plan['delete']:
                print(f"  {item['filename']} - {item['reason']}")
        
        # 详细列出创建计划
        if self.plan['create']:
            print("\n➕ 创建计划:")
            for item in self.plan['create'][:10]:  # 只显示前10个
                print(f"  [{item['category']}] {item['filename']} - {item['description']}")
            if len(self.plan['create']) > 10:
                print(f"  ... 还有 {len(self.plan['create']) - 10} 个")
        
        print("\n" + "="*60)


def main():
    """主函数"""
    script_dir = Path(__file__).parent
    inventory_file = script_dir / "document_inventory.json"
    problems_file = script_dir / "problem_documents.json"
    
    if not inventory_file.exists():
        print(f"❌ 文档清单不存在: {inventory_file}")
        return
    
    if not problems_file.exists():
        print(f"❌ 问题列表不存在: {problems_file}")
        return
    
    # 创建规划器并生成计划
    planner = RestructurePlanner(str(inventory_file), str(problems_file))
    planner.generate_plan()
    
    # 保存结果
    output_file = script_dir / "restructure_plan.json"
    planner.save_plan(str(output_file))
    
    # 打印摘要
    planner.print_summary()


if __name__ == "__main__":
    main()
