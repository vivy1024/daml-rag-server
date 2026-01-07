#!/bin/bash
# DAML-RAG容器启动脚本
# 确保MCP服务正确构建并初始化

set -e  # 遇到错误立即退出

echo "🚀 DAML-RAG容器启动中..."
echo "================================================"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 步骤1: 验证Python MCP工具
echo ""
echo "📋 步骤1: 验证Python MCP工具..."
MCP_TOOLS_DIR="/app/src/applications/fitness/mcp_tools"

if [ ! -d "$MCP_TOOLS_DIR" ]; then
    log_error "MCP工具目录不存在: $MCP_TOOLS_DIR"
    exit 1
fi

log_info "MCP工具目录存在: $MCP_TOOLS_DIR"

# 验证关键Python工具目录
TOOL_DIRS=(
    "exercise"
    "nutrition"
    "safety"
    "training"
)

for dir in "${TOOL_DIRS[@]}"; do
    if [ -d "$MCP_TOOLS_DIR/$dir" ]; then
        log_info "  ✓ $dir 工具目录存在"
    else
        log_warn "  ⚠ $dir 工具目录不存在"
    fi
done

# 验证stdio MCP服务（用户档案）
USER_PROFILE_MCP="/app/mcp-servers/user-profile-stdio/build/index.js"
if [ -f "$USER_PROFILE_MCP" ]; then
    log_info "  ✓ user-profile-stdio MCP服务存在"
else
    log_warn "  ⚠ user-profile-stdio MCP服务不存在"
fi

# 步骤2: 验证MCP配置文件
echo ""
echo "📋 步骤2: 验证MCP配置文件..."
MCP_CONFIG="/app/config/mcp_registry.json"

if [ -f "$MCP_CONFIG" ]; then
    log_info "MCP配置文件存在: $MCP_CONFIG"
    
    # 验证JSON格式
    if python3 -c "import json; json.load(open('$MCP_CONFIG'))" 2>/dev/null; then
        log_info "MCP配置文件格式正确"
    else
        log_error "MCP配置文件格式错误"
        exit 1
    fi
else
    log_error "MCP配置文件不存在: $MCP_CONFIG"
    exit 1
fi

# 步骤3: 验证数据库连接配置
echo ""
echo "📋 步骤3: 验证数据库连接配置..."

# 检查环境变量
REQUIRED_VARS=(
    "NEO4J_URI"
    "QDRANT_HOST"
    "REDIS_HOST"
    "MYSQL_HOST"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        log_warn "  ⚠ 环境变量 $var 未设置"
    else
        log_info "  ✓ $var = ${!var}"
    fi
done

# 步骤4: 启动DAML-RAG服务
echo ""
echo "📋 步骤4: 启动DAML-RAG主服务..."
echo "================================================"
cd /app

log_info "所有准备工作完成，启动DAML-RAG服务器..."
log_info "MCP工具模式: 15个Python内置工具 + 1个stdio MCP服务（用户档案）"
log_info "  - Python工具: exercise(2) + nutrition(4) + safety(3) + training(6)"
log_info "  - stdio MCP: user-profile-stdio (Node.js)"
echo ""

# 执行Python启动脚本
exec python3 start_server.py
