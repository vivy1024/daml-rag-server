#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空INVOLVES_JOINT关系

原因：
- musclewiki数据源本身没有joints数据
- 等待musclewiki后续更新后再导入
- 当前的103个关系数据来源不明，需要清空

优先级：P2
"""

import os
from neo4j import GraphDatabase
from datetime import datetime

# Neo4j连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "build_body_2024")


class InvolvesJointCleaner:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.stats = {
            "relationships_deleted": 0
        }
    
    def close(self):
        self.driver.close()
    
    def log(self, message):
        """打印日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def check_current_state(self):
        """检查当前状态"""
        self.log("\n📊 检查当前INVOLVES_JOINT关系...")
        
        with self.driver.session() as session:
            # 检查关系总数
            result = session.run("MATCH ()-[r:INVOLVES_JOINT]->() RETURN count(r) as count")
            total_count = result.single()["count"]
            self.log(f"  当前INVOLVES_JOINT关系: {total_count} 个")
            
            if total_count > 0:
                # 按Joint统计
                result = session.run("""
                    MATCH (j:Joint)<-[r:INVOLVES_JOINT]-(e:Exercise)
                    RETURN j.name_zh as joint, count(e) as exercise_count
                    ORDER BY exercise_count DESC
                """)
                
                self.log("\n  各关节涉及的动作数量:")
                for record in result:
                    self.log(f"    {record['joint']}: {record['exercise_count']} 个动作")
            
            return total_count
    
    def delete_relationships(self):
        """删除所有INVOLVES_JOINT关系"""
        self.log("\n🗑️  删除所有INVOLVES_JOINT关系...")
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH ()-[r:INVOLVES_JOINT]->()
                DELETE r
                RETURN count(r) as deleted_count
            """)
            
            self.stats["relationships_deleted"] = result.single()["deleted_count"]
            self.log(f"  ✅ 成功删除 {self.stats['relationships_deleted']} 个关系")
    
    def verify_results(self):
        """验证结果"""
        self.log("\n📊 验证结果...")
        
        with self.driver.session() as session:
            result = session.run("MATCH ()-[r:INVOLVES_JOINT]->() RETURN count(r) as count")
            remaining_count = result.single()["count"]
            
            if remaining_count == 0:
                self.log("  ✅ 所有INVOLVES_JOINT关系已清空")
            else:
                self.log(f"  ⚠️ 仍有 {remaining_count} 个关系未删除")
    
    def print_summary(self):
        """打印总结"""
        self.log("\n" + "=" * 60)
        self.log("📊 执行总结")
        self.log("=" * 60)
        self.log(f"✅ 删除关系: {self.stats['relationships_deleted']} 个")
        self.log("\n说明:")
        self.log("  - musclewiki数据源本身没有joints数据")
        self.log("  - 等待musclewiki后续更新后再导入")
        self.log("  - Joint节点保留，仅删除关系")
    
    def run(self):
        """执行流程"""
        try:
            self.log("=" * 60)
            self.log("🚀 清空INVOLVES_JOINT关系")
            self.log("=" * 60)
            
            # 1. 检查当前状态
            current_count = self.check_current_state()
            
            if current_count == 0:
                self.log("\n✅ 当前没有INVOLVES_JOINT关系，无需清空")
                return
            
            # 2. 确认删除
            self.log("\n⚠️  即将删除所有INVOLVES_JOINT关系")
            self.log("  按Ctrl+C取消，或等待3秒后自动执行...")
            import time
            time.sleep(3)
            
            # 3. 删除关系
            self.delete_relationships()
            
            # 4. 验证结果
            self.verify_results()
            
            # 5. 打印总结
            self.print_summary()
            
            self.log("\n✅ 完成!")
        
        except KeyboardInterrupt:
            self.log("\n❌ 用户取消操作")
        
        except Exception as e:
            self.log(f"\n❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.close()


if __name__ == "__main__":
    cleaner = InvolvesJointCleaner()
    cleaner.run()
