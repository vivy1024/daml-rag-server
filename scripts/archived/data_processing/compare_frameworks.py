#!/usr/bin/env python3
"""
对比daml-rag-server和daml-rag-framework的代码差异
"""
import os

def count_module(path):
    """统计模块的文件数和代码行数"""
    files = 0
    lines = 0
    for root, dirs, filenames in os.walk(path):
        if '__pycache__' in root or 'egg-info' in root:
            continue
        for f in filenames:
            if f.endswith('.py'):
                files += 1
                try:
                    with open(os.path.join(root, f), 'r', encoding='utf-8') as fp:
                        lines += len(fp.readlines())
                except:
                    pass
    return files, lines

def main():
    # 定义两个项目的路径
    server_path = '/app/src/framework'
    # framework_path 需要在本地运行，这里用相对路径
    
    # 模块列表
    modules = [
        'adapters',
        'auth',
        'base',
        'clients',
        'config',
        'core',
        'dag',
        'interfaces',
        'mcp',
        'models',
        'monitoring',
        'orchestration',
        'processors',
        'quality',
        'registry',
        'retrieval',
        'skills',
        'storage',
        'tools',
        'utils',
    ]
    
    print('=' * 90)
    print('daml-rag-server vs daml-rag-framework 模块对比')
    print('=' * 90)
    print()
    print(f"{'模块':<15} {'server文件':>10} {'server行':>10} {'framework文件':>12} {'framework行':>12} {'差距'}")
    print('-' * 90)
    
    total_server_files = 0
    total_server_lines = 0
    
    server_only = []
    
    for module in modules:
        server_module_path = f'{server_path}/{module}'
        
        if os.path.exists(server_module_path):
            s_files, s_lines = count_module(server_module_path)
            total_server_files += s_files
            total_server_lines += s_lines
            
            # 标记server独有的模块
            if module in ['auth', 'dag', 'mcp', 'skills']:
                server_only.append(module)
                print(f"{module:<15} {s_files:>10} {s_lines:>10} {'N/A':>12} {'N/A':>12} 🆕 server独有")
            else:
                print(f"{module:<15} {s_files:>10} {s_lines:>10} {'?':>12} {'?':>12} 需要对比")
        else:
            print(f"{module:<15} {'N/A':>10} {'N/A':>10} {'?':>12} {'?':>12} framework独有")
    
    print('-' * 90)
    print(f"{'总计':<15} {total_server_files:>10} {total_server_lines:>10}")
    print()
    print('server独有模块（需要新增到framework）:')
    for m in server_only:
        print(f"  - {m}")

if __name__ == '__main__':
    main()
