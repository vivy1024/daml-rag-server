#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真实工作流程测试脚本

使用真实用户vivy（user_id=2）测试完整的DAML-RAG工作流程
监控所有11个步骤的执行情况和日志输出

版本: v1.0.0
日期: 2025-12-22
"""

import requests
import json
import time
from datetime import datetime

# 配置
API_URL = "http://localhost:8001/api/v1/chat"
USER_ID = "2"  # vivy
SESSION_ID = f"test_session_{int(time.time())}"

# 测试查询
TEST_QUERIES = [
    "我想练胸肌，给我推荐一些动作",
    "我的训练计划怎么样？",
    "帮我分析一下我的身体数据"
]

def test_workflow(query: str):
    """测试单个查询的完整工作流程"""
    print(f"\n{'='*80}")
    print(f"🚀 开始测试工作流程")
    print(f"{'='*80}")
    print(f"📝 查询: {query}")
    print(f"👤 用户: vivy (user_id={USER_ID})")
    print(f"🔑 会话: {SESSION_ID}")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    # 构建请求
    payload = {
        "user_id": USER_ID,
        "session_id": SESSION_ID,
        "query": query,
        "stream": False  # 非流式，便于调试
    }
    
    print("📤 发送请求...")
    print(f"URL: {API_URL}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}\n")
    
    try:
        # 记录开始时间
        start_time = time.time()
        
        # 发送请求
        response = requests.post(
            API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120  # 2分钟超时
        )
        
        # 记录结束时间
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ 请求完成")
        print(f"⏱️  总耗时: {duration:.2f}秒")
        print(f"📊 状态码: {response.status_code}\n")
        
        # 解析响应
        if response.status_code == 200:
            result = response.json()
            print(f"{'='*80}")
            print(f"📥 响应结果")
            print(f"{'='*80}")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            print(f"{'='*80}\n")
            
            # 提取关键信息
            if "data" in result:
                data = result["data"]
                print(f"✨ 关键信息:")
                print(f"  - 响应长度: {len(data.get('response', ''))} 字符")
                print(f"  - 会话ID: {data.get('session_id', 'N/A')}")
                print(f"  - 请求ID: {data.get('request_id', 'N/A')}")
                
                # 检查是否有结构化数据
                if "structured_data" in data:
                    print(f"  - 结构化数据: {len(data['structured_data'])} 项")
                
                print()
            
            return True
        else:
            print(f"❌ 请求失败")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text}\n")
            return False
            
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（>120秒）\n")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接错误: {e}\n")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {e}\n")
        return False


def main():
    """主函数"""
    print(f"\n{'#'*80}")
    print(f"# DAML-RAG 真实工作流程测试")
    print(f"# 测试用户: vivy (user_id=2, membership_tier=energy)")
    print(f"# 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}\n")
    
    # 测试第一个查询
    query = TEST_QUERIES[0]
    success = test_workflow(query)
    
    if success:
        print(f"\n{'='*80}")
        print(f"🎉 测试完成！")
        print(f"{'='*80}")
        print(f"\n💡 提示:")
        print(f"  1. 查看容器日志: docker logs fitness_daml_rag --tail 200")
        print(f"  2. 查看实时日志: docker logs -f fitness_daml_rag")
        print(f"  3. 查看Prometheus指标: http://localhost:8002/metrics")
        print(f"  4. 查看Grafana仪表板: http://localhost:3001")
        print()
    else:
        print(f"\n{'='*80}")
        print(f"❌ 测试失败")
        print(f"{'='*80}")
        print(f"\n🔍 调试建议:")
        print(f"  1. 检查容器状态: docker ps")
        print(f"  2. 查看错误日志: docker logs fitness_daml_rag --tail 50")
        print(f"  3. 检查服务健康: curl http://localhost:8001/health")
        print(f"  4. 检查数据库连接: docker exec fitness_daml_rag python -c 'import pymysql; print(pymysql.connect(host=\"mysql\", user=\"fitness_user\", password=\"fitness_pass\", database=\"fitness_app\"))'")
        print()


if __name__ == "__main__":
    main()
