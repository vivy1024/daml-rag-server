#!/usr/bin/env python3
"""
字段一致性检查脚本
检查所有数据源的Exercise字段是否统一
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, '/app')
sys.path.insert(0, '/app/src')

# 统一字段名定义（标准）
STANDARD_FIELDS = {
    # 基础字段
    "id": "动作ID",
    "name_zh": "中文名称",
    "name_en": "英文名称",
    "slug": "URL标识",
    
    # 难度字段（统一后）
    "difficulty_zh": "难度（中文）",
    "difficulty_en": "难度（英文）",
    
    # 器械字段（统一后）
    "equipment_zh": "器械（中文）",
    "equipment_en": "器械（英文）",
    
    # 力类型字段（统一后）
    "force_zh": "力类型（中文）",
    "force_en": "力类型（英文）",
    
    # 动作机制字段（统一后）
    "mechanic_zh": "动作机制（中文）",
    "mechanic_en": "动作机制（英文）",
    
    # 肌肉字段（统一后）
    "primary_muscle_zh": "主要肌群（中文，单数）",
    "primary_muscle_en": "主要肌群（英文，单数）",
    "muscles_primary_zh": "主要肌群列表（中文）",
    "muscles_primary_en": "主要肌群列表（英文）",
    "muscles_secondary_zh": "次要肌群列表（中文）",
    "muscles_secondary_en": "次要肌群列表（英文）",
    "all_muscles_zh": "所有肌群（中文）",
    "all_muscles_en": "所有肌群（英文）",
    
    # 握法字段
    "grips_zh": "握法（中文）",
    "grips_en": "握法（英文）",
    
    # 训练参数
    "rep_range": "推荐次数范围",
    "set_range": "推荐组数范围",
    "rest_period": "休息时间",
    "intensity_percentage": "强度百分比",
    "safety_level": "安全等级",
    
    # 描述和步骤
    "description_zh": "描述（中文）",
    "description_en": "描述（英文）",
    "correct_steps_zh": "正确步骤（中文）",
    "correct_steps_en": "正确步骤（英文）",
}

# 旧字段名（应该不存在）
OLD_FIELDS = [
    "difficulty",  # 应该是 difficulty_zh/difficulty_en
    "equipment",   # 应该是 equipment_zh/equipment_en
    "force",       # 应该是 force_zh/force_en
    "mechanic",    # 应该是 mechanic_zh/mechanic_en
    "primary_muscles",  # 应该是 muscles_primary_zh
    "secondary_muscles",  # 应该是 muscles_secondary_zh
]


async def check_file_system():
    """检查文件系统中的Exercise数据"""
    print("\n" + "="*60)
    print("📁 检查文件系统 (exercises_v2)")
    print("="*60)
    
    base_path = Path("/app/data/exercises_v2") if Path("/app/data/exercises_v2").exists() else None
    if not base_path:
        # 尝试其他路径
        for p in ["/app/yuzhen-backend/storage/app/public/exercises_v2", 
                  "yuzhen-backend/storage/app/public/exercises_v2",
                  "F:/build_body/yuzhen-backend/storage/app/public/exercises_v2"]:
            if Path(p).exists():
                base_path = Path(p)
                break
    
    if not base_path or not base_path.exists():
        print("❌ 找不到exercises_v2目录")
        return None
    
    # 读取一个样本文件
    sample_files = list(base_path.rglob("data.json"))[:5]
    
    all_fields = set()
    old_fields_found = {}
    
    for f in sample_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                all_fields.update(data.keys())
                
                # 检查旧字段
                for old_field in OLD_FIELDS:
                    if old_field in data and old_field not in ["secondary_muscles"]:  # secondary_muscles可能是兼容字段
                        if old_field not in old_fields_found:
                            old_fields_found[old_field] = []
                        old_fields_found[old_field].append(str(f))
        except Exception as e:
            print(f"  ⚠️ 读取失败: {f} - {e}")
    
    print(f"\n📊 样本文件数: {len(sample_files)}")
    print(f"📊 总字段数: {len(all_fields)}")
    
    # 检查标准字段
    print("\n✅ 标准字段检查:")
    missing_standard = []
    for field in ["difficulty_zh", "difficulty_en", "equipment_zh", "equipment_en", 
                  "force_zh", "force_en", "mechanic_zh", "mechanic_en",
                  "muscles_primary_zh", "muscles_secondary_zh"]:
        if field in all_fields:
            print(f"  ✓ {field}")
        else:
            print(f"  ✗ {field} (缺失)")
            missing_standard.append(field)
    
    # 检查旧字段
    if old_fields_found:
        print("\n⚠️ 发现旧字段:")
        for field, files in old_fields_found.items():
            print(f"  ✗ {field} (在 {len(files)} 个文件中)")
    else:
        print("\n✅ 未发现旧字段")
    
    return {
        "source": "file_system",
        "total_fields": len(all_fields),
        "fields": list(all_fields),
        "missing_standard": missing_standard,
        "old_fields": list(old_fields_found.keys())
    }


async def check_neo4j():
    """检查Neo4j中的Exercise节点字段"""
    print("\n" + "="*60)
    print("🔷 检查Neo4j Exercise节点")
    print("="*60)
    
    try:
        from neo4j import AsyncGraphDatabase
        
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "fitness123")
        
        driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        
        async with driver.session() as session:
            # 获取Exercise节点的所有属性
            result = await session.run("""
                MATCH (e:Exercise)
                WITH e LIMIT 1
                RETURN keys(e) as fields
            """)
            record = await result.single()
            
            if record:
                fields = record["fields"]
                print(f"\n📊 Exercise节点字段数: {len(fields)}")
                
                # 检查标准字段
                print("\n✅ 标准字段检查:")
                standard_check = ["difficulty_zh", "difficulty_en", "equipment_zh", "equipment_en",
                                 "force_zh", "force_en", "mechanic_zh", "mechanic_en",
                                 "muscles_primary_zh", "muscles_secondary_zh"]
                missing = []
                for field in standard_check:
                    if field in fields:
                        print(f"  ✓ {field}")
                    else:
                        print(f"  ✗ {field} (缺失)")
                        missing.append(field)
                
                # 检查旧字段
                print("\n⚠️ 旧字段检查:")
                old_found = []
                for old_field in OLD_FIELDS:
                    if old_field in fields:
                        print(f"  ✗ {old_field} (仍存在)")
                        old_found.append(old_field)
                
                if not old_found:
                    print("  ✅ 未发现旧字段")
                
                # 检查difficulty_zh的值分布
                result2 = await session.run("""
                    MATCH (e:Exercise)
                    RETURN e.difficulty_zh as difficulty, count(*) as count
                    ORDER BY count DESC
                """)
                records = await result2.data()
                print("\n📊 difficulty_zh值分布:")
                for r in records:
                    print(f"  {r['difficulty'] or '空值'}: {r['count']}个")
                
                await driver.close()
                return {
                    "source": "neo4j",
                    "total_fields": len(fields),
                    "fields": fields,
                    "missing_standard": missing,
                    "old_fields": old_found
                }
            
        await driver.close()
    except Exception as e:
        print(f"❌ Neo4j检查失败: {e}")
        return None


async def check_qdrant():
    """检查Qdrant中的Exercise向量payload字段"""
    print("\n" + "="*60)
    print("🔶 检查Qdrant fitness_exercises_v2集合")
    print("="*60)
    
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "qdrant"),
            port=int(os.getenv("QDRANT_PORT", 6333))
        )
        
        # 获取集合信息
        collection_info = client.get_collection("fitness_exercises_v2")
        print(f"\n📊 向量数量: {collection_info.points_count}")
        
        # 获取一个样本点
        results = client.scroll(
            collection_name="fitness_exercises_v2",
            limit=1,
            with_payload=True
        )
        
        if results[0]:
            payload = results[0][0].payload
            fields = list(payload.keys())
            print(f"📊 Payload字段数: {len(fields)}")
            
            # 检查标准字段
            print("\n✅ 标准字段检查:")
            standard_check = ["difficulty_zh", "difficulty_en", "equipment_zh", "equipment_en",
                            "force_zh", "force_en", "mechanic_zh", "mechanic_en",
                            "muscles_primary_zh", "muscles_secondary_zh"]
            missing = []
            for field in standard_check:
                if field in fields:
                    print(f"  ✓ {field}")
                else:
                    print(f"  ✗ {field} (缺失)")
                    missing.append(field)
            
            # 检查旧字段
            print("\n⚠️ 旧字段检查:")
            old_found = []
            for old_field in OLD_FIELDS:
                if old_field in fields:
                    print(f"  ✗ {old_field} (仍存在)")
                    old_found.append(old_field)
            
            if not old_found:
                print("  ✅ 未发现旧字段")
            
            return {
                "source": "qdrant",
                "total_fields": len(fields),
                "fields": fields,
                "missing_standard": missing,
                "old_fields": old_found
            }
        
    except Exception as e:
        print(f"❌ Qdrant检查失败: {e}")
        return None


async def check_mysql():
    """检查MySQL exercises表字段"""
    print("\n" + "="*60)
    print("🔵 检查MySQL exercises表")
    print("="*60)
    
    try:
        import aiomysql
        
        conn = await aiomysql.connect(
            host=os.getenv("MYSQL_HOST", "mysql"),
            port=int(os.getenv("MYSQL_PORT", 3306)),
            user=os.getenv("MYSQL_USER", "fitness_user"),
            password=os.getenv("MYSQL_PASSWORD", "fitness_password"),
            db=os.getenv("MYSQL_DATABASE", "fitness_app")
        )
        
        async with conn.cursor() as cursor:
            # 获取表结构
            await cursor.execute("DESCRIBE exercises")
            columns = await cursor.fetchall()
            fields = [col[0] for col in columns]
            
            print(f"\n📊 表字段数: {len(fields)}")
            
            # 检查标准字段
            print("\n✅ 标准字段检查:")
            standard_check = ["difficulty_zh", "difficulty_en", "equipment_zh", "equipment_en",
                            "force_zh", "force_en", "mechanic_zh", "mechanic_en"]
            missing = []
            for field in standard_check:
                if field in fields:
                    print(f"  ✓ {field}")
                else:
                    print(f"  ✗ {field} (缺失)")
                    missing.append(field)
            
            # 检查旧字段
            print("\n⚠️ 旧字段检查:")
            old_found = []
            for old_field in OLD_FIELDS:
                if old_field in fields:
                    print(f"  ✗ {old_field} (仍存在)")
                    old_found.append(old_field)
            
            if not old_found:
                print("  ✅ 未发现旧字段")
            
            # 检查difficulty_zh值分布
            await cursor.execute("""
                SELECT difficulty_zh, COUNT(*) as count 
                FROM exercises 
                GROUP BY difficulty_zh 
                ORDER BY count DESC
            """)
            dist = await cursor.fetchall()
            print("\n📊 difficulty_zh值分布:")
            for row in dist:
                print(f"  {row[0] or '空值'}: {row[1]}个")
        
        conn.close()
        return {
            "source": "mysql",
            "total_fields": len(fields),
            "fields": fields,
            "missing_standard": missing,
            "old_fields": old_found
        }
        
    except Exception as e:
        print(f"❌ MySQL检查失败: {e}")
        return None


async def check_mcp_tools():
    """检查MCP工具中使用的字段名"""
    print("\n" + "="*60)
    print("🔧 检查MCP工具字段使用")
    print("="*60)
    
    mcp_tools_path = Path("/app/src/applications/fitness/mcp_tools")
    if not mcp_tools_path.exists():
        print("❌ 找不到MCP工具目录")
        return None
    
    # 要检查的旧字段模式
    old_patterns = [
        (r'\.difficulty\b(?!_zh|_en)', 'difficulty'),
        (r'\.equipment\b(?!_zh|_en)', 'equipment'),
        (r'\.force\b(?!_zh|_en)', 'force'),
        (r'\.mechanic\b(?!_zh|_en)', 'mechanic'),
        (r'e\.difficulty\b(?!_zh|_en)', 'e.difficulty'),
        (r'e\.equipment\b(?!_zh|_en)', 'e.equipment'),
        (r'e\.force\b(?!_zh|_en)', 'e.force'),
        (r'e\.mechanic\b(?!_zh|_en)', 'e.mechanic'),
    ]
    
    import re
    
    issues = []
    checked_files = 0
    
    for py_file in mcp_tools_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        
        checked_files += 1
        try:
            content = py_file.read_text(encoding='utf-8')
            
            for pattern, field_name in old_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    # 排除注释和字符串中的匹配
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            # 简单排除注释
                            stripped = line.strip()
                            if not stripped.startswith('#') and not stripped.startswith('"""'):
                                issues.append({
                                    "file": str(py_file.relative_to(mcp_tools_path)),
                                    "line": i,
                                    "field": field_name,
                                    "content": stripped[:80]
                                })
        except Exception as e:
            print(f"  ⚠️ 读取失败: {py_file} - {e}")
    
    print(f"\n📊 检查文件数: {checked_files}")
    
    if issues:
        print(f"\n⚠️ 发现 {len(issues)} 处可能的旧字段使用:")
        for issue in issues[:20]:  # 只显示前20个
            print(f"  {issue['file']}:{issue['line']} - {issue['field']}")
            print(f"    {issue['content']}")
    else:
        print("\n✅ MCP工具中未发现旧字段使用")
    
    return {
        "source": "mcp_tools",
        "checked_files": checked_files,
        "issues": issues
    }


