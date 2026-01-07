#!/usr/bin/env python3
"""
生成文档重构计划
根据文档清单和问题列表,生成详细的重构计划
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class RestructurePlanGenerator:
    """重构计划生成器"""
    
    def __init__(self, inventory_file: str, problems_file: str):
        """初始化生成器"""
        with open(inventory_file, 'r', encoding='utf-8') as f:
            self.inventory = json.load(f)
        
        with open(problems_file, 'r', encoding='utf-8') as f:
            self.problems = json.load(f)
        
        self.plan = {
            "generated_at": datetime.now().isoformat(),
            "rename_plan": [],
            "move_plan": [],
            "archive_plan": [],
            "delete_plan": [],
            "number_conflicts_resolution": [],
            "workflow_mapping": {}
        }
    
    def map_to_workflow_step(self, doc: Dict) -> int:
        """
        根据文档内容确定其在11步工作流程中的位置
        返回工作流程编号(1-11)或0(不属于工作流程)
        """
        title = doc.get('title', '').lower()
        filename = doc.get('filename', '').lower()
        
        # 工作流程步骤映射
        workflow_keywords = {
            1: ['用户档案', '预加载', 'user profile', 'preload'],
            2: ['会话记录', '存储', 'session', 'storage', '对话存储'],
            3: ['会员权限', '权限检查', 'membership', 'permission'],
            4: ['bge', '复杂度分类', 'complexity'],
            5: ['模型选择', 'model selection', '智能模型'],
            6: ['few-shot', 'fewshot', '检索', 'retrieval', '推理时'],
            7: ['dag', '编排', 'orchestration', '模板'],
            8: ['三层检索', 'three layer', 'vector', 'graph', 'constraint'],
            9: ['工具结果', '汇总', 'tool result', 'aggregation'],
            10: ['llm', '深度分析', 'analysis', '综合'],
            11: ['交互记录', 'interaction', 'record', '记录']
        }
        
        # 检查是否匹配工作流程步骤
        for step, keywords in workflow_keywords.items():
            for keyword in keywords:
                if keyword in title or keyword in filename:
                    return step
        
        return 0  # 不属于工作流程步骤
    
    def generate_rename_plan(self):
        """生成重命名计划"""
        print("生成重命名计划...")
        
        # 处理无编号文档
        for doc in self.problems['unnumbered']:
            category = doc['category']
            filename = doc['filename']
            path = doc['path']
            
            # 根据分类确定编号
            if category == '快速开始':
                # 快速开始目录按固定顺序
                order_map = {
                    '安装指南.md': 1,
                    '环境配置.md': 2,
                    '快速开始.md': 3
                }
                new_number = order_map.get(filename, 99)
                new_filename = f"{new_number:02d}-{filename}"
            
            elif category == '开发指南':
                # 开发指南需要判断类型
                if '日志' in filename or '结果' in filename:
                    # 临时文件,标记为删除
                    self.plan['delete_plan'].append({
                        'path': path,
                        'filename': filename,
                        'reason': '临时文件,无长期价值'
                    })
                    continue
                elif '体系' in filename:
                    new_number = 28
                elif '讨论' in filename:
                    new_number = 29
                elif '说明' in filename:
                    new_number = 30
                elif '规划' in filename:
                    new_number = 31
                else:
                    new_number = 99
                new_filename = f"{new_number:02d}-{filename}"
            
            elif category == 'API文档':
                # API文档按类型编号
                if 'API参考文档' in filename:
                    new_number = 1
                elif 'MCP工具API参考' in filename:
                    new_number = 2
                elif 'MCP工具API' in filename:
                    # 这个文件可能重复,需要检查
                    continue
                else:
                    new_number = 99
                new_filename = f"{new_number:02d}-{filename}"
            
            elif category == '部署运维':
                # 部署运维按类型编号
                order_map = {
                    'Docker部署.md': 1,
                    '环境变量配置指南.md': 2,
                    '服务器部署完整指南.md': 4,
                    '生产环境部署指南.md': 5,
                    '数据备份与恢复.md': 6
                }
                new_number = order_map.get(filename, 99)
                new_filename = f"{new_number:02d}-{filename}"
            
            else:
                continue
            
            self.plan['rename_plan'].append({
                'old_path': path,
                'old_filename': filename,
                'new_filename': new_filename,
                'new_number': new_number,
                'category': category
            })
        
        # 处理编号冲突
        for conflict in self.problems['duplicate_numbers']:
            category = conflict['category']
            number = conflict['number']
            files = conflict['files']
            paths = conflict['paths']
            
            # 为冲突的文件重新分配编号
            for i, (file, path) in enumerate(zip(files, paths)):
                if i == 0:
                    # 第一个文件保持原编号
                    continue
                else:
                    # 后续文件递增编号
                    new_number = number + i
                    new_filename = f"{new_number:02d}-{file.split('-', 1)[1]}"
                    
                    self.plan['number_conflicts_resolution'].append({
                        'old_path': path,
                        'old_filename': file,
                        'old_number': number,
                        'new_number': new_number,
                        'new_filename': new_filename,
                        'category': category,
                        'reason': f'解决编号{number}冲突'
                    })
    
    def generate_move_plan(self):
        """生成移动计划"""
        print("生成移动计划...")
        
        for doc in self.problems['misplaced']:
            self.plan['move_plan'].append({
                'path': doc['path'],
                'filename': doc['filename'],
                'from_category': doc['current_category'],
                'to_category': doc['suggested_category'],
                'reason': doc['reason']
            })
    
    def generate_archive_plan(self):
        """生成归档计划"""
        print("生成归档计划...")
        
        # 已归档文档保持不变
        archived_docs = [
            doc for doc in self.inventory['documents']
            if doc.get('number') is not None and doc.get('number') >= 90 and doc['category'] == '核心架构'
        ]
        
        for doc in archived_docs:
            self.plan['archive_plan'].append({
                'path': doc['path'],
                'filename': doc['filename'],
                'status': '已归档',
                'action': '保持不变'
            })
    
    def generate_workflow_mapping(self):
        """生成工作流程映射"""
        print("生成工作流程映射...")
        
        # 为03-代码参考目录的文档生成工作流程映射
        code_ref_docs = [
            doc for doc in self.inventory['documents']
            if doc['category'] == '代码参考'
        ]
        
        for doc in code_ref_docs:
            workflow_step = self.map_to_workflow_step(doc)
            
            if workflow_step > 0:
                # 属于工作流程步骤
                suggested_number = workflow_step + 1  # +1因为01是框架接口
                
                self.plan['workflow_mapping'][doc['filename']] = {
                    'current_path': doc['path'],
                    'current_number': doc.get('number'),
                    'workflow_step': workflow_step,
                    'suggested_number': suggested_number,
                    'needs_renumber': doc.get('number') != suggested_number
                }
            else:
                # 不属于工作流程,归类为核心组件(20+)
                self.plan['workflow_mapping'][doc['filename']] = {
                    'current_path': doc['path'],
                    'current_number': doc.get('number'),
                    'workflow_step': 0,
                    'category': '核心组件',
                    'suggested_number_range': '20-29'
                }
    
    def generate_plan(self) -> Dict:
        """生成完整的重构计划"""
        print("开始生成重构计划...")
        
        self.generate_rename_plan()
        self.generate_move_plan()
        self.generate_archive_plan()
        self.generate_workflow_mapping()
        
        # 添加统计信息
        self.plan['statistics'] = {
            'total_documents': self.inventory['total_documents'],
            'unnumbered_count': len(self.problems['unnumbered']),
            'conflicts_count': len(self.problems['duplicate_numbers']),
            'misplaced_count': len(self.problems['misplaced']),
            'to_rename': len(self.plan['rename_plan']),
            'to_move': len(self.plan['move_plan']),
            'to_delete': len(self.plan['delete_plan']),
            'conflicts_to_resolve': len(self.plan['number_conflicts_resolution'])
        }
        
        print("重构计划生成完成!")
        return self.plan
    
    def save_plan(self, output_file: str):
        """保存重构计划到文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.plan, f, ensure_ascii=False, indent=2)
        print(f"重构计划已保存到: {output_file}")
    
    def generate_markdown_report(self, output_file: str):
        """生成Markdown格式的重构计划报告"""
        lines = [
            "# 文档重构计划",
            "",
            f"**生成时间**: {self.plan['generated_at']}",
            "",
            "## 统计信息",
            "",
            f"- 文档总数: {self.plan['statistics']['total_documents']}",
            f"- 无编号文档: {self.plan['statistics']['unnumbered_count']}",
            f"- 编号冲突: {self.plan['statistics']['conflicts_count']}",
            f"- 放错位置: {self.plan['statistics']['misplaced_count']}",
            f"- 需要重命名: {self.plan['statistics']['to_rename']}",
            f"- 需要移动: {self.plan['statistics']['to_move']}",
            f"- 需要删除: {self.plan['statistics']['to_delete']}",
            f"- 需要解决冲突: {self.plan['statistics']['conflicts_to_resolve']}",
            "",
            "---",
            ""
        ]
        
        # 重命名计划
        if self.plan['rename_plan']:
            lines.extend([
                "## 1. 重命名计划",
                "",
                "| 原文件名 | 新文件名 | 新编号 | 分类 |",
                "|---------|---------|--------|------|"
            ])
            
            for item in self.plan['rename_plan']:
                lines.append(
                    f"| {item['old_filename']} | {item['new_filename']} | "
                    f"{item['new_number']:02d} | {item['category']} |"
                )
            
            lines.extend(["", ""])
        
        # 编号冲突解决
        if self.plan['number_conflicts_resolution']:
            lines.extend([
                "## 2. 编号冲突解决",
                "",
                "| 原文件名 | 原编号 | 新编号 | 新文件名 | 原因 |",
                "|---------|--------|--------|---------|------|"
            ])
            
            for item in self.plan['number_conflicts_resolution']:
                lines.append(
                    f"| {item['old_filename']} | {item['old_number']:02d} | "
                    f"{item['new_number']:02d} | {item['new_filename']} | {item['reason']} |"
                )
            
            lines.extend(["", ""])
        
        # 移动计划
        if self.plan['move_plan']:
            lines.extend([
                "## 3. 移动计划",
                "",
                "| 文件名 | 当前分类 | 目标分类 | 原因 |",
                "|--------|---------|---------|------|"
            ])
            
            for item in self.plan['move_plan']:
                lines.append(
                    f"| {item['filename']} | {item['from_category']} | "
                    f"{item['to_category']} | {item['reason']} |"
                )
            
            lines.extend(["", ""])
        
        # 删除计划
        if self.plan['delete_plan']:
            lines.extend([
                "## 4. 删除计划",
                "",
                "| 文件名 | 原因 |",
                "|--------|------|"
            ])
            
            for item in self.plan['delete_plan']:
                lines.append(f"| {item['filename']} | {item['reason']} |")
            
            lines.extend(["", ""])
        
        # 工作流程映射
        if self.plan['workflow_mapping']:
            lines.extend([
                "## 5. 工作流程映射(03-代码参考)",
                "",
                "| 文件名 | 当前编号 | 工作流程步骤 | 建议编号 | 需要重编号 |",
                "|--------|---------|-------------|---------|-----------|"
            ])
            
            for filename, mapping in sorted(
                self.plan['workflow_mapping'].items(),
                key=lambda x: x[1].get('suggested_number', 99)
            ):
                workflow_step = mapping.get('workflow_step', 0)
                if workflow_step > 0:
                    lines.append(
                        f"| {filename} | {mapping.get('current_number', 'N/A'):02d} | "
                        f"步骤{workflow_step} | {mapping['suggested_number']:02d} | "
                        f"{'是' if mapping['needs_renumber'] else '否'} |"
                    )
                else:
                    lines.append(
                        f"| {filename} | {mapping.get('current_number', 'N/A'):02d} | "
                        f"核心组件 | {mapping['suggested_number_range']} | - |"
                    )
            
            lines.extend(["", ""])
        
        # 归档文档
        if self.plan['archive_plan']:
            lines.extend([
                "## 6. 归档文档",
                "",
                "| 文件名 | 状态 | 操作 |",
                "|--------|------|------|"
            ])
            
            for item in self.plan['archive_plan']:
                lines.append(
                    f"| {item['filename']} | {item['status']} | {item['action']} |"
                )
            
            lines.extend(["", ""])
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"Markdown报告已保存到: {output_file}")


def main():
    """主函数"""
    script_dir = Path(__file__).parent
    
    # 输入文件
    inventory_file = script_dir / "document_inventory.json"
    problems_file = script_dir / "problem_documents.json"
    
    # 输出文件
    plan_json = script_dir / "restructure_plan.json"
    plan_md = script_dir / "RESTRUCTURE_PLAN.md"
    
    # 生成重构计划
    generator = RestructurePlanGenerator(str(inventory_file), str(problems_file))
    plan = generator.generate_plan()
    
    # 保存计划
    generator.save_plan(str(plan_json))
    generator.generate_markdown_report(str(plan_md))
    
    print("\n✅ 重构计划生成完成!")
    print(f"   - JSON格式: {plan_json}")
    print(f"   - Markdown格式: {plan_md}")


if __name__ == "__main__":
    main()
