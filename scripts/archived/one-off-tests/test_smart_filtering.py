"""
测试智能过滤功能
验证查询"胸部训练"时是否还会返回"山"（瑜伽动作）
"""
import requests
import json

def test_smart_filtering():
    """测试智能过滤"""
    url = "http://localhost:8001/api/graphrag/query"
    
    # 测试查询：胸部训练动作
    payload = {
        "query_text": "胸部训练动作",
        "user_id": "21",
        "user_profile": {
            "fitness_level": "intermediate",
            "available_equipment": ["杠铃", "哑铃"],
            "health_conditions": [],
            "injury_history": []
        },
        "filters": {},  # 不使用额外过滤，只测试智能过滤
        "top_k": 10
    }
    
    print("=" * 80)
    print("测试智能过滤功能")
    print("=" * 80)
    print(f"查询: {payload['query_text']}")
    print(f"过滤条件: {payload['filters']}")
    print()
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        print(f"响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # API返回格式：{"code": 200, "msg": "success", "data": {...}}
            api_data = data.get("data", {})
            results = api_data.get("results", [])
            print(f"返回结果数量: {len(results)}")
            print()
            
            # 检查是否包含"山"
            has_yoga = False
            
            # 打印第一个结果的完整结构用于调试
            if results:
                print(f"第一个结果结构: {json.dumps(results[0], ensure_ascii=False, indent=2)}")
                print()
            
            for i, result in enumerate(results[:10], 1):
                # 尝试不同的字段路径
                if "payload" in result:
                    payload = result["payload"]
                    name = payload.get("name_zh", "未知")
                    equipment = payload.get("equipment_zh", "未知")
                else:
                    name = result.get("name_zh", "未知")
                    equipment = result.get("equipment_zh", "未知")
                
                score = result.get("score", 0)
                
                print(f"{i}. {name} (器械: {equipment}, 相似度: {score:.4f})")
                
                if name == "山":
                    has_yoga = True
                    print("   ⚠️ 发现瑜伽动作！")
            
            print()
            if has_yoga:
                print("❌ 智能过滤失败：仍然返回瑜伽动作")
            else:
                print("✅ 智能过滤成功：已排除瑜伽动作")
        else:
            print(f"❌ 请求失败: {response.text}")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    test_smart_filtering()
