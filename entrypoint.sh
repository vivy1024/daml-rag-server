#!/bin/bash
# DAML-RAG Container Startup Script
# Ensures MCP services are properly built and initialized

set -e  # Exit on error

echo "DAML-RAG Container Starting..."
echo "================================================"

# Color definitions
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${GREEN}[OK] $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

log_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Step 0: Environment Detection and Configuration
echo ""
echo "Step 0: Detecting environment..."
cd /app

# 检测是否在Zeabur生产环境
if [ "$ENVIRONMENT" = "production" ] || [ -n "$ZEABUR_SERVICE_ID" ]; then
    log_info "Detected Zeabur production environment"
    
    # 如果存在.env.production，使用它
    if [ -f "/app/.env.production" ]; then
        log_info "Loading .env.production configuration..."
        # 导出.env.production中的变量（不覆盖已存在的环境变量）
        set -a
        source /app/.env.production
        set +a
        log_info "Production configuration loaded"
    else
        log_warn ".env.production not found, using Zeabur injected variables"
    fi
    
    # 打印关键配置（调试用）
    log_info "REDIS_HOST: ${REDIS_HOST:-not set}"
    log_info "MYSQL_HOST: ${MYSQL_HOST:-not set}"
    log_info "NEO4J_URI: ${NEO4J_URI:-not set}"
else
    log_info "Detected local development environment"
    
    # 本地环境使用.env
    if [ -f "/app/.env" ]; then
        log_info "Loading .env configuration..."
        set -a
        source /app/.env
        set +a
    fi
fi

# Step 1: Verify Python MCP Tools
echo ""
echo "Step 1: Verifying Python MCP Tools..."
MCP_TOOLS_DIR="/app/src/applications/fitness/mcp_tools"

if [ ! -d "$MCP_TOOLS_DIR" ]; then
    log_error "MCP tools directory not found: $MCP_TOOLS_DIR"
    exit 1
fi

log_info "MCP tools directory exists: $MCP_TOOLS_DIR"

# Verify key Python tool directories
TOOL_DIRS=("exercise" "nutrition" "safety" "training")

for dir in "${TOOL_DIRS[@]}"; do
    if [ -d "$MCP_TOOLS_DIR/$dir" ]; then
        log_info "  $dir tools directory exists"
    else
        log_warn "  $dir tools directory not found"
    fi
done

# Verify stdio MCP service (user profile)
USER_PROFILE_MCP="/app/mcp-servers/user-profile-stdio/build/index.js"
if [ -f "$USER_PROFILE_MCP" ]; then
    log_info "  user-profile-stdio MCP service exists"
else
    log_warn "  user-profile-stdio MCP service not found"
fi

# Step 2: Verify MCP config file
echo ""
echo "Step 2: Verifying MCP config file..."
MCP_CONFIG="/app/config/mcp_registry.json"

if [ -f "$MCP_CONFIG" ]; then
    log_info "MCP config file exists: $MCP_CONFIG"
    
    # Verify JSON format
    if python3 -c "import json; json.load(open('$MCP_CONFIG'))" 2>/dev/null; then
        log_info "MCP config file format is valid"
    else
        log_error "MCP config file format is invalid"
        exit 1
    fi
else
    log_error "MCP config file not found: $MCP_CONFIG"
    exit 1
fi

# Step 3: Verify database connection config
echo ""
echo "Step 3: Verifying database connection config..."

# Check environment variables
REQUIRED_VARS=("NEO4J_URI" "QDRANT_HOST" "REDIS_HOST" "MYSQL_HOST")

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        log_warn "  Environment variable $var is not set"
    else
        log_info "  $var = ${!var}"
    fi
done

# Step 4: Start DAML-RAG service
echo ""
echo "Step 4: Starting DAML-RAG main service..."
echo "================================================"
cd /app

log_info "All preparation complete, starting DAML-RAG server..."
log_info "MCP tools mode: 18 Python built-in tools + 1 stdio MCP service (user profile)"
log_info "  - Python tools: exercise(2) + nutrition(4) + safety(3) + training(9)"
log_info "  - stdio MCP: user-profile-stdio (Node.js)"
echo ""

# Execute Python startup script
exec python3 start_server.py
