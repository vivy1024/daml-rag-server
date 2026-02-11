FROM python:3.11-slim

WORKDIR /app

# ============= 第1层：系统依赖（很少变化，缓存命中率高）=============
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y \
    build-essential \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

RUN node --version && npm --version

# ============= 第2层：Python依赖（仅requirements.txt变化时重建）=============
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip && \
    pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# ============= 第3层：模型下载（~4.3GB，极少变化，缓存命中率最高）=============
ENV HF_ENDPOINT=https://hf-mirror.com
ENV HF_HOME=/root/.cache/huggingface
RUN python -c "from sentence_transformers import SentenceTransformer; \
    model = SentenceTransformer('thenlper/gte-large-zh'); \
    print('✅ GTE-Large-zh model downloaded successfully')" || \
    echo "⚠️ Model download failed, will retry at runtime"

# ============= 第4层：应用代码（频繁变化，但层很小）=============
COPY . .

# 创建数据目录和日志目录
RUN mkdir -p /app/data /app/logs /app/mcp-servers

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    PORT=8001 \
    HOST=0.0.0.0 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_OFFLINE=1

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 复制启动脚本并修复行尾
COPY entrypoint.sh /app/entrypoint.sh
RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# 修复.env文件的行尾（如果存在）
RUN if [ -f /app/.env ]; then sed -i 's/\r$//' /app/.env; fi

ENTRYPOINT ["/app/entrypoint.sh"]
