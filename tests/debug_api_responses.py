"""调试API响应内容"""
import requests
import json

BASE_URL = "http://localhost:8001"

endpoints = [
    "/api/health",
    "/api/health/components",
    "/api/health/metrics",
    "/api/health/metrics/streaming",
    "/api/health/metrics/prometheus"
]

for endpoint in endpoints:
    print(f"\n{'='*60}")
    print(f"端点: {endpoint}")
    print('='*60)
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}")
        print(f"状态码: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        
        if "prometheus" in endpoint:
            print(f"响应内容（前500字符）:\n{response.text[:500]}")
        else:
            try:
                data = response.json()
                print(f"响应JSON:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
            except:
                print(f"响应文本:\n{response.text[:500]}")
    except Exception as e:
        print(f"错误: {e}")
