#!/usr/bin/env python3
"""验证远程MySQL数据完整性"""
import pymysql

REMOTE_HOST = "182.92.78.183"
REMOTE_PORT = 30932
REMOTE_USER = "root"
REMOTE_PASSWORD = "root_password_2025"
REMOTE_DB = "fitness_app"

LOCAL_HOST = "fitness_mysql"
LOCAL_PORT = 3306
LOCAL_USER = "root"
LOCAL_PASSWORD = "root_password_2025"
LOCAL_DB = "fitness_app"

def get_tables_info(conn):
    """获取所有表的信息"""
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    
    info = {}
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cursor.fetchone()[0]
        info[table] = count
    return info

def main():
    print("=" * 50)
    print("MySQL数据验证")
    print("=" * 50)
    
    # 连接本地
    local_conn = pymysql.connect(host=LOCAL_HOST, port=LOCAL_PORT, user=LOCAL_USER, 
                                  password=LOCAL_PASSWORD, database=LOCAL_DB)
    # 连接远程
    remote_conn = pymysql.connect(host=REMOTE_HOST, port=REMOTE_PORT, user=REMOTE_USER,
                                   password=REMOTE_PASSWORD, database=REMOTE_DB)
    
    try:
        local_info = get_tables_info(local_conn)
        remote_info = get_tables_info(remote_conn)
        
        print(f"\n{'表名':<30} {'本地':<10} {'远程':<10} {'状态'}")
        print("-" * 60)
        
        all_tables = set(local_info.keys()) | set(remote_info.keys())
        issues = []
        
        for table in sorted(all_tables):
            local_count = local_info.get(table, 0)
            remote_count = remote_info.get(table, 0)
            
            if local_count == remote_count:
                status = "✅"
            elif remote_count == 0 and local_count > 0:
                status = "❌ 缺失"
                issues.append(table)
            else:
                status = f"⚠️ 差{local_count - remote_count}"
            
            print(f"{table:<30} {local_count:<10} {remote_count:<10} {status}")
        
        # 关键表检查
        print("\n关键表详情:")
        key_tables = ['users', 'exercises', 'foods', 'training_logs', 'user_profiles']
        for table in key_tables:
            if table in remote_info:
                print(f"  {table}: {remote_info[table]} 条")
            else:
                print(f"  {table}: 不存在")
        
    finally:
        local_conn.close()
        remote_conn.close()

if __name__ == "__main__":
    main()
