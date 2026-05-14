#!/usr/bin/env python3
"""
文档结构验证脚本
验证DAML-RAG文档目录结构的完整性、分类一致性、引用链接有效性和格式规范性
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ValidationResult:
    """验证结果"""
    passed: bool
    message: str
    details: List[str] = field(default_factory=list)


class DocsValidator:
    """文档验证器"""
    
    def __init__(self, docs_root: str):
        self.docs_root = Path(docs_root)
        self.results = {
            'structure': [],
            'classification': [],
            'references': [],
            'format': []
        }
        
    def validate_all(self) -> Dict[str, List[ValidationResult]]:
        """运行所有验证"""
        print("=" * 80)
        print("DAML-RAG 文档结构验证")
        print("=" * 80)
        print()
        
        self.validate_directory_structure()
        self.validate_document_classification()
        self.validate_references()
        self.validate_document_format()
        
        return self.results
    
    def validate_directory_structure(self):
        """验证目录结构完整性"""
        print("📁 验证目录结构...")
        print("-" * 80)
        
        # 定义必需的目录结构
        required_structure = {
            '02-核心架构': [
                '01-系统架构',
                '02-数据层',
                '03-编排层',
                '04-LLM层',
                '05-监控层',
                '06-优化层'
            ],
            '03-代码参考': [
                '01-工作流程步骤',
                '02-核心组件',
                '03-MCP工具实现',
                '04-DAG模板实现',
                '05-流式输出'
            ],
            '04-开发指南': [
                '01-快速上手',
                '02-工具使用',
                '03-配置管理',
                '04-最佳实践'
            ]
        }
        
        # 检查主目录
        for main_dir, sub_dirs in required_structure.items():
            main_path = self.docs_root / main_dir
            
            if not main_path.exists():
                self.results['structure'].append(ValidationResult(
                    passed=False,
                    message=f"❌ 缺少主目录: {main_dir}",
                    details=[]
                ))
                continue
            
            # 检查主目录README
            main_readme = main_path / 'README.md'
            if not main_readme.exists():
                self.results['structure'].append(ValidationResult(
                    passed=False,
                    message=f"❌ 缺少README: {main_dir}/README.md",
                    details=[]
                ))
            else:
                self.results['structure'].append(ValidationResult(
                    passed=True,
                    message=f"✅ {main_dir}/README.md 存在",
                    details=[]
                ))
            
            # 检查子目录
            for sub_dir in sub_dirs:
                sub_path = main_path / sub_dir
                
                if not sub_path.exists():
                    self.results['structure'].append(ValidationResult(
                        passed=False,
                        message=f"❌ 缺少子目录: {main_dir}/{sub_dir}",
                        details=[]
                    ))
                    continue
                
                # 检查子目录README
                sub_readme = sub_path / 'README.md'
                if not sub_readme.exists():
                    self.results['structure'].append(ValidationResult(
                        passed=False,
                        message=f"❌ 缺少README: {main_dir}/{sub_dir}/README.md",
                        details=[]
                    ))
                else:
                    self.results['structure'].append(ValidationResult(
                        passed=True,
                        message=f"✅ {main_dir}/{sub_dir}/README.md 存在",
                        details=[]
                    ))
        
        # 检查目录命名规范
        self._check_naming_convention()
        
        print()
    
    def _check_naming_convention(self):
        """检查目录命名规范"""
        pattern = re.compile(r'^\d{2}-[\u4e00-\u9fa5a-zA-Z]+$')
        
        for main_dir in ['02-核心架构', '03-代码参考', '04-开发指南']:
            main_path = self.docs_root / main_dir
            if not main_path.exists():
                continue
            
            for item in main_path.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    if not pattern.match(item.name):
                        self.results['structure'].append(ValidationResult(
                            passed=False,
                            message=f"❌ 目录命名不符合规范: {main_dir}/{item.name}",
                            details=["应使用格式: 数字-中文名称 (如: 01-系统架构)"]
                        ))
    
    def validate_document_classification(self):
        """验证文档分类一致性"""
        print("📋 验证文档分类...")
        print("-" * 80)
        
        classification_rules = {
            '02-核心架构': {
                'keywords': ['架构', '设计', '理念', 'What', 'Why', '总览', '结构'],
                'anti_keywords': ['代码实现', '使用指南', '配置步骤', 'How to']
            },
            '03-代码参考': {
                'keywords': ['代码', '实现', '算法', 'How', '函数', '类', '模块'],
                'anti_keywords': ['使用指南', '配置说明', '操作步骤']
            },
            '04-开发指南': {
                'keywords': ['使用', '指南', '配置', '操作', '步骤', 'How to'],
                'anti_keywords': ['架构设计', '代码实现', '算法']
            }
        }
        
        for main_dir, rules in classification_rules.items():
            main_path = self.docs_root / main_dir
            if not main_path.exists():
                continue
            
            # 递归检查所有.md文件
            for md_file in main_path.rglob('*.md'):
                if md_file.name == 'README.md':
                    continue
                
                try:
                    content = md_file.read_text(encoding='utf-8')
                    relative_path = md_file.relative_to(self.docs_root)
                    
                    # 检查是否包含反关键词
                    found_anti = []
                    for anti_kw in rules['anti_keywords']:
                        if anti_kw.lower() in content.lower():
                            found_anti.append(anti_kw)
                    
                    if found_anti:
                        self.results['classification'].append(ValidationResult(
                            passed=False,
                            message=f"⚠️  文档可能分类错误: {relative_path}",
                            details=[f"包含不应出现的关键词: {', '.join(found_anti)}"]
                        ))
                    else:
                        self.results['classification'].append(ValidationResult(
                            passed=True,
                            message=f"✅ {relative_path} 分类正确",
                            details=[]
                        ))
                
                except Exception as e:
                    self.results['classification'].append(ValidationResult(
                        passed=False,
                        message=f"❌ 无法读取文件: {relative_path}",
                        details=[str(e)]
                    ))
        
        print()
    
    def validate_references(self):
        """验证引用链接有效性"""
        print("🔗 验证引用链接...")
        print("-" * 80)
        
        # 匹配Markdown链接: [text](path)
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        
        for md_file in self.docs_root.rglob('*.md'):
            try:
                content = md_file.read_text(encoding='utf-8')
                relative_path = md_file.relative_to(self.docs_root)
                
                links = link_pattern.findall(content)
                
                for link_text, link_path in links:
                    # 跳过外部链接
                    if link_path.startswith('http://') or link_path.startswith('https://'):
                        continue
                    
                    # 跳过锚点链接
                    if link_path.startswith('#'):
                        continue
                    
                    # 解析相对路径
                    target_path = (md_file.parent / link_path).resolve()
                    
                    if not target_path.exists():
                        self.results['references'].append(ValidationResult(
                            passed=False,
                            message=f"❌ 断链: {relative_path}",
                            details=[
                                f"链接文本: {link_text}",
                                f"目标路径: {link_path}",
                                f"解析路径: {target_path}"
                            ]
                        ))
            
            except Exception as e:
                self.results['references'].append(ValidationResult(
                    passed=False,
                    message=f"❌ 无法验证引用: {md_file.relative_to(self.docs_root)}",
                    details=[str(e)]
                ))
        
        print()
    
    def validate_document_format(self):
        """验证文档格式规范性"""
        print("📝 验证文档格式...")
        print("-" * 80)
        
        # 必需的元数据
        version_pattern = re.compile(r'\*\*版本\*\*:\s*v?\d+\.\d+\.\d+')
        date_pattern = re.compile(r'\*\*创建日期\*\*:\s*\d{4}-\d{2}-\d{2}')
        status_pattern = re.compile(r'\*\*状态\*\*:\s*(✅|📋|🚧|🎉|🔄)')
        
        for md_file in self.docs_root.rglob('*.md'):
            if md_file.name == 'README.md':
                continue
            
            try:
                content = md_file.read_text(encoding='utf-8')
                relative_path = md_file.relative_to(self.docs_root)
                
                # 只检查前500个字符（元数据通常在开头）
                header = content[:500]
                
                issues = []
                
                if not version_pattern.search(header):
                    issues.append("缺少版本号")
                
                if not date_pattern.search(header):
                    issues.append("缺少创建日期")
                
                if not status_pattern.search(header):
                    issues.append("缺少状态标记")
                
                if issues:
                    self.results['format'].append(ValidationResult(
                        passed=False,
                        message=f"⚠️  格式不完整: {relative_path}",
                        details=issues
                    ))
                else:
                    self.results['format'].append(ValidationResult(
                        passed=True,
                        message=f"✅ {relative_path} 格式正确",
                        details=[]
                    ))
            
            except Exception as e:
                self.results['format'].append(ValidationResult(
                    passed=False,
                    message=f"❌ 无法验证格式: {md_file.relative_to(self.docs_root)}",
                    details=[str(e)]
                ))
        
        print()
    
    def generate_report(self) -> str:
        """生成验证报告"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("DAML-RAG 文档验证报告")
        report_lines.append("=" * 80)
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        categories = [
            ('structure', '📁 目录结构验证'),
            ('classification', '📋 文档分类验证'),
            ('references', '🔗 引用链接验证'),
            ('format', '📝 文档格式验证')
        ]
        
        total_passed = 0
        total_failed = 0
        
        for category, title in categories:
            results = self.results[category]
            passed = sum(1 for r in results if r.passed)
            failed = sum(1 for r in results if not r.passed)
            
            total_passed += passed
            total_failed += failed
            
            report_lines.append(f"\n{title}")
            report_lines.append("-" * 80)
            report_lines.append(f"通过: {passed} | 失败: {failed}")
            report_lines.append("")
            
            # 只显示失败的结果
            for result in results:
                if not result.passed:
                    report_lines.append(result.message)
                    for detail in result.details:
                        report_lines.append(f"  - {detail}")
        
        # 总结
        report_lines.append("\n" + "=" * 80)
        report_lines.append("验证总结")
        report_lines.append("=" * 80)
        report_lines.append(f"总通过: {total_passed}")
        report_lines.append(f"总失败: {total_failed}")
        
        if total_failed == 0:
            report_lines.append("\n✅ 所有验证通过！文档结构符合规范。")
        else:
            report_lines.append(f"\n⚠️  发现 {total_failed} 个问题，请修复后重新验证。")
        
        report_lines.append("")
        
        return "\n".join(report_lines)


def main():
    """主函数"""
    # 获取docs目录路径
    script_dir = Path(__file__).parent
    docs_root = script_dir.parent / 'docs'
    
    if not docs_root.exists():
        print(f"❌ 错误: 找不到docs目录: {docs_root}")
        return 1
    
    # 创建验证器并运行
    validator = DocsValidator(str(docs_root))
    validator.validate_all()
    
    # 生成报告
    report = validator.generate_report()
    print(report)
    
    # 保存报告
    report_path = docs_root / '07-测试报告' / '10-文档结构验证报告.md'
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# DAML-RAG 文档结构验证报告\n\n")
        f.write(f"**版本**: v1.0.0\n")
        f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**状态**: ✅ 已完成\n\n")
        f.write("---\n\n")
        f.write("```\n")
        f.write(report)
        f.write("\n```\n")
    
    print(f"\n📄 验证报告已保存到: {report_path}")
    
    # 返回状态码
    total_failed = sum(
        sum(1 for r in results if not r.passed)
        for results in validator.results.values()
    )
    
    return 0 if total_failed == 0 else 1


if __name__ == '__main__':
    exit(main())
