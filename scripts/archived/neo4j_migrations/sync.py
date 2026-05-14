"""
Neo4j 全量同步脚本 — 本地 → 生产

从本地 fitness_daml_rag 容器执行，通过公网 bolt 端口直连生产 Neo4j。
Zeabur 命令行不可用（卡顿、无法粘贴），所以所有操作都从本地发起。

用法:
    # 只检查差异（不写入）
    docker exec fitness_daml_rag bash -c "python scripts/neo4j_migrations/sync.py --check"

    # 执行同步
    docker exec fitness_daml_rag bash -c "python scripts/neo4j_migrations/sync.py --sync"

    # 指定生产地址（默认已配置）
    docker exec fitness_daml_rag bash -c "python scripts/neo4j_migrations/sync.py --sync --prod-uri bolt://182.92.78.183:32372"

原理:
    1. 对比本地和生产的节点数、关系数、关系类型分布
    2. 找出生产缺少的关系和节点
    3. 用 MERGE + UNWIND 批量写入（幂等，可重复执行）
"""
import argparse
import os
import sys
from collections import defaultdict

from neo4j import GraphDatabase

# 连接配置
LOCAL_URI = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
LOCAL_USER = os.getenv('NEO4J_USER', 'neo4j')
LOCAL_PASSWORD = os.getenv('NEO4J_PASSWORD', 'build_body_2024')

PROD_URI = 'bolt://182.92.78.183:32372'
PROD_USER = 'neo4j'
PROD_PASSWORD = 'build_body_2024'


def get_stats(session) -> dict:
    """获取数据库统计信息"""
    nodes = session.run('MATCH (n) RETURN count(n) AS cnt').single()['cnt']
    rels = session.run('MATCH ()-[r]->() RETURN count(r) AS cnt').single()['cnt']

    # 按标签统计节点
    node_labels = {}
    for rec in session.run('MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt ORDER BY cnt DESC'):
        node_labels[rec['label']] = rec['cnt']

    # 按类型统计关系
    rel_types = {}
    for rec in session.run('MATCH ()-[r]->() RETURN type(r) AS t, count(r) AS cnt ORDER BY cnt DESC'):
        rel_types[rec['t']] = rec['cnt']

    return {'nodes': nodes, 'rels': rels, 'node_labels': node_labels, 'rel_types': rel_types}


def export_relationships(session, rel_type: str) -> list[dict]:
    """导出指定类型的所有关系（含两端节点标识和关系属性）"""
    result = session.run(f'''
        MATCH (a)-[r:{rel_type}]->(b)
        RETURN labels(a)[0] AS a_label, a.id AS a_id, a.name AS a_name,
               labels(b)[0] AS b_label, b.id AS b_id, b.name AS b_name,
               properties(r) AS props
    ''')
    rels = []
    for rec in result:
        rels.append({
            'a_label': rec['a_label'],
            'a_id': rec['a_id'],
            'a_name': rec['a_name'],
            'b_label': rec['b_label'],
            'b_id': rec['b_id'],
            'b_name': rec['b_name'],
            'props': dict(rec['props']) if rec['props'] else {},
        })
    return rels


def make_rel_key(rel: dict) -> tuple:
    """生成关系唯一键（优先用 id，其次用 name）"""
    a_key = rel['a_id'] if rel['a_id'] is not None else rel['a_name']
    b_key = rel['b_id'] if rel['b_id'] is not None else rel['b_name']
    return (rel['a_label'], a_key, rel['b_label'], b_key)


def export_nodes(session, label: str) -> list[dict]:
    """导出指定标签的所有节点"""
    result = session.run(f'MATCH (n:{label}) RETURN properties(n) AS props')
    return [dict(rec['props']) for rec in result]


def sync_relationships(prod_session, rel_type: str, missing_rels: list[dict]):
    """批量同步缺失的关系到生产"""
    if not missing_rels:
        return 0

    # 按 (a_label, b_label) 分组处理
    groups = defaultdict(list)
    for rel in missing_rels:
        groups[(rel['a_label'], rel['b_label'])].append(rel)

    total = 0
    for (a_label, b_label), rels in groups.items():
        # 确定匹配属性（优先 id，其次 name）
        sample = rels[0]
        a_match = 'id' if sample['a_id'] is not None else 'name'
        b_match = 'id' if sample['b_id'] is not None else 'name'

        a_key_field = 'a_id' if a_match == 'id' else 'a_name'
        b_key_field = 'b_id' if b_match == 'id' else 'b_name'

        batch_size = 500
        for i in range(0, len(rels), batch_size):
            batch = rels[i:i + batch_size]
            params = [{
                'a_key': r[a_key_field],
                'b_key': r[b_key_field],
                'props': {k: v for k, v in r['props'].items()
                          if not hasattr(v, 'year')},  # 跳过 DateTime 类型
            } for r in batch]

            result = prod_session.run(f'''
                UNWIND $batch AS item
                MATCH (a:{a_label} {{{a_match}: item.a_key}})
                MATCH (b:{b_label} {{{b_match}: item.b_key}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r += item.props
                RETURN count(r) AS cnt
            ''', batch=params)
            cnt = result.single()['cnt']
            total += cnt
            print(f'    ({a_label})-[:{rel_type}]->({b_label}): 批次 {i // batch_size + 1}, 写入 {cnt}')

    return total


