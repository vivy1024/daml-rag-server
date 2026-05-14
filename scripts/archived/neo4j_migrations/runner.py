"""
Neo4j Migration Runner — 类似 Laravel migrate 的数据库版本管理

用法:
    # 在容器内执行（本地 Neo4j）
    docker exec fitness_daml_rag python scripts/neo4j_migrations/runner.py

    # 指定生产环境
    docker exec fitness_daml_rag python scripts/neo4j_migrations/runner.py --target prod

    # 只检查状态不执行
    docker exec fitness_daml_rag python scripts/neo4j_migrations/runner.py --status

    # 回滚最后一个 migration（如果支持）
    docker exec fitness_daml_rag python scripts/neo4j_migrations/runner.py --rollback

设计:
    - migrations/ 目录下的 Python 文件按编号顺序执行
    - 每个 migration 文件必须实现 up(session) 和可选的 down(session)
    - 已执行的 migration 记录在 Neo4j 的 __Migration__ 节点中
    - 支持 --target local|prod 切换目标数据库
"""
import argparse
import importlib.util
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from neo4j import GraphDatabase

# 连接配置
TARGETS = {
    'local': {
        'uri': os.getenv('NEO4J_URI', 'bolt://neo4j:7687'),
        'user': os.getenv('NEO4J_USER', 'neo4j'),
        'password': os.getenv('NEO4J_PASSWORD', 'build_body_2024'),
    },
    'prod': {
        'uri': 'bolt://182.92.78.183:32372',
        'user': 'neo4j',
        'password': 'build_body_2024',
    },
}

MIGRATIONS_DIR = Path(__file__).parent / 'migrations'


def get_driver(target: str):
    cfg = TARGETS[target]
    return GraphDatabase.driver(cfg['uri'], auth=(cfg['user'], cfg['password']))


def get_executed_migrations(session) -> set[str]:
    """查询已执行的 migration 列表"""
    result = session.run(
        'MATCH (m:__Migration__) RETURN m.name AS name ORDER BY m.name'
    )
    return {rec['name'] for rec in result}


def record_migration(session, name: str):
    """记录已执行的 migration"""
    session.run(
        'CREATE (m:__Migration__ {name: $name, executed_at: $ts})',
        name=name,
        ts=datetime.now(timezone.utc).isoformat(),
    )


def remove_migration_record(session, name: str):
    """删除 migration 记录（回滚用）"""
    session.run('MATCH (m:__Migration__ {name: $name}) DELETE m', name=name)


def discover_migrations() -> list[tuple[str, Path]]:
    """发现所有 migration 文件，按编号排序"""
    if not MIGRATIONS_DIR.exists():
        return []
    files = sorted(MIGRATIONS_DIR.glob('[0-9]*.py'))
    return [(f.stem, f) for f in files]


