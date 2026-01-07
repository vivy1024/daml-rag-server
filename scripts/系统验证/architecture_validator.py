#!/usr/bin/env python3
"""
架构验证脚本
用于验证框架层与应用层的职责分离
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ValidationIssue:
    """验证问题"""
    file_path: str
    issue_type: str
    severity: str  # "high", "medium", "low"
    description: str
    line_number: int = 0


@dataclass
class ArchitectureReport:
    """架构验证报告"""
    timestamp: str
    framework_layer_issues: List[ValidationIssue]
    application_layer_issues: List[ValidationIssue]
    misplaced_files: List[Dict[str, str]]
    deprecated_directories: List[str]
    dependency_violations: List[ValidationIssue]
    summary: Dict[str, int]


class ArchitectureValidator:
    """架构验证器"""
    
    # 健身领域关键词
    FITNESS_KEYWORDS = {
        'exercise', 'muscle', 'fitness', 'training', 'workout',
        'nutrition', 'diet', 'calorie', 'protein', 'carb',
        'rep', 'set', 'weight', 'bodybuilding', 'cardio',
        'strength', 'endurance', 'flexibility', 'injury',
        'recovery', 'periodization', 'hypertrophy', 'athlete'
    }
    
    # 通用组件标识（应该在框架层）
    GENERIC_COMPONENTS = {
        'cache', 'monitor', 'visualizer', 'performance',
        'logger', 'metrics', 'profiler', 'tracer'
    }
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.src_root = self.project_root / "src"
        self.framework_path = self.src_root / "framework"
        self.application_path = self.src_root / "applications" / "fitness"
        
        self.issues: List[ValidationIssue] = []
        self.misplaced_files: List[Dict[str, str]] = []
        self.deprecated_dirs: List[str] = []
        
    def validate_all(self) -> ArchitectureReport:
        """执行所有验证"""
        print("🔍 开始架构验证...")
        print(f"项目根目录: {self.project_root}")
        print(f"框架层路径: {self.framework_path}")
        print(f"应用层路径: {self.application_path}")
        print()
        
        # 1. 验证框架层领域无关性
        print("📋 任务 1.1: 验证框架层领域无关性...")
        self.validate_framework_domain_independence()
        
        # 2. 验证应用层依赖方向
        print("📋 任务 1.2: 验证应用层依赖方向...")
        self.validate_dependency_direction()
        
        # 3. 识别错位文件
        print("📋 任务 1.3: 识别错位文件...")
        self.identify_misplaced_files()
        
        # 4. 检查废弃目录
        print("📋 检查废弃目录...")
        self.check_deprecated_directories()
        
        # 生成报告
        report = self.generate_report()
        
        return report
    
    def validate_framework_domain_independence(self):
        """验证框架层领域无关性（任务1.1）"""
        print("  检查框架层文件...")
        
        if not self.framework_path.exists():
            print(f"  ⚠️  框架层路径不存在: {self.framework_path}")
            return
        
        py_files = list(self.framework_path.rglob("*.py"))
        print(f"  找到 {len(py_files)} 个Python文件")
        
        for file_path in py_files:
            if "__pycache__" in str(file_path):
                continue
                
            self._check_file_for_domain_keywords(file_path, "framework")
        
        framework_issues = [i for i in self.issues if "框架层" in i.description]
        print(f"  ✅ 框架层验证完成，发现 {len(framework_issues)} 个问题")
        print()
    
    def validate_dependency_direction(self):
        """验证应用层依赖方向（任务1.2）"""
        print("  分析导入依赖...")
        
        # 检查框架层是否导入应用层
        if self.framework_path.exists():
            framework_files = list(self.framework_path.rglob("*.py"))
            print(f"  检查 {len(framework_files)} 个框架层文件...")
            
            for file_path in framework_files:
                if "__pycache__" in str(file_path):
                    continue
                self._check_illegal_imports(file_path, "framework")
        
        # 检查应用层导入
        if self.application_path.exists():
            app_files = list(self.application_path.rglob("*.py"))
            print(f"  检查 {len(app_files)} 个应用层文件...")
            
            for file_path in app_files:
                if "__pycache__" in str(file_path):
                    continue
                self._check_illegal_imports(file_path, "application")
        
        dep_issues = [i for i in self.issues if "依赖" in i.description]
        print(f"  ✅ 依赖方向验证完成，发现 {len(dep_issues)} 个问题")
        print()
    
    def identify_misplaced_files(self):
        """识别错位文件（任务1.3）"""
        print("  扫描错位文件...")
        
        # 检查应用层中的通用组件
        if self.application_path.exists():
            app_files = list(self.application_path.glob("*.py"))
            print(f"  检查应用层 {len(app_files)} 个文件...")
            
            for file_path in app_files:
                file_name = file_path.stem
                
                # 检查是否是通用组件
                for keyword in self.GENERIC_COMPONENTS:
                    if keyword in file_name.lower():
                        self.misplaced_files.append({
                            "file": file_path.name,
                            "current_location": "applications/fitness/",
                            "suggested_location": self._suggest_framework_location(file_name),
                            "reason": f"包含通用组件关键词: {keyword}"
                        })
                        
                        self.issues.append(ValidationIssue(
                            file_path=str(file_path.relative_to(self.project_root)),
                            issue_type="misplaced_file",
                            severity="high",
                            description=f"通用组件 {file_path.name} 应该在框架层"
                        ))
                        break
        
        # 检查框架层中的领域特定组件
        if self.framework_path.exists():
            framework_files = list(self.framework_path.rglob("*.py"))
            
            for file_path in framework_files:
                if "__pycache__" in str(file_path) or file_path.name == "__init__.py":
                    continue
                
                # 检查文件名是否包含健身关键词
                file_name_lower = file_path.stem.lower()
                for keyword in self.FITNESS_KEYWORDS:
                    if keyword in file_name_lower:
                        self.misplaced_files.append({
                            "file": file_path.name,
                            "current_location": str(file_path.parent.relative_to(self.src_root)),
                            "suggested_location": "applications/fitness/",
                            "reason": f"包含领域特定关键词: {keyword}"
                        })
                        
                        self.issues.append(ValidationIssue(
                            file_path=str(file_path.relative_to(self.project_root)),
                            issue_type="misplaced_file",
                            severity="high",
                            description=f"领域特定组件 {file_path.name} 应该在应用层"
                        ))
                        break
        
        print(f"  ✅ 错位文件识别完成，发现 {len(self.misplaced_files)} 个错位文件")
        print()
    
    def check_deprecated_directories(self):
        """检查废弃目录"""
        print("  检查废弃目录...")
        
        deprecated_paths = [
            self.application_path / "tools",
            self.application_path / "mcp_server",
            self.application_path / "retrieval"
        ]
        
        for dir_path in deprecated_paths:
            if dir_path.exists():
                files = list(dir_path.rglob("*.py"))
                # 排除__init__.py和__pycache__
                files = [f for f in files if f.name != "__init__.py" and "__pycache__" not in str(f)]
                
                if len(files) == 0:
                    self.deprecated_dirs.append(str(dir_path.relative_to(self.project_root)))
                    print(f"  📁 空目录: {dir_path.relative_to(self.project_root)}")
                else:
                    print(f"  📁 目录包含 {len(files)} 个文件: {dir_path.relative_to(self.project_root)}")
        
        print(f"  ✅ 废弃目录检查完成，发现 {len(self.deprecated_dirs)} 个空目录")
        print()
    
    def _check_file_for_domain_keywords(self, file_path: Path, layer: str):
        """检查文件是否包含领域关键词"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # 检查文件内容
            for keyword in self.FITNESS_KEYWORDS:
                # 使用正则表达式查找关键词（避免误报）
                pattern = r'\b' + keyword + r'\b'
                matches = re.finditer(pattern, content, re.IGNORECASE)
                
                for match in matches:
                    # 计算行号
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # 排除注释和字符串中的关键词（简单检查）
                    line_start = content.rfind('\n', 0, match.start()) + 1
                    line_end = content.find('\n', match.start())
                    if line_end == -1:
                        line_end = len(content)
                    line_content = content[line_start:line_end].strip()
                    
                    # 跳过注释
                    if line_content.startswith('#'):
                        continue
                    
                    self.issues.append(ValidationIssue(
                        file_path=str(file_path.relative_to(self.project_root)),
                        issue_type="domain_keyword",
                        severity="medium",
                        description=f"框架层文件包含健身领域关键词: '{keyword}'",
                        line_number=line_num
                    ))
                    break  # 每个关键词只报告一次
                    
        except Exception as e:
            print(f"  ⚠️  读取文件失败 {file_path}: {e}")
    
    def _check_illegal_imports(self, file_path: Path, layer: str):
        """检查非法导入"""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                if not line.startswith('from ') and not line.startswith('import '):
                    continue
                
                if layer == "framework":
                    # 框架层不应该导入应用层
                    if 'applications.fitness' in line or 'applications/fitness' in line:
                        self.issues.append(ValidationIssue(
                            file_path=str(file_path.relative_to(self.project_root)),
                            issue_type="illegal_import",
                            severity="high",
                            description=f"框架层非法导入应用层: {line}",
                            line_number=line_num
                        ))
                
                elif layer == "application":
                    # 应用层可以导入框架层（这是正常的）
                    pass
                    
        except Exception as e:
            print(f"  ⚠️  读取文件失败 {file_path}: {e}")
    
    def _suggest_framework_location(self, file_name: str) -> str:
        """建议框架层位置"""
        file_name_lower = file_name.lower()
        
        if 'cache' in file_name_lower:
            return "framework/storage/"
        elif 'monitor' in file_name_lower or 'performance' in file_name_lower:
            return "framework/monitoring/"
        elif 'visualizer' in file_name_lower or 'visualize' in file_name_lower:
            return "framework/monitoring/"
        else:
            return "framework/"
    
    def generate_report(self) -> ArchitectureReport:
        """生成验证报告"""
        print("📊 生成架构验证报告...")
        
        # 分类问题
        framework_issues = [i for i in self.issues if "框架层" in i.description]
        application_issues = [i for i in self.issues if "应用层" in i.description]
        dependency_issues = [i for i in self.issues if i.issue_type == "illegal_import"]
        
        report = ArchitectureReport(
            timestamp=datetime.now().isoformat(),
            framework_layer_issues=framework_issues,
            application_layer_issues=application_issues,
            misplaced_files=self.misplaced_files,
            deprecated_directories=self.deprecated_dirs,
            dependency_violations=dependency_issues,
            summary={
                "total_issues": len(self.issues),
                "framework_issues": len(framework_issues),
                "application_issues": len(application_issues),
                "misplaced_files": len(self.misplaced_files),
                "deprecated_directories": len(self.deprecated_dirs),
                "dependency_violations": len(dependency_issues)
            }
        )
        
        return report
    
    def save_report(self, report: ArchitectureReport, output_path: str):
        """保存报告到文件"""
        # 转换为可序列化的格式
        report_dict = {
            "timestamp": report.timestamp,
            "framework_layer_issues": [asdict(i) for i in report.framework_layer_issues],
            "application_layer_issues": [asdict(i) for i in report.application_layer_issues],
            "misplaced_files": report.misplaced_files,
            "deprecated_directories": report.deprecated_directories,
            "dependency_violations": [asdict(i) for i in report.dependency_violations],
            "summary": report.summary
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 报告已保存到: {output_file}")
    
    def print_summary(self, report: ArchitectureReport):
        """打印报告摘要"""
        print("\n" + "="*80)
        print("📊 架构验证报告摘要")
        print("="*80)
        print(f"验证时间: {report.timestamp}")
        print()
        
        print("📈 统计信息:")
        print(f"  总问题数: {report.summary['total_issues']}")
        print(f"  框架层问题: {report.summary['framework_issues']}")
        print(f"  应用层问题: {report.summary['application_issues']}")
        print(f"  错位文件: {report.summary['misplaced_files']}")
        print(f"  废弃目录: {report.summary['deprecated_directories']}")
        print(f"  依赖违规: {report.summary['dependency_violations']}")
        print()
        
        if report.misplaced_files:
            print("🔄 错位文件清单:")
            for item in report.misplaced_files:
                print(f"  📄 {item['file']}")
                print(f"     当前位置: {item['current_location']}")
                print(f"     建议位置: {item['suggested_location']}")
                print(f"     原因: {item['reason']}")
                print()
        
        if report.deprecated_directories:
            print("📁 废弃目录清单:")
            for dir_path in report.deprecated_directories:
                print(f"  🗑️  {dir_path}")
            print()
        
        if report.dependency_violations:
            print("⚠️  依赖违规:")
            for issue in report.dependency_violations[:5]:  # 只显示前5个
                print(f"  ❌ {issue.file_path}:{issue.line_number}")
                print(f"     {issue.description}")
            if len(report.dependency_violations) > 5:
                print(f"  ... 还有 {len(report.dependency_violations) - 5} 个问题")
            print()
        
        print("="*80)


def main():
    """主函数"""
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print("🚀 DAML-RAG 架构验证工具")
    print("="*80)
    print()
    
    # 创建验证器
    validator = ArchitectureValidator(str(project_root))
    
    # 执行验证
    report = validator.validate_all()
    
    # 保存报告
    output_path = project_root / "architecture_validation_report.json"
    validator.save_report(report, str(output_path))
    
    # 打印摘要
    validator.print_summary(report)
    
    print("\n✅ 架构验证完成！")
    print(f"详细报告: {output_path}")


if __name__ == "__main__":
    main()
