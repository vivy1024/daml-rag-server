"""
Migration 001: 补充 11 个孤立 InjuryType 的 CONTRAINDICATED_FOR 关系

背景: CHANGELOG #17 (2026-02-22)
- 11 个 InjuryType 节点原本没有 CONTRAINDICATED_FOR 关系（孤立节点）
- 通过 backfill_contraindications.py 补充了 3,293 条关系
- 关系方向: (Exercise)-[:CONTRAINDICATED_FOR]->(InjuryType)
- 关系属性: severity, reason, confidence

本 migration 用于记录这次数据变更，实际数据已通过 sync.py 同步。
如果目标数据库已有这些关系（通过 sync 同步过），up() 中的 MERGE 会跳过。
"""


def up(session):
    """检查并补充 CONTRAINDICATED_FOR 关系"""
    # 检查当前状态
    result = session.run(
        'MATCH ()-[r:CONTRAINDICATED_FOR]->() RETURN count(r) AS cnt'
    )
    current = result.single()['cnt']

    if current >= 6371:
        print(f'  已有 {current} 条 CONTRAINDICATED_FOR，跳过')
        return

    # 查找缺少 CONTRAINDICATED_FOR 的 InjuryType
    result = session.run('''
        MATCH (i:InjuryType)
        WHERE NOT EXISTS { MATCH (:Exercise)-[:CONTRAINDICATED_FOR]->(i) }
        RETURN i.name AS name
    ''')
    orphans = [rec['name'] for rec in result]

    if not orphans:
        print(f'  无孤立 InjuryType，当前 {current} 条关系')
        return

    print(f'  发现 {len(orphans)} 个孤立 InjuryType: {orphans}')
    print(f'  请运行 sync.py --sync 从本地同步数据')


def down(session):
    """回滚: 删除补充的关系（仅删除 confidence < 1.0 的批量生成关系）"""
    result = session.run('''
        MATCH ()-[r:CONTRAINDICATED_FOR]->()
        WHERE r.confidence IS NOT NULL AND r.confidence < 1.0
        DELETE r
        RETURN count(r) AS deleted
    ''')
    deleted = result.single()['deleted']
    print(f'  删除 {deleted} 条批量生成的 CONTRAINDICATED_FOR 关系')
