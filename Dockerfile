FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（使用清华镜像源）
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    build-essential \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# 验证Node.js安装
RUN node --version && npm --version

# 安装Python依赖 + HTTP API所需依赖
# 使用清华PyPI镜像源，避免超时
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip && \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    mcp>=0.9.0 \
    sentence-transformers>=2.2.0 \
    faiss-cpu>=1.7.4 \
    redis>=5.0.0 \
    aiosqlite>=0.19.0 \
    qdrant-client>=1.15.0 \
    fastapi>=0.104.0 \
    uvicorn[standard]>=0.24.0 \
    pydantic>=2.0.0 \
    pydantic-settings>=2.0.0 \
    python-dotenv>=1.0.0 \
    numpy>=1.24.0 \
    PyYAML>=6.0.0 \
    httpx>=0.24.0 \
    aiohttp>=3.8.0 \
    psutil>=5.9.0 \
    pymysql>=1.1.0 \
    neo4j>=5.15.0 \
    toml>=0.10.2 \
    prometheus_client>=0.19.0 \
    aiomysql>=0.2.0 \
    requests>=2.31.0 \
    PyJWT>=2.8.0

# 复制DAML-RAG源代码（v3.0精简架构）
COPY . .

# 创建数据目录和日志目录
RUN mkdir -p /app/data /app/logs /app/mcp-servers

# ============= 预下载GTE-Large-zh模型 =============
# 使用HuggingFace国内镜像加速下载
# 模型会缓存到 /root/.cache/huggingface/hub/
ENV HF_ENDPOINT=https://hf-mirror.com
ENV HF_HOME=/root/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; \
    model = SentenceTransformer('thenlper/gte-large-zh'); \
    print('✅ GTE-Large-zh model downloaded successfully')" || \
    echo "⚠️ Model download failed, will retry at runtime"

# 设置环境变量（保持HF_ENDPOINT在运行时也生效）
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    PORT=8001 \
    HOST=0.0.0.0 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1

# 暴露HTTP API端口
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 复制启动脚本并修复行尾
COPY entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# 修复.env文件的行尾（如果存在）
RUN if [ -f /app/.env ]; then sed -i 's/\r$//' /app/.env; fi

# 使用entrypoint脚本启动（确保MCP服务构建）
ENTRYPOINT ["/app/entrypoint.sh"]