def load_migration_module(name: str, path: Path):
    """动态加载 migration 模块"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cmd_migrate(target: str, dry_run: bool = False):
    """执行所有未执行的 migration"""
    driver = get_driver(target)
    all_migrations = discover_migrations()

    with driver.session(database='neo4j') as session:
        executed = get_executed_migrations(session)
        pending = [(name, path) for name, path in all_migrations if name not in executed]

        if not pending:
            print(f'[{target}] 所有 migration 已执行，无需操作。')
            driver.close()
            return

        print(f'[{target}] 待执行 {len(pending)} 个 migration:')
        for name, _ in pending:
            print(f'  → {name}')

        if dry_run:
            print('\n(dry-run 模式，不实际执行)')
            driver.close()
            return

        for name, path in pending:
            print(f'\n执行 {name}...')
            module = load_migration_module(name, path)
            try:
                module.up(session)
                record_migration(session, name)
                print(f'  ✅ {name} 完成')
            except Exception as e:
                print(f'  ❌ {name} 失败: {e}')
                driver.close()
                sys.exit(1)

    driver.close()
    print(f'\n[{target}] 全部 migration 执行完成!')


def cmd_status(target: str):
    """显示 migration 状态"""
    driver = get_driver(target)
    all_migrations = discover_migrations()

    with driver.session(database='neo4j') as session:
        executed = get_executed_migrations(session)

        # 同时查数据库概况
        nodes = session.run('MATCH (n) RETURN count(n) AS cnt').single()['cnt']
        rels = session.run('MATCH ()-[r]->() RETURN count(r) AS cnt').single()['cnt']

        print(f'[{target}] 数据库概况: {nodes} 节点 / {rels} 关系')
        print(f'[{target}] Migration 状态:')
        for name, _ in all_migrations:
            status = '✅ 已执行' if name in executed else '⏳ 待执行'
            print(f'  {status}  {name}')

        if not all_migrations:
            print('  (无 migration 文件)')

    driver.close()


def cmd_rollback(target: str):
    """回滚最后一个 migration"""
    driver = get_driver(target)
    all_migrations = discover_migrations()

    with driver.session(database='neo4j') as session:
        executed = get_executed_migrations(session)
        executed_list = sorted(executed)

        if not executed_list:
            print(f'[{target}] 无已执行的 migration，无法回滚。')
            driver.close()
            return

        last = executed_list[-1]
        # 找到对应的文件
        migration_map = dict(all_migrations)
        if last not in migration_map:
            print(f'[{target}] 找不到 {last} 的文件，无法回滚。')
            driver.close()
            return

        module = load_migration_module(last, migration_map[last])
        if not hasattr(module, 'down'):
            print(f'[{target}] {last} 没有 down() 函数，不支持回滚。')
            driver.close()
            return

        print(f'[{target}] 回滚 {last}...')
        try:
            module.down(session)
            remove_migration_record(session, last)
            print(f'  ✅ 回滚完成')
        except Exception as e:
            print(f'  ❌ 回滚失败: {e}')

    driver.close()


def cmd_sync():
    """对比本地和生产，显示差异"""
    local_driver = get_driver('local')
    prod_driver = get_driver('prod')

    with local_driver.session(database='neo4j') as ls, \
         prod_driver.session(database='neo4j') as ps:

        local_nodes = ls.run('MATCH (n) RETURN count(n) AS cnt').single()['cnt']
        local_rels = ls.run('MATCH ()-[r]->() RETURN count(r) AS cnt').single()['cnt']
        prod_nodes = ps.run('MATCH (n) RETURN count(n) AS cnt').single()['cnt']
        prod_rels = ps.run('MATCH ()-[r]->() RETURN count(r) AS cnt').single()['cnt']

        local_mig = get_executed_migrations(ls)
        prod_mig = get_executed_migrations(ps)

    local_driver.close()
    prod_driver.close()

    print('=== 本地 vs 生产 对比 ===')
    print(f'  节点: 本地={local_nodes}, 生产={prod_nodes}, 差={local_nodes - prod_nodes}')
    print(f'  关系: 本地={local_rels}, 生产={prod_rels}, 差={local_rels - prod_rels}')
    print(f'  Migration: 本地={len(local_mig)}, 生产={len(prod_mig)}')

    only_local = local_mig - prod_mig
    only_prod = prod_mig - local_mig
    if only_local:
        print(f'  仅本地已执行: {sorted(only_local)}')
    if only_prod:
        print(f'  仅生产已执行: {sorted(only_prod)}')
    if not only_local and not only_prod and local_nodes == prod_nodes:
        print('  ✅ 本地与生产完全一致')


def main():
    parser = argparse.ArgumentParser(description='Neo4j Migration Runner')
    parser.add_argument('--target', choices=['local', 'prod'], default='local',
                        help='目标数据库 (default: local)')
    parser.add_argument('--status', action='store_true', help='显示 migration 状态')
    parser.add_argument('--rollback', action='store_true', help='回滚最后一个 migration')
    parser.add_argument('--sync-status', action='store_true', help='对比本地和生产差异')
    parser.add_argument('--dry-run', action='store_true', help='只显示待执行，不实际执行')
    parser.add_argument('--all', action='store_true', help='同时在本地和生产执行')

    args = parser.parse_args()

    if args.sync_status:
        cmd_sync()
    elif args.status:
        cmd_status(args.target)
    elif args.rollback:
        cmd_rollback(args.target)
    elif args.all:
        print('=== 执行本地 ===')
        cmd_migrate('local', args.dry_run)
        print('\n=== 执行生产 ===')
        cmd_migrate('prod', args.dry_run)
    else:
        cmd_migrate(args.target, args.dry_run)


if __name__ == '__main__':
    main()
