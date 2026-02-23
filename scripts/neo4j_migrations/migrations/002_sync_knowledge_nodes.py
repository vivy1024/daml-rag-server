"""
Migration 002: 同步 KnowledgeArticle + __KGBuilder__ + Guideline 节点

背景: CHANGELOG #3 (2026-02-21) 知识库入库
- KnowledgeArticle: 5 个知识文章节点
- __KGBuilder__: 9 个知识图谱构建元数据节点
- Guideline: 1 个指南节点

这些节点只在本地创建，需要同步到生产。
实际数据通过 sync.py --sync 同步，本 migration 仅做状态检查。
"""


def up(session):
    """检查缺失节点"""
    for label in ['KnowledgeArticle', '__KGBuilder__', 'Guideline']:
        result = session.run(f'MATCH (n:{label}) RETURN count(n) AS cnt')
        cnt = result.single()['cnt']
        expected = {'KnowledgeArticle': 5, '__KGBuilder__': 9, 'Guideline': 1}
        exp = expected.get(label, 0)
        if cnt >= exp:
            print(f'  {label}: {cnt} 个 ✅')
        else:
            print(f'  {label}: {cnt}/{exp} 个，请运行 sync.py --sync')


def down(session):
    """回滚: 删除这些节点"""
    for label in ['KnowledgeArticle', '__KGBuilder__', 'Guideline']:
        result = session.run(f'MATCH (n:{label}) DETACH DELETE n RETURN count(n) AS cnt')
        cnt = result.single()['cnt']
        print(f'  删除 {label}: {cnt} 个')
