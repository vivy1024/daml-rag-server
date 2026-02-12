# 使用预构建基础镜像（包含系统依赖+Python包+GTE-Large-zh模型）
# 基础镜像更新方式：修改requirements.txt后，本地运行：
#   docker build -f Dockerfile.base -t crpi-32sc66smgb44ld25.cn-hangzhou.personal.cr.aliyuncs.com/yuzhenfitness/daml-rag-base:latest .
#   docker push crpi-32sc66smgb44ld25.cn-hangzhou.personal.cr.aliyuncs.com/yuzhenfitness/daml-rag-base:latest
FROM crpi-32sc66smgb44ld25.cn-hangzhou.personal.cr.aliyuncs.com/yuzhenfitness/daml-rag-base:latest

WORKDIR /app

# 只复制应用代码（依赖和模型已在基础镜像中）
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
