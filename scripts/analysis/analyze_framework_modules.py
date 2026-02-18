#!/usr/bin/env python3
"""
分析daml-rag-server框架层模块，识别需要开源的核心代码
"""
import os
import json

def analyze_module(path, module_name):
    """分析单个模块的代码复杂度"""
    files = []
    total_lines = 0
    total_classes = 0
    total_functions = 0
    imports_fitness = False  # 是否依赖fitness领域代码
    
    for root, dirs, filenames in os.walk(path):
        if '__pycache__' in root:
            continue
        for f in filenames:
            if f.endswith('.py'):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as fp:
                        content = fp.read()
                        lines = content.split('\n')
                        total_lines += len(lines)
                        
                        # 统计类和函数
                        for line in lines:
                            if line.strip().startswith('class '):
                                total_classes += 1
                            elif line.strip().startswith('def ') or line.strip().startswith('async def '):
                                total_functions += 1
                            
                            # 检查是否依赖fitness领域代码
                            if 'applications.fitness' in line or 'from applications' in line:
                                imports_fitness = True
                        
                        files.append({
                            'file': f,
                            'lines': len(lines)
                        })
                except:
                    pass
    
    return {
        'module': module_name,
        'file_count': len(files),
        'total_lines': total_lines,
        'classes': total_classes,
        'functions': total_functions,
        'imports_fitness': imports_fitness,
        'files': sorted(files, key=lambda x: -x['lines'])[:5]  # Top 5 largest files
    }

def main():
    # 分析framework层各子目录
    framework_modules = [
        ('adapters', '领域适配器接口'),
        ('auth', '认证授权'),
        ('base', '基础类'),
        ('clients', '客户端（LLM/Neo4j/Qdrant）'),
        ('config', '配置管理'),
        ('core', '核心查询'),
        ('dag', 'DAG执行'),
        ('interfaces', '接口定义'),
        ('mcp', 'MCP协议'),
        ('models', '模型选择'),
        ('monitoring', '监控日志'),
        ('orchestration', 'DAG编排'),
        ('processors', '处理器'),
        ('retrieval', '三层检索'),
        ('skills', 'Skills架构'),
        ('storage', '存储缓存'),
        ('tools', '工具注册'),
        ('utils', '工具函数'),
    ]

    results = []
    for dirname, desc in framework_modules:
        path = f'/app/src/framework/{dirname}'
        if os.path.exists(path):
            result = analyze_module(path, dirname)
            result['description'] = desc
            results.append(result)

    # 输出分析结果
    print('=' * 80)
    print('daml-rag-server 框架层模块分析')
    print('=' * 80)
    print()

    # 按代码行数排序
    results.sort(key=lambda x: -x['total_lines'])

    total_files = 0
    total_lines = 0
    total_classes = 0
    total_functions = 0
    domain_dependent = []
    domain_independent = []

    print(f"{'模块':<15} {'文件':>4} {'代码行':>6} {'类':>4} {'函数':>5} {'状态'}")
    print('-' * 80)
    
    for r in results:
        total_files += r['file_count']
        total_lines += r['total_lines']
        total_classes += r['classes']
        total_functions += r['functions']
        
        status = '⚠️ 依赖fitness' if r['imports_fitness'] else '✅ 领域无关'
        if r['imports_fitness']:
            domain_dependent.append(r['module'])
        else:
            domain_independent.append(r['module'])
        
        print(f"{r['module']:<15} {r['file_count']:>4} {r['total_lines']:>6} {r['classes']:>4} {r['functions']:>5} {status}")

    print()
    print('-' * 80)
    print(f"总计: {total_files}个文件, {total_lines}行代码, {total_classes}个类, {total_functions}个函数")
    print()
    print('领域无关模块（可直接开源）:')
    for m in domain_independent:
        print(f"  - {m}")
    print()
    print('领域依赖模块（需要抽象）:')
    for m in domain_dependent:
        print(f"  - {m}")
    
    # 输出详细的文件列表
    print()
    print('=' * 80)
    print('各模块最大文件（Top 5）')
    print('=' * 80)
    
    for r in results[:10]:  # 只显示前10个模块
        print(f"\n{r['module']} ({r['description']}):")
        for f in r['files'][:3]:
            print(f"  - {f['file']}: {f['lines']}行")

if __name__ == '__main__':
    main()
