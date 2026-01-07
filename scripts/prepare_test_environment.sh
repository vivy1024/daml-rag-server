#!/bin/bash
# 准备测试环境脚本
# 用于流式工作流综合测试

echo "============================================================"
echo "🚀 准备流式工作流综合测试环境"
echo "============================================================"

# 步骤1: 验证Docker容器运行状态
echo ""
echo "📋 步骤1: 验证Docker容器运行状态"
echo "------------------------------------------------------------"

required_containers=("fitness_daml_rag" "fitness_prometheus" "fitness_grafana")
all_running=true

for container in "${required_containers[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "   ✅ ${container} - 运行中"
    else
        echo "   ❌ ${container} - 未运行"
        all_running=false
    fi
done

if [ "$all_running" = false ]; then
    echo ""
    echo "❌ 部分容器未运行，请先启动所有必需的容器"
    echo "   运行: docker-compose up -d"
    exit 1
fi

# 步骤2: 清理测试数据
echo ""
echo "📋 步骤2: 清理测试数据和历史记录"
echo "------------------------------------------------------------"
docker exec fitness_daml_rag python scripts/cleanup_test_data.py

if [ $? -ne 0 ]; then
    echo ""
    echo "⚠️ 清理测试数据时出现警告，但继续执行"
fi

# 步骤3: 验证测试环境
echo ""
echo "📋 步骤3: 验证测试环境配置"
echo "------------------------------------------------------------"
docker exec fitness_daml_rag python scripts/verify_test_environment.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 测试环境验证失败，请检查上述错误"
    exit 1
fi

# 完成
echo ""
echo "============================================================"
echo "✅ 测试环境准备完成！"
echo "============================================================"
echo ""
echo "📝 下一步操作："
echo "   1. 运行功能测试: docker exec fitness_daml_rag pytest tests/integration/test_streaming_workflow_功能.py -v"
echo "   2. 运行性能测试: docker exec fitness_daml_rag pytest tests/performance/test_streaming_workflow_性能.py -v"
echo "   3. 运行完整测试套件: ./scripts/run_comprehensive_streaming_tests.sh"
echo ""
