#!/usr/bin/env python3
"""
问题文档识别器 - 识别临时文件、编号冲突、过时内容、放错位置的文档
"""
import json
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict


class ProblemIdentifier:
    """问题文档识别器"""
    
    def __init__(self, inventory_file: str):
        with open(inventory_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.documents = data['documents']
        
        self.problems = {
            'unnumbered': [],
            'number_conflicts': [],
            'outdated': [],
            'misplaced': [],
            'temporary': [],
            'missing_version': [],
            'duplicate_numbers': []
        }
    
    def identify_all_problems(self):
        """识别所有问题"""
        print("🔍 开始识别问题文档...")
        
        self._identify_unnumbered()
        self._identify_number_conflicts()
        self._identify_outdated()
        self._identify_misplaced()
        self._identify_temporary()
        self._identify_missing_version()
        
        print("✅ 问题识别完成")
    
    def _identify_unnumbered(self):
        """识别无编号文档"""
        print("\n📋 识别无编号文档...")
        
        for doc in self.documents:
            if not doc['is_numbered']:
                # 排除特殊文件
                special_files = ['README.md', 'API_USAGE.md', 'Docker部署.md']
                if doc['filename'] not in special_files:
                    self.problems['unnumbered'].append({
                        'path': doc['path'],
                        'filename': doc['filename'],
                        'category': doc['category'],
                        'reason': '缺少编号前缀'
                    })
        
        print(f"  找到 {len(self.problems['unnumbered'])} 个无编号文档")
    
    def _identify_number_conflicts(self):
        """识别编号冲突"""
        print("\n🔢 识别编号冲突...")
        
        # 按分类统计编号
        category_numbers = defaultdict(list)
        for doc in self.documents:
            if doc['is_numbered'] and doc['number'] is not None:
                category_numbers[doc['category']].append({
                    'number': doc['number'],
                    'filename': doc['filename'],
                    'path': doc['path']
                })
        
        # 检查每个分类中的编号冲突
        for category, docs in category_numbers.items():
            number_count = defaultdict(list)
            for doc in docs:
                number_count[doc['number']].append(doc)
            
            # 找出重复的编号
            for number, doc_list in number_count.items():
                if len(doc_list) > 1:
                    self.problems['duplicate_numbers'].append({
                        'category': category,
                        'number': number,
                        'files': [d['filename'] for d in doc_list],
                        'paths': [d['path'] for d in doc_list]
                    })
        
        print(f"  找到 {len(self.problems['duplicate_numbers'])} 个编号冲突")
    
    def _identify_outdated(self):
        """识别过时内容"""
        print("\n⏰ 识别过时内容...")
        
        # 根据文档内容和状态判断是否过时
        outdated_keywords = [
            '已归档',
            '已废弃',
            '不再使用',
            'deprecated'
        ]
        
        for doc in self.documents:
            # 检查文件名
            if any(keyword in doc['filename'] for keyword in outdated_keywords):
                if doc['number'] is None or doc['number'] < 90:
                    self.problems['outdated'].append({
                        'path': doc['path'],
                        'filename': doc['filename'],
                        'reason': '文件名包含过时标记但未归档（应使用90-99编号）'
                    })
            
            # 检查状态
            if doc['status'] and '已归档' in doc['status']:
                if doc['number'] is None or doc['number'] < 90:
                    self.problems['outdated'].append({
                        'path': doc['path'],
                        'filename': doc['filename'],
                        'reason': '状态标记为已归档但未使用90-99编号'
                    })
        
        print(f"  找到 {len(self.problems['outdated'])} 个过时文档")
    
    def _identify_misplaced(self):
        """识别放错位置的文档"""
        print("\n📁 识别放错位置的文档...")
        
        # 定义文档分类规则
        classification_rules = {
            '核心架构': ['架构', '系统', '工作流程', '数据库', 'MCP架构', '技术栈', '接口设计', '目录结构'],
            '代码参考': ['参考', '实现', '引擎', '客户端', '检索', 'DAG', 'LLM', '缓存', '监控'],
            '开发指南': ['指南', '报告', '验证', '评审', '总结', '设计', '说明', '讨论', '体系', '规划'],
            'API文档': ['API', '接口'],
            '部署运维': ['部署', '配置', '导入', '备份', '恢复', '环境变量'],
        }
        
        for doc in self.documents:
            title = doc['title']
            current_category = doc['category']
            
            # 跳过快速开始分类
            if current_category == '快速开始':
                continue
            
            # 检查标题是否更适合其他分类
            suggested_category = None
            max_match_count = 0
            
            for category, keywords in classification_rules.items():
                if category == current_category:
                    continue
                
                match_count = sum(1 for keyword in keywords if keyword in title)
                if match_count > max_match_count:
                    max_match_count = match_count
                    suggested_category = category
            
            # 如果有更合适的分类
            if suggested_category and max_match_count >= 2:
                self.problems['misplaced'].append({
                    'path': doc['path'],
                    'filename': doc['filename'],
                    'current_category': current_category,
                    'suggested_category': suggested_category,
                    'reason': f'标题更符合"{suggested_category}"分类'
                })
        
        print(f"  找到 {len(self.problems['misplaced'])} 个可能放错位置的文档")
    
    def _identify_temporary(self):
        """识别临时文件"""
        print("\n⚠️  识别临时文件...")
        
        for doc in self.documents:
            if doc['is_temporary']:
                self.problems['temporary'].append({
                    'path': doc['path'],
                    'filename': doc['filename'],
                    'category': doc['category'],
                    'has_version': doc['has_version_info'],
                    'status': doc['status']
                })
        
        print(f"  找到 {len(self.problems['temporary'])} 个临时文件")
    
    def _identify_missing_version(self):
        """识别缺少版本信息的文档"""
        print("\n📌 识别缺少版本信息的文档...")
        
        for doc in self.documents:
            if not doc['has_version_info'] and not doc['is_temporary']:
                self.problems['missing_version'].append({
                    'path': doc['path'],
                    'filename': doc['filename'],
                    'category': doc['category']
                })
        
        print(f"  找到 {len(self.problems['missing_version'])} 个缺少版本信息的文档")
    
    def save_problems(self, output_file: str):
        """保存问题列表"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.problems, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 问题列表已保存到: {output_file}")
    
    def print_summary(self):
        """打印问题摘要"""
        print("\n" + "="*60)
        print("📊 问题文档统计")
        print("="*60)
        
        total_problems = sum(len(v) for v in self.problems.values())
        print(f"\n总问题数: {total_problems}")
        
        print("\n问题分类:")
        print(f"  ❌ 无编号文档: {len(self.problems['unnumbered'])}个")
        print(f"  🔢 编号冲突: {len(self.problems['duplicate_numbers'])}个")
        print(f"  ⏰ 过时文档: {len(self.problems['outdated'])}个")
        print(f"  📁 放错位置: {len(self.problems['misplaced'])}个")
        print(f"  ⚠️  临时文件: {len(self.problems['temporary'])}个")
        print(f"  📌 缺少版本信息: {len(self.problems['missing_version'])}个")
        
        # 详细列出编号冲突
        if self.problems['duplicate_numbers']:
            print("\n🔢 编号冲突详情:")
            for conflict in self.problems['duplicate_numbers']:
                print(f"  {conflict['category']} - 编号{conflict['number']:02d}:")
                for filename in conflict['files']:
                    print(f"    - {filename}")
        
        # 详细列出无编号文档
        if self.problems['unnumbered']:
            print("\n❌ 无编号文档列表:")
            for doc in self.problems['unnumbered']:
                print(f"  [{doc['category']}] {doc['filename']}")
        
        # 详细列出临时文件
        if self.problems['temporary']:
            print("\n⚠️  临时文件列表:")
            for doc in self.problems['temporary']:
                status = doc['status'] if doc['status'] else '无状态'
                print(f"  [{doc['category']}] {doc['filename']} - {status}")
        
        print("\n" + "="*60)


def main():
    """主函数"""
    script_dir = Path(__file__).parent
    inventory_file = script_dir / "document_inventory.json"
    
    if not inventory_file.exists():
        print(f"❌ 文档清单不存在: {inventory_file}")
        print("请先运行 document_scanner.py")
        return
    
    # 创建识别器并识别问题
    identifier = ProblemIdentifier(str(inventory_file))
    identifier.identify_all_problems()
    
    # 保存结果
    output_file = script_dir / "problem_documents.json"
    identifier.save_problems(str(output_file))
    
    # 打印摘要
    identifier.print_summary()


if __name__ == "__main__":
    main()
