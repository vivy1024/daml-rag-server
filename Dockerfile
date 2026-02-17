# syntax=docker/dockerfile:1
# 使用 BuildKit cache mount 持久化依赖和模型缓存
# Zeabur 支持 BuildKit，后续构建命中缓存后只需几分钟
#
# 旧方案（已弃用）：FROM 阿里云预构建镜像(4.39GB) → 每次构建都要拉取
# 新方案：FROM python:3.11-slim + --mount=type=cache → 首次慢，后续快

FROM python:3.11-slim

WORKDIR /app

# 系统依赖（这层变化少，Docker layer cache 会缓存）
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖（--mount=type=cache 持久化 pip 下载缓存）
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip && \
    pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 下载 GTE-Large-zh 模型
# cache mount 在 /tmp/hf_cache 持久化下载缓存，然后复制到镜像内的最终位置
# 首次构建：下载 ~1.2GB → 复制到镜像
# 后续构建：缓存命中 → 直接复制（秒级）
ENV HF_ENDPOINT=https://hf-mirror.com
RUN --mount=type=cache,target=/tmp/hf_cache \
    HF_HOME=/tmp/hf_cache python -c "\
from sentence_transformers import SentenceTransformer; \
model = SentenceTransformer('thenlper/gte-large-zh'); \
print('GTE-Large-zh ready')" && \
    mkdir -p /root/.cache && \
    cp -r /tmp/hf_cache /root/.cache/huggingface

# 复制应用代码
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
