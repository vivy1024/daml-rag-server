#!/bin/bash
# -*- coding: utf-8 -*-
"""
性能测试运行脚本

用法:
  ./scripts/run_performance_tests.sh [test_type]

test_type:
  all       - 运行所有测试（默认）
  e2e       - 只运行端到端性能测试
  stress    - 只运行压力测试
  quick     - 只运行快速测试（排除慢速测试）

示例:
  ./scripts/run_performance_tests.sh all
  ./scripts/run_performance_tests.sh e2e
  ./scripts/run_performance_tests.sh stress

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-21
"""

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
CONTAINER_NAME="fitness_daml_rag"
TEST_DIR="tests/performance"

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查Docker容器状态
check_container() {
    print_info "检查Docker容器状态..."
    
    if ! docker ps | grep -q "$CONTAINER_NAME"; then
        print_error "容器 $CONTAINER_NAME 未运行"
        print_info "尝试启动容器..."
        docker-compose up -d $CONTAINER_NAME
        sleep 5
    fi
    
    print_success "容器 $CONTAINER_NAME 正在运行"
}

# 检查API可用性
check_api() {
    print_info "检查API可用性..."
    
    if ! curl -s http://localhost:8001/health > /dev/null; then
        print_error "API不可访问 (http://localhost:8001)"
        print_info "请检查服务日志: docker-compose logs fitness_daml_rag"
        exit 1
    fi
    
    print_success "API可访问"
}

# 运行端到端性能测试
run_e2e_tests() {
    print_info "运行端到端性能测试..."
    echo ""
    
    docker exec $CONTAINER_NAME pytest $TEST_DIR/test_e2e_performance.py -v
    
    if [ $? -eq 0 ]; then
        print_success "端到端性能测试完成"
    else
        print_error "端到端性能测试失败"
        return 1
    fi
}

# 运行压力测试
run_stress_tests() {
    print_info "运行压力测试..."
    echo ""
    
    docker exec $CONTAINER_NAME pytest $TEST_DIR/test_stress_test.py -v -m slow
    
    if [ $? -eq 0 ]; then
        print_success "压力测试完成"
    else
        print_error "压力测试失败"
        return 1
    fi
}

# 运行快速测试
run_quick_tests() {
    print_info "运行快速测试..."
    echo ""
    
    docker exec $CONTAINER_NAME pytest $TEST_DIR/ -v -m "not slow"
    
    if [ $? -eq 0 ]; then
        print_success "快速测试完成"
    else
        print_error "快速测试失败"
        return 1
    fi
}

# 运行所有测试
run_all_tests() {
    print_info "运行所有性能测试..."
    echo ""
    
    docker exec $CONTAINER_NAME pytest $TEST_DIR/ -v
    
    if [ $? -eq 0 ]; then
        print_success "所有测试完成"
    else
        print_error "部分测试失败"
        return 1
    fi
}

# 显示测试报告
show_reports() {
    print_info "查看测试报告..."
    echo ""
    
    # 端到端性能测试报告
    if docker exec $CONTAINER_NAME test -f $TEST_DIR/performance_report.json; then
        print_success "端到端性能测试报告:"
        docker exec $CONTAINER_NAME cat $TEST_DIR/performance_report.json | python -m json.tool
        echo ""
    fi
    
    # 压力测试报告
    if docker exec $CONTAINER_NAME test -f $TEST_DIR/stress_test_report.json; then
        print_success "压力测试报告:"
        docker exec $CONTAINER_NAME cat $TEST_DIR/stress_test_report.json | python -m json.tool
        echo ""
    fi
}

# 主函数
main() {
    local test_type="${1:-all}"
    
    echo ""
    echo "=========================================="
    echo "  性能测试运行脚本"
    echo "=========================================="
    echo ""
    
    # 检查前置条件
    check_container
    check_api
    
    echo ""
    echo "=========================================="
    echo "  开始测试"
    echo "=========================================="
    echo ""
    
    # 根据参数运行测试
    case "$test_type" in
        all)
            run_all_tests
            ;;
        e2e)
            run_e2e_tests
            ;;
        stress)
            run_stress_tests
            ;;
        quick)
            run_quick_tests
            ;;
        *)
            print_error "未知的测试类型: $test_type"
            echo ""
            echo "用法: $0 [test_type]"
            echo ""
            echo "test_type:"
            echo "  all       - 运行所有测试（默认）"
            echo "  e2e       - 只运行端到端性能测试"
            echo "  stress    - 只运行压力测试"
            echo "  quick     - 只运行快速测试"
            echo ""
            exit 1
            ;;
    esac
    
    # 显示报告
    echo ""
    echo "=========================================="
    echo "  测试报告"
    echo "=========================================="
    show_reports
    
    echo ""
    print_success "测试流程完成！"
    echo ""
}

# 运行主函数
main "$@"