async def check_dag_parameters():
    """检查DAG参数映射配置"""
    print("\n" + "="*60)
    print("📋 检查DAG参数映射配置")
    print("="*60)
    
    config_path = Path("/app/config/parameter_mapping_config.yaml")
    if not config_path.exists():
        print("❌ 找不到参数映射配置文件")
        return None
    
    try:
        import yaml
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print("\n📊 配置文件结构:")
        
        # 检查字段映射
        if "field_mappings" in config:
            mappings = config["field_mappings"]
            print(f"  字段映射数: {len(mappings)}")
            
            # 检查是否有旧字段映射
            old_mappings = []
            for key, value in mappings.items():
                if key in OLD_FIELDS or (isinstance(value, str) and value in OLD_FIELDS):
                    old_mappings.append(f"{key} -> {value}")
            
            if old_mappings:
                print(f"\n⚠️ 发现旧字段映射:")
                for m in old_mappings:
                    print(f"    {m}")
            else:
                print("  ✅ 未发现旧字段映射")
        
        return {
            "source": "dag_config",
            "config_keys": list(config.keys()) if config else []
        }
        
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return None


async def main():
    """主函数"""
    print("="*60)
    print("🔍 数据字段一致性全面检查")
    print("="*60)
    print("检查范围: 文件系统、Neo4j、Qdrant、MySQL、MCP工具、DAG配置")
    
    results = {}
    
    # 1. 检查文件系统
    results["file_system"] = await check_file_system()
    
    # 2. 检查Neo4j
    results["neo4j"] = await check_neo4j()
    
    # 3. 检查Qdrant
    results["qdrant"] = await check_qdrant()
    
    # 4. 检查MySQL
    results["mysql"] = await check_mysql()
    
    # 5. 检查MCP工具
    results["mcp_tools"] = await check_mcp_tools()
    
    # 6. 检查DAG参数配置
    results["dag_config"] = await check_dag_parameters()
    
    # 汇总报告
    print("\n" + "="*60)
    print("📊 汇总报告")
    print("="*60)
    
    all_ok = True
    for source, result in results.items():
        if result is None:
            print(f"  ❌ {source}: 检查失败")
            all_ok = False
        elif "old_fields" in result and result["old_fields"]:
            print(f"  ⚠️ {source}: 发现旧字段 {result['old_fields']}")
            all_ok = False
        elif "issues" in result and result["issues"]:
            print(f"  ⚠️ {source}: 发现 {len(result['issues'])} 处问题")
            all_ok = False
        else:
            print(f"  ✅ {source}: 通过")
    
    if all_ok:
        print("\n🎉 所有数据源字段一致性检查通过！")
    else:
        print("\n⚠️ 存在字段不一致问题，请检查上述详情")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