def sync_nodes(prod_session, label: str, nodes: list[dict]):
    """同步缺失节点到生产"""
    if not nodes:
        return 0

    count = 0
    for node in nodes:
        # 清理不可序列化的值
        clean = {k: v for k, v in node.items() if not hasattr(v, 'year')}
        props_set = ', '.join([f'n.{k} = ${k}' for k in clean.keys()])

        if 'name' in clean:
            prod_session.run(
                f'MERGE (n:{label} {{name: $name}}) SET {props_set}', **clean
            )
        elif 'id' in clean:
            prod_session.run(
                f'MERGE (n:{label} {{id: $id}}) SET {props_set}', **clean
            )
        else:
            prod_session.run(f'CREATE (n:{label}) SET {props_set}', **clean)
        count += 1

    return count


def cmd_check(local_driver, prod_driver):
    """对比本地和生产差异"""
    with local_driver.session(database='neo4j') as ls, \
         prod_driver.session(database='neo4j') as ps:

        local_stats = get_stats(ls)
        prod_stats = get_stats(ps)

    print('=' * 60)
    print('Neo4j 本地 vs 生产 对比报告')
    print('=' * 60)

    print(f'\n总计: 本地 {local_stats["nodes"]} 节点 / {local_stats["rels"]} 关系')
    print(f'      生产 {prod_stats["nodes"]} 节点 / {prod_stats["rels"]} 关系')

    node_diff = local_stats['nodes'] - prod_stats['nodes']
    rel_diff = local_stats['rels'] - prod_stats['rels']
    print(f'      差异: {node_diff:+d} 节点 / {rel_diff:+d} 关系')

    # 节点标签差异
    all_labels = set(local_stats['node_labels']) | set(prod_stats['node_labels'])
    label_diffs = []
    for label in sorted(all_labels):
        lc = local_stats['node_labels'].get(label, 0)
        pc = prod_stats['node_labels'].get(label, 0)
        if lc != pc:
            label_diffs.append((label, lc, pc, lc - pc))

    if label_diffs:
        print('\n节点差异:')
        for label, lc, pc, diff in label_diffs:
            print(f'  {label}: 本地={lc}, 生产={pc}, 差={diff:+d}')

    # 关系类型差异
    all_types = set(local_stats['rel_types']) | set(prod_stats['rel_types'])
    type_diffs = []
    for t in sorted(all_types):
        lc = local_stats['rel_types'].get(t, 0)
        pc = prod_stats['rel_types'].get(t, 0)
        if lc != pc:
            type_diffs.append((t, lc, pc, lc - pc))

    if type_diffs:
        print('\n关系差异:')
        for t, lc, pc, diff in type_diffs:
            print(f'  {t}: 本地={lc}, 生产={pc}, 差={diff:+d}')

    if not label_diffs and not type_diffs:
        print('\n✅ 本地与生产完全一致，无需同步。')
        return False

    return True


def cmd_sync(local_driver, prod_driver):
    """执行全量同步"""
    # 先检查差异
    has_diff = cmd_check(local_driver, prod_driver)
    if not has_diff:
        return

    print('\n' + '=' * 60)
    print('开始同步...')
    print('=' * 60)

    with local_driver.session(database='neo4j') as ls, \
         prod_driver.session(database='neo4j') as ps:

        local_stats = get_stats(ls)
        prod_stats = get_stats(ps)

        # 同步缺失节点
        all_labels = set(local_stats['node_labels']) | set(prod_stats['node_labels'])
        for label in sorted(all_labels):
            lc = local_stats['node_labels'].get(label, 0)
            pc = prod_stats['node_labels'].get(label, 0)
            if lc > pc:
                print(f'\n同步节点 {label} (本地={lc}, 生产={pc})...')
                local_nodes = export_nodes(ls, label)
                prod_nodes = export_nodes(ps, label)

                # 简单用节点数差异判断（MERGE 保证幂等）
                cnt = sync_nodes(ps, label, local_nodes)
                print(f'  MERGE {cnt} 个节点')

        # 同步缺失关系
        all_types = set(local_stats['rel_types']) | set(prod_stats['rel_types'])
        for rel_type in sorted(all_types):
            lc = local_stats['rel_types'].get(rel_type, 0)
            pc = prod_stats['rel_types'].get(rel_type, 0)
            if lc > pc:
                print(f'\n同步关系 {rel_type} (本地={lc}, 生产={pc}, 差={lc - pc})...')
                local_rels = export_relationships(ls, rel_type)
                prod_rels = export_relationships(ps, rel_type)

                local_keys = {make_rel_key(r) for r in local_rels}
                prod_keys = {make_rel_key(r) for r in prod_rels}
                missing_keys = local_keys - prod_keys

                missing_rels = [r for r in local_rels if make_rel_key(r) in missing_keys]
                print(f'  精确差异: {len(missing_rels)} 条')

                cnt = sync_relationships(ps, rel_type, missing_rels)
                print(f'  写入完成: {cnt} 条')

    # 验证
    print('\n' + '=' * 60)
    print('验证同步结果...')
    print('=' * 60)
    cmd_check(local_driver, prod_driver)


def main():
    parser = argparse.ArgumentParser(description='Neo4j 全量同步 (本地→生产)')
    parser.add_argument('--check', action='store_true', help='只检查差异，不写入')
    parser.add_argument('--sync', action='store_true', help='执行同步')
    parser.add_argument('--prod-uri', default=PROD_URI, help='生产 Neo4j bolt 地址')

    args = parser.parse_args()

    if not args.check and not args.sync:
        parser.print_help()
        print('\n请指定 --check 或 --sync')
        sys.exit(1)

    local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    prod_driver = GraphDatabase.driver(args.prod_uri, auth=(PROD_USER, PROD_PASSWORD))

    try:
        if args.check:
            cmd_check(local_driver, prod_driver)
        elif args.sync:
            cmd_sync(local_driver, prod_driver)
    finally:
        local_driver.close()
        prod_driver.close()


if __name__ == '__main__':
    main()
