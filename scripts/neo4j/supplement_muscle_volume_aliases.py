#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
补充剩余23个Muscle节点的训练量数据（别名和变体名称）

这些是一些肌肉的别名或变体名称，需要映射到对应的标准训练量数据。

作者: BUILD_BODY Team
日期: 2026-01-06
"""

import os
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "build_body_2024")

# 剩余23个节点的训练量数据（基于RP标准）
REMAINING_MUSCLE_DATA = {
    # 胸部变体
    "中下胸肌": {"mev": 6, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "上胸肌": {"mev": 6, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    
    # 肩部变体
    "肩前部": {"mev": 0, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "肩部": {"mev": 8, "mav": 18, "mrv": 26, "optimal_frequency": "2次/周"},
    "肩后部": {"mev": 8, "mav": 16, "mrv": 22, "optimal_frequency": "2-3次/周"},
    
    # 大腿变体
    "大腿内侧": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "股四头肌内侧": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "股四头肌外侧": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    
    # 斜方肌变体
    "上斜方肌": {"mev": 0, "mav": 12, "mrv": 20, "optimal_frequency": "2-3次/周"},
    "下斜方肌": {"mev": 0, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "中斜方肌": {"mev": 0, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    
    # 背部变体
    "下背部": {"mev": 0, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    
    # 腿后肌群变体
    "腿后肌群": {"mev": 6, "mav": 16, "mrv": 22, "optimal_frequency": "2次/周"},
    "腿后肌群外侧": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    "腿后肌群内侧": {"mev": 4, "mav": 12, "mrv": 18, "optimal_frequency": "2次/周"},
    
    # 前臂变体
    "前臂": {"mev": 2, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "腕屈肌": {"mev": 2, "mav": 10, "mrv": 16, "optimal_frequency": "2次/周"},
    "腕伸肌": {"mev": 2, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    
    # 小腿变体
    "小腿": {"mev": 8, "mav": 16, "mrv": 22, "optimal_frequency": "2-3次/周"},
    "足部": {"mev": 0, "mav": 8, "mrv": 14, "optimal_frequency": "2次/周"},
    
    # 腹部变体
    "上腹肌": {"mev": 0, "mav": 12, "mrv": 20, "optimal_frequency": "3次/周"},
    "下腹肌": {"mev": 0, "mav": 12, "mrv": 20, "optimal_frequency": "3次/周"},
    "腹斜肌": {"mev": 0, "mav": 12, "mrv": 20, "optimal_frequency": "3次/周"},
}


def main():
    """主函数：补充剩余Muscle节点的训练量数据"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    print("=" * 80)
    print("🏋️ 补充剩余Muscle节点的训练量数据（别名和变体）")
    print("=" * 80)
    
    with driver.session() as session:
        updated_count = 0
        not_found_count = 0
        
        for muscle_name, data in REMAINING_MUSCLE_DATA.items():
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
        
        # 验证最终结果
        print("\n" + "=" * 80)
        print("📊 最终验证")
        print("=" * 80)
        
        result = session.run("MATCH (m:Muscle) RETURN count(m) as count")
        muscle_count = result.single()["count"]
        
        fields = ["mev", "mav", "mrv", "optimal_frequency"]
        print(f"\n   Muscle节点总数: {muscle_count}")
        print(f"   本次更新节点数: {updated_count}")
        
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
        
        # 检查是否还有缺失
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
