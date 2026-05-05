# 产品经理多Agent协作工作站 - 后端服务
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml .
COPY README.md .

# 安装依赖
RUN pip install --no-cache-dir --prefix=/install .

# 生产阶段
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# 复制安装的依赖
COPY --from=builder /install /usr/local

# 复制源代码
COPY src/ src/
COPY docs/ docs/

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# 环境变量
ENV PYTHONPATH=/app/src
ENV PORT=8000

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "pm_workstation.api.app:create_app", "--host", "0.0.0.0", "--port", "8000"]
