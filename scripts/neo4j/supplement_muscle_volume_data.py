#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充所有Muscle节点的训练量数据（MEV/MAV/MRV/optimal_frequency）

基于Renaissance Periodization (RP) 训练量标准，为所有缺少这些字段的Muscle节点补充数据。

MEV = Minimum Effective Volume (最小有效训练量)
MAV = Maximum Adaptive Volume (最大适应训练量)  
MRV = Maximum Recoverable Volume (最大可恢复训练量)

数据来源：
- Renaissance Periodization官方指南
- Dr. Mike Israetel的训练量建议
- 运动科学研究文献

作者: BUILD_BODY Team
日期: 2026-01-06
"""

import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "build_body_2024")

# 基于RP标准的训练量数据（每周组数）
# 按肌群分类，提供MEV/MAV/MRV和最佳训练频率
MUSCLE_VOLUME_DATA = {
    # === 胸部肌群 ===
    "胸肌": {"mev": 10, "mav": 20, "mrv": 26, "optimal_frequency": "2次/周"},
    "胸大肌": {"mev": 10, "mav": 20, "mrv": 26, "optimal_frequency": "2次/周"},
    "胸大肌锁骨部": {"mev": 6, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "胸大肌胸肋部": {"mev": 6, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "胸小肌": {"mev": 0, "mav": 8, "mrv": 12, "optimal_frequency": "2次/周"},
    "前锯肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    
    # === 背部肌群 ===
    "背阔肌": {"mev": 10, "mav": 20, "mrv": 26, "optimal_frequency": "2次/周"},
    "斜方肌": {"mev": 0, "mav": 16, "mrv": 26, "optimal_frequency": "2次/周"},
    "斜方肌上部": {"mev": 0, "mav": 12, "mrv": 20, "optimal_frequency": "2-3次/周"},
    "斜方肌中部": {"mev": 0, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "菱形肌": {"mev": 0, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "大圆肌": {"mev": 6, "mav": 14, "mrv": 20, "optimal_frequency": "2次/周"},
    "小圆肌": {"mev": 0, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "冈下肌": {"mev": 0, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "冈上肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    "肩胛下肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    "竖脊肌": {"mev": 0, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "腰方肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    
    # === 肩部肌群 ===
    "三角肌": {"mev": 8, "mav": 18, "mrv": 26, "optimal_frequency": "2次/周"},
    "三角肌前束": {"mev": 0, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "三角肌中束": {"mev": 8, "mav": 16, "mrv": 22, "optimal_frequency": "2-3次/周"},
    "三角肌后束": {"mev": 8, "mav": 16, "mrv": 22, "optimal_frequency": "2-3次/周"},
    
    # === 手臂肌群 ===
    "肱二头肌": {"mev": 8, "mav": 18, "mrv": 26, "optimal_frequency": "2-3次/周"},
    "肱二头肌长头": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "肱二头肌短头": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "肱肌": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "肱桡肌": {"mev": 2, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "肱三头肌": {"mev": 6, "mav": 14, "mrv": 20, "optimal_frequency": "2次/周"},
    "肱三头肌长头": {"mev": 4, "mav": 10, "mrv": 14, "optimal_frequency": "2次/周"},
    "肱三头肌外侧头": {"mev": 4, "mav": 10, "mrv": 14, "optimal_frequency": "2次/周"},
    "肱三头肌内侧头": {"mev": 4, "mav": 10, "mrv": 14, "optimal_frequency": "2次/周"},
    "前臂屈肌": {"mev": 2, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "前臂伸肌": {"mev": 2, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    
    # === 核心肌群 ===
    "腹直肌": {"mev": 0, "mav": 16, "mrv": 25, "optimal_frequency": "3次/周"},
    "腹外斜肌": {"mev": 0, "mav": 12, "mrv": 20, "optimal_frequency": "3次/周"},
    "腹内斜肌": {"mev": 0, "mav": 12, "mrv": 20, "optimal_frequency": "3次/周"},
    "腹横肌": {"mev": 0, "mav": 10, "mrv": 16, "optimal_frequency": "3次/周"},
    "腹肌": {"mev": 0, "mav": 16, "mrv": 25, "optimal_frequency": "3次/周"},
    
    # === 臀部肌群 ===
    "臀大肌": {"mev": 4, "mav": 16, "mrv": 22, "optimal_frequency": "2次/周"},
    "臀中肌": {"mev": 0, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "臀小肌": {"mev": 0, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "臀部": {"mev": 4, "mav": 16, "mrv": 22, "optimal_frequency": "2次/周"},
    
    # === 大腿肌群 ===
    "股四头肌": {"mev": 8, "mav": 18, "mrv": 26, "optimal_frequency": "2次/周"},
    "股直肌": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "股外侧肌": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "股内侧肌": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "股中间肌": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "腘绳肌": {"mev": 6, "mav": 16, "mrv": 22, "optimal_frequency": "2次/周"},
    "股二头肌": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "半腱肌": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "半膜肌": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "内收肌群": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "大收肌": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "长收肌": {"mev": 4, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "短收肌": {"mev": 4, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "耻骨肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    "股薄肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    "缝匠肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    "阔筋膜张肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    "髂腰肌": {"mev": 0, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "腹股沟": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    
    # === 小腿肌群 ===
    "小腿三头肌": {"mev": 8, "mav": 16, "mrv": 22, "optimal_frequency": "2-3次/周"},
    "腓肠肌": {"mev": 6, "mav": 14, "mrv": 20, "optimal_frequency": "2-3次/周"},
    "比目鱼肌": {"mev": 6, "mav": 14, "mrv": 20, "optimal_frequency": "2-3次/周"},
    "胫骨前肌": {"mev": 0, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "腓骨长肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    "腓骨短肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    
    # === 颈部肌群 ===
    "颈部": {"mev": 0, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "胸锁乳突肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    "斜角肌": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    "肩胛提肌": {"mev": 0, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    
    # === 其他 ===
    "手部": {"mev": 2, "mav": 10, "mrv": 16, "optimal_frequency": "2-3次/周"},
}


def main():
    """主函数：补充所有Muscle节点的训练量数据"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    print("=" * 80)
    print("🏋️ 补充Muscle节点的训练量数据（MEV/MAV/MRV）")
    print("=" * 80)
    print(f"数据来源: Renaissance Periodization (RP)")
    
    with driver.session() as session:
        # 首先获取所有缺少训练量数据的节点
        result = session.run("""
            MATCH (m:Muscle)
            WHERE m.mev IS NULL OR m.mav IS NULL OR m.mrv IS NULL
            RETURN m.name_zh as name
        """)
        
        missing_nodes = [record["name"] for record in result]
        print(f"缺少训练量数据的节点数: {len(missing_nodes)}")
        
        updated_count = 0
        not_found_count = 0
        no_data_count = 0
        
        for muscle_name in missing_nodes:
            if muscle_name in MUSCLE_VOLUME_DATA:
                data = MUSCLE_VOLUME_DATA[muscle_name]
                
                try:
                    query = """
                    MATCH (m:Muscle)
                    WHERE m.name_zh = $name_zh
                    SET m.mev = $mev,
                        m.mav = $mav,
                        m.mrv = $mrv,
                        m.optimal_frequency = $optimal_frequency
                    RETURN m.name_zh as name
                    """
                    
                    result = session.run(query, {
                        "name_zh": muscle_name,
                        "mev": data["mev"],
                        "mav": data["mav"],
                        "mrv": data["mrv"],
                        "optimal_frequency": data["optimal_frequency"]
                    })
                    
                    record = result.single()
                    if record:
                        updated_count += 1
                        print(f"   ✅ {muscle_name}: MEV={data['mev']}, MAV={data['mav']}, MRV={data['mrv']}")
                    else:
                        not_found_count += 1
                        print(f"   ⚠️ 未找到: {muscle_name}")
                
                except Exception as e:
                    print(f"   ❌ 错误: {muscle_name} - {e}")
            else:
                no_data_count += 1
                print(f"   📝 无数据: {muscle_name}")
        
        # 验证最终结果
        print("\n" + "=" * 80)
        print("📊 最终验证")
        print("=" * 80)
        
        result = session.run("MATCH (m:Muscle) RETURN count(m) as count")
        muscle_count = result.single()["count"]
        
        fields = ["mev", "mav", "mrv", "optimal_frequency"]
        print(f"\n   Muscle节点总数: {muscle_count}")
        print(f"   本次更新节点数: {updated_count}")
        print(f"   无数据节点数: {no_data_count}")
        
        print(f"\n   训练量字段覆盖率:")
        for field in fields:
            result = session.run(f"""
                MATCH (m:Muscle)
                WHERE m.{field} IS NOT NULL
                RETURN count(m) as count
            """)
            count = result.single()["count"]
            pct = count / muscle_count * 100
            status = "✅" if pct == 100 else "⚠️" if pct > 80 else "❌"
            print(f"   {status} {field}: {count}/{muscle_count} ({pct:.1f}%)")
        
        # 列出仍然缺少数据的节点
        result = session.run("""
            MATCH (m:Muscle)
            WHERE m.mev IS NULL
            RETURN m.name_zh as name
        """)
        still_missing = [record["name"] for record in result]
        
        if still_missing:
            print(f"\n   ⚠️ 仍缺少训练量数据的节点 ({len(still_missing)}个):")
            for name in still_missing:
                print(f"      - {name}")
        else:
            print(f"\n   🎉 所有Muscle节点的训练量数据已100%补充完成！")
        
        print("\n" + "=" * 80)
    
    driver.close()
    print("✅ 脚本执行完成")


if __name__ == "__main__":
    main()
